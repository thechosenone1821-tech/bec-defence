"""SPINE — Containment planner (M5).

Given the attacker's apparent position — the VLANs the live campaign touches —
and the campus VLAN topology, compute the minimum-disruption cut that severs
reachability from the compromised side to every Tier-0 (crown) asset.

Honest scope notes
------------------
* The planner PROPOSES. Nothing here executes. The bus submits the proposal to
  the Governor (whose preserve_tier0_vlans invariant + TCB re-derivation gate
  it); the executor is a dry-run organ. Three independent locks, never one.
* Fixture flows come from the topology's edge weights — there is no live
  NetFlow in the sandbox. Every flow number below is FIXTURE-MEASURED, never
  quoted as a production SLO.
* The candidate space is tiny (10 non-crown edges), so the optimizer is
  EXHAUSTIVE, not heuristic: every subset is scored, best feasible wins.
  Deterministic; no randomness, no ML.

Objective:  minimize  J = C + lambda*D + mu*R + nu*A
  C = cut size (edges severed, count)
  D = fraction of non-crown fixture flow weight severed (0..1)
  R = mission-critical fixture flow weight still reachable from seeds
  A = number of severed edges incident to a Tier-0 VLAN (clinical-adjacent)
Constraint: reachability from seeds to any Tier-0 VLAN == empty set.

Crowd-jewel edges (criticality_weights.* == null  =>  infinite) are never
candidates, exactly as in the Hashimoto organ. Edges incident to a Tier-0 VLAN
are legal candidates (that IS how you protect it) but carry the nu penalty so
clinical/core-adjacent roads are severed only when there is no cheaper way.
"""

from __future__ import annotations

import itertools
import json
import time
import uuid
from collections import deque
from typing import Any, Dict, List, Optional, Sequence, Tuple

INF = float("inf")


def load_topology(path: str) -> Dict[str, Any]:
    with open(path) as f:
        topo = json.load(f)
    crit_weights = (topo.get("criticality_weights") or {})
    vlans = [v["id"] for v in topo.get("vlans", [])]
    tier0 = sorted(v["id"] for v in topo.get("vlans", [])
                   if v.get("tier") == 0 or v.get("criticality") == "crown_jewel")
    tier0_set = set(tier0)
    edges: List[Dict[str, Any]] = []
    for raw in topo.get("edges", []):
        crit = raw.get("criticality", "standard")
        wt = raw.get("weight")
        if wt is None:
            wt = crit_weights.get(crit)
        if crit == "crown_jewel" or wt is None:
            weight, protected = INF, True
        else:
            weight, protected = float(wt), False
        mission = (not protected) and (crit == "mission_critical" or weight >= 8.0)
        edges.append({"a": raw["a"], "b": raw["b"], "criticality": crit,
                      "weight": weight, "protected": protected,
                      "mission_critical": mission,
                      "tier0_adjacent": bool({raw["a"], raw["b"]} & tier0_set)})
    return {"vlans": sorted(set(vlans)), "tier0_vlans": tier0, "edges": edges}


def _reachable(vlans: Sequence[str], edges: List[Dict[str, Any]],
               seeds: Sequence[str], cut_idx: Sequence[int]) -> set:
    adj: Dict[str, List[str]] = {v: [] for v in vlans}
    cut = set(cut_idx)
    for i, e in enumerate(edges):
        if i in cut:
            continue
        adj[e["a"]].append(e["b"])
        adj[e["b"]].append(e["a"])
    seen, q = set(seeds), deque(seeds)
    while q:
        u = q.popleft()
        for v in adj.get(u, []):
            if v not in seen:
                seen.add(v)
                q.append(v)
    return seen


def _mission_weight(edges: List[Dict[str, Any]], reach: set) -> float:
    return sum(e["weight"] for e in edges
               if e["mission_critical"] and e["a"] in reach and e["b"] in reach)


def propose(topology_path: str, seeds: Sequence[str],
            lam: float = 2.0, mu: float = 0.1, nu: float = 5.0) -> Dict[str, Any]:
    """Exhaustive minimum-disruption containment over the access layer."""
    t0 = time.time()
    topo = load_topology(topology_path)
    vlans, tier0, edges = topo["vlans"], topo["tier0_vlans"], topo["edges"]
    tier0_set = set(tier0)

    seeds = list(dict.fromkeys(str(s) for s in seeds if str(s).strip()))
    if not seeds:
        return {"status": "REFUSED", "reason": "no seed VLANs supplied (pass seeds=[...] or replay an attack first)"}
    unknown = [s for s in seeds if s not in vlans]
    if unknown:
        return {"status": "REFUSED", "reason": f"unknown VLAN seed(s): {unknown}", "valid_vlans": vlans}
    on_tier0 = [s for s in seeds if s in tier0_set]
    if on_tier0:
        return {"status": "REFUSED", "reason": f"seed(s) sit ON Tier-0: {on_tier0} — no cut can protect a breached crown asset; page the human",
                "tier0_vlans": tier0}

    total_flow = sum(e["weight"] for e in edges if not e["protected"])
    crit_before = sum(e["weight"] for e in edges if e["mission_critical"]) or 1.0
    candidates = [i for i, e in enumerate(edges) if not e["protected"]]

    best: Optional[Tuple[Tuple[float, int], Tuple[int, ...], float, float, float, float, set]] = None
    for r in range(0, len(candidates) + 1):
        if best is not None and r > best[0][1] and r > best[0][0]:
            pass  # keep scanning equal sizes for tie-breaking determinism; tiny space
        for combo in itertools.combinations(candidates, r):
            reach = _reachable(vlans, edges, seeds, combo)
            if tier0_set & reach:
                continue
            severed = sum(edges[i]["weight"] for i in combo)
            D = severed / total_flow if total_flow else 0.0
            R = _mission_weight(edges, reach)
            A = sum(1 for i in combo if edges[i]["tier0_adjacent"])
            C = len(combo)
            J = C + lam * D + mu * R + nu * A
            key = (round(J, 9), C)
            if best is None or key < best[0]:
                best = (key, combo, D, R, A, severed, reach)

    if best is None:
        return {"status": "INFEASIBLE",
                "reason": "no non-crown cut severs the seeds from Tier-0 — attacker is already inside the core-adjacent fabric; human step-up required",
                "seeds": seeds, "tier0_vlans": tier0}

    (key, combo, D, R, A, severed, reach) = best
    cut_edges = [{"a": edges[i]["a"], "b": edges[i]["b"], "criticality": edges[i]["criticality"],
                  "weight": None if edges[i]["weight"] == INF else edges[i]["weight"],
                  "tier0_adjacent": edges[i]["tier0_adjacent"]} for i in combo]
    crit_after = crit_before - sum(edges[i]["weight"] for i in combo if edges[i]["mission_critical"])
    plan = {
        "status": "PLAN_PROPOSED",
        "plan_id": f"cut_{uuid.uuid4().hex[:10]}",
        "seeds": seeds,
        "cut_edges": cut_edges,
        "cut_size": len(combo),
        "objective": {"C": len(combo), "D": round(D, 4), "R": round(R, 2), "A": A,
                      "lambda": lam, "mu": mu, "nu": nu, "J": round(key[0], 4)},
        "preserved_fixture_flow_pct": round((1.0 - D) * 100.0, 2),
        "preserved_critical_weight_pct": round(100.0 * crit_after / crit_before, 2),
        "tier0_edges_cut": 0,
        "tier0_adjacent_cut_edges": A,
        "reachability_to_tier0": "EMPTY",
        "icu_status": "INTACT" if not any(e["a"] == "VLAN_ICU_CLINICAL" or e["b"] == "VLAN_ICU_CLINICAL"
                                          for e in cut_edges) else "ADJACENT_ROAD_CUT_REVIEW_REQUIRED",
        "note": "Fixture-measured on the synthetic campus graph; not a production SLO.",
        "computed_in_ms": round((time.time() - t0) * 1000.0, 1),
    }
    return plan
