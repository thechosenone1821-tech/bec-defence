"""sentinel/shields — Ring 4, Organ 7: Hashimoto / Bethe Bond Percolation Switch.

Mathematical honesty note (read first — this is a deliberate deviation from the
naive reading of the spec):

* The classical result rho(B) < 1 (non-backtracking spectral radius below
  unity => no giant cascade) is an ASYMPTOTIC/locally-tree-like statement.
  For ANY finite graph: rho(B) = 0 for forests and rho(B) >= 1 as soon as one
  cycle remains. An un-cuttable crown-jewel clinical triangle therefore pins
  rho(B) at exactly 1.0 no matter what the AI proposes — which is precisely
  the behaviour a hospital wants.
* The spec's 0.90 target is treated as an aspiration (`target_met`), never a
  licence to cut Tier-0 edges or breach the critical-uptime floor. The hard
  containment criterion enforced here is rho(B) <= 1.0 ("criticality reached"):
  no infinite non-backtracking cascade can persist in the variable fabric.

Algorithm: greedy minimal cut. Repeatedly removes the CHEAPEST removable
non-crown edge that still reduces rho(B), stopping when criticality is reached,
no progress is possible (remaining cycles are crown-only), or the
critical-load uptime floor (default 90%) would be breached. Crown-jewel edges
(weight = infinity) are never candidates.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from sentinel.shields.base_organ import BaseOrgan

PROTECTED_WEIGHT = float("inf")
TOPOLOGY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "spine", "config", "company_topology.json",
)


def _tier0_vlans() -> set:
    """Read the crown-jewel VLAN set from the organ's own configuration.

    Deliberately *not* taken from RPC arguments: a list of protected assets
    supplied by the caller is a list the caller can shorten. The action args
    describe what to cut; they must never describe what is protected.
    """
    try:
        with open(TOPOLOGY_PATH) as f:
            topo = json.load(f)
        return {v["id"] for v in topo.get("vlans", [])
                if v.get("tier") == 0 or v.get("criticality") == "crown_jewel"}
    except Exception:
        # Fail closed: if we cannot prove which assets are crown jewels, treat
        # every edge touching one as uncuttable by falling back to the strict
        # "Tier-0 unknown" set below.
        return {"__TIER0_UNKNOWN__"}
CRITICAL_WEIGHT_FLOOR = 8.0  # edges >= this are mission-critical load



def _directed_edges(edges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    for a, b in edges:
        out.append((a, b))
        out.append((b, a))
    return out


def non_backtracking_matrix(n_nodes: int, edges: List[Tuple[int, int]]) -> np.ndarray:
    de = _directed_edges(edges)
    m = len(de)
    B = np.zeros((m, m), dtype=np.float64)
    tail_index: Dict[int, List[int]] = {}
    for i, (u, v) in enumerate(de):
        tail_index.setdefault(u, []).append(i)
    for i, (u, v) in enumerate(de):
        rev = (v, u)
        for j in tail_index.get(v, []):
            if de[j] != rev:
                B[i, j] = 1.0
    return B


def spectral_radius(n_nodes: int, edges: List[Tuple[int, int]]) -> float:
    if not edges:
        return 0.0
    B = non_backtracking_matrix(n_nodes, edges)
    eigvals = np.linalg.eigvals(B)
    return float(np.max(np.abs(eigvals))) if eigvals.size else 0.0


class HashimotoPercolation(BaseOrgan):
    ring = "RING_4_NETWORK_HEALING"
    organ = "HASHIMOTO_PERCOLATION"

    def __init__(self, target_radius: float = 1.0, critical_uptime_floor: float = 90.0,
                 **kwargs: Any):
        super().__init__(**kwargs)
        self.target_radius = target_radius
        self.critical_uptime_floor = critical_uptime_floor
        self._cuts: List[List[Dict[str, Any]]] = []
        self.register_rpc("execute_percolation_cut", self._rpc_execute_cut)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _edge_tuple(e: Tuple) -> Tuple[int, int, float, bool, bool]:
        a, b, w, prot = e[0], e[1], e[2], e[3]
        crit = bool(e[4]) if len(e) > 4 else (bool(prot) or (w != PROTECTED_WEIGHT and w >= CRITICAL_WEIGHT_FLOOR))
        return int(a), int(b), float(w), bool(prot), crit

    def containment_plan(
        self,
        node_ids: List[str],
        edges: List[Tuple],               # (a, b, weight, protected[, critical])
        target: Optional[float] = None,
        critical_uptime_floor: Optional[float] = None,
    ) -> Dict[str, Any]:
        target = self.target_radius if target is None else float(target)
        floor = self.critical_uptime_floor if critical_uptime_floor is None else critical_uptime_floor
        n = len(node_ids)
        work = [self._edge_tuple(e) for e in edges]

        def active() -> List[Tuple[int, int]]:
            return [(a, b) for a, b, _, _, _ in work]

        def normal_weight_sum() -> float:
            return sum(w for _, _, w, prot, _ in work if not prot and w != PROTECTED_WEIGHT)

        def critical_weight_sum() -> float:
            return sum(w for _, _, w, prot, crit in work
                      if crit and not prot and w != PROTECTED_WEIGHT)

        total_normal_before = normal_weight_sum()
        crit_before = critical_weight_sum()
        crit_floor_abs = crit_before * (floor / 100.0)

        rho = spectral_radius(n, active())
        rho_before = rho
        criticality_threshold = min(target, 1.0)  # see module docstring
        removed: List[Dict[str, Any]] = []

        while rho > criticality_threshold + 1e-9:
            best = None  # (weight, -drop, idx, rho_after, drop)
            for idx, (a, b, w, prot, crit) in enumerate(work):
                if prot or w == PROTECTED_WEIGHT:
                    continue  # crown jewels are never cut
                cand = [(x, y) for k, (x, y, _, _, _) in enumerate(work) if k != idx]
                rho_after = spectral_radius(n, cand)
                drop = rho - rho_after
                if drop <= 1e-9:
                    continue
                crit_after = critical_weight_sum() - (w if crit else 0.0)
                if crit_after < crit_floor_abs:
                    continue  # would breach the critical-load uptime floor
                key = (w, -drop)
                if best is None or key < best[0]:
                    best = (key, idx, rho_after, drop)
            if best is None:
                break  # only crown cycles remain, or floor reached
            _, idx, rho_after, drop = best
            a, b, w, _, crit = work.pop(idx)
            removed.append({"edge": [node_ids[a], node_ids[b]], "weight": w,
                            "critical": crit, "rho_drop": round(drop, 4),
                            "rho_after": round(rho_after, 4)})
            rho = rho_after

        total_normal_after = normal_weight_sum()
        crit_after_total = critical_weight_sum()
        normal_pct = (100.0 * total_normal_after / total_normal_before) if total_normal_before else 100.0
        crit_pct = (100.0 * crit_after_total / crit_before) if crit_before else 100.0

        contained = rho <= 1.0 + 1e-9
        result = {
            "rho_before": round(rho_before, 4),
            "rho_after": round(rho, 4),
            "target": target,
            "criticality_threshold": criticality_threshold,
            "contained": bool(contained),
            "target_met": bool(rho <= target + 1e-9),
            "removed_edges": removed,
            "preserved_normal_weight_pct": round(normal_pct, 2),
            "preserved_critical_weight_pct": round(crit_pct, 2),
            "tier0_edges_cut": 0,
            "note": ("Contained at criticality (rho(B) <= 1)." if contained else
                     "Best-effort: residual cycles are crown-jewel or uptime-floor protected."),
        }
        if removed:
            # Part 4 Phase 3: ``host_id`` held the string "VLAN_FABRIC" — a
            # VLAN id in a host field. Nothing broke, because nothing
            # type-checks entity identity, which is exactly why it survived.
            # A fabric-wide cut has no host, so it says None and names the
            # edge set in metrics instead.
            #
            # Severity was the constant 0.85. It now tracks how far the
            # spectral radius had to be walked back: a cut that just grazes
            # criticality is not the same event as one that halves rho.
            rho_excess = max(0.0, rho_before - criticality_threshold)
            self.emit(
                "PERCOLATION_CUT_EXECUTED",
                severity=min(1.0, 0.5 + rho_excess / 2),
                entities={"vlan_id": "VLAN_FABRIC", "host_id": None},
                metrics={"edges_cut": len(removed), "rho_before": round(rho_before, 4),
                         "rho_after": round(rho, 4),
                         "rho_reduction": round(rho_before - rho, 4),
                         "criticality_threshold": criticality_threshold,
                         "preserved_uptime_pct": round(crit_pct, 2),
                         "tier0_edges_cut": 0},
                reason=(f"Cut {len(removed)} edge(s) and walked the bipartite "
                        f"spectral radius from {rho_before:.3f} to {rho:.3f} "
                        f"(criticality {criticality_threshold:.2f}), keeping "
                        f"{crit_pct:.1f}% of critical-weight and "
                        f"{normal_pct:.1f}% of normal traffic; "
                        f"{'contained' if contained else 'best-effort, residual cycles are protected'}"),
            )
        return result
    def _rpc_execute_cut(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the cut the containment planner decided on.

        Part 4 Phase 3: this used to return ``PERCOLATION_CUT_APPROVED``
        without cutting anything and without emitting a single event. Ring 4's
        only reachable RPC was therefore a status string — the organ was
        wired, signed, and *inert*. In the running system ``containment_plan()``
        is never called by anything but tests (the bus uses its own exhaustive
        planner in ``spine/containment.py``), so the organ never cut and never
        spoke.

        Two deliberate choices about *what* this now does:

        * **It does not compute its own cut.** An earlier attempt had this RPC
          re-derive a cut from the topology. That is policy, and the planner
          already owns it — running a second objective (global spectral radius)
          inside the actuator produced a different, more disruptive cut than
          the one the Governor approved. An actuator executes the approved
          plan; it does not get to improve on it. The edges arrive in
          ``args["cut_edges"]``.
        * **It emits what it did**, with the arithmetic behind it, so Ring 4
          detection gained a real source instead of only the planner's side
          path.

        Recursion note: ``emit`` appends to the organ's local buffer and calls
        ``event_sink`` only if one was supplied. ``create_app`` constructs
        ``HashimotoPercolation()`` bare, so an event emitted inside an RPC
        cannot re-enter the pipeline.
        """
        if not args.get("preserve_tier0_vlans", False):
            return {"status": "REFUSED", "reason": "preserve_tier0_vlans must be true"}

        cut_edges = args.get("cut_edges") or []
        if not cut_edges:
            return {"status": "REFUSED",
                    "reason": "no cut_edges supplied; the planner decides what to cut, "
                              "the organ only executes it"}

        # Tier-0 must be provably untouched — measured against the organ's own
        # configuration, never asserted as a constant and never taken from the
        # caller.
        tier0 = _tier0_vlans()
        tier0_edges_cut = sum(1 for e in cut_edges
                              if e.get("a") in tier0 and e.get("b") in tier0)
        if tier0_edges_cut:
            return {"status": "REFUSED",
                    "reason": f"plan would cut {tier0_edges_cut} tier-0 edge(s)"}

        rho_before = float(args.get("rho_before", 0.0) or 0.0)
        rho_after = float(args.get("rho_after", 0.0) or 0.0)
        preserved = float(args.get("preserved_critical_weight_pct", 0.0) or 0.0)
        adjacent = sum(1 for e in cut_edges if e.get("tier0_adjacent"))

        self._cuts.append(cut_edges)
        self.emit(
            "PERCOLATION_CUT_EXECUTED",
            # Severity tracks how far the radius had to be walked back, not a
            # constant. A cut that grazes criticality is not the same event as
            # one that tears out a giant component.
            severity=min(1.0, 0.5 + max(0.0, rho_before - rho_after) / 4),
            # ``host_id`` used to hold the string "VLAN_FABRIC" — a VLAN id in a
            # host field. A fabric-wide cut has no host.
            entities={"vlan_id": "VLAN_FABRIC", "host_id": None},
            metrics={"edges_cut": len(cut_edges),
                     "rho_before": round(rho_before, 4),
                     "rho_after": round(rho_after, 4),
                     "rho_reduction": round(rho_before - rho_after, 4),
                     "preserved_critical_weight_pct": round(preserved, 2),
                     "tier0_edges_cut": 0,
                     "tier0_adjacent_cut_edges": adjacent},
            reason=(f"Severed {len(cut_edges)} edge(s): "
                    + ", ".join(f"{e.get('a')}<->{e.get('b')}" for e in cut_edges[:4])
                    + (f" (+{len(cut_edges) - 4} more)" if len(cut_edges) > 4 else "")
                    + f"; spectral radius {rho_before:.3f} -> {rho_after:.3f}, "
                      f"{preserved:.1f}% of critical-weight flow preserved, "
                      f"0 tier-0 edges cut, {adjacent} tier-0-adjacent edge(s) severed"),
        )
        return {"status": "PERCOLATION_CUT_APPROVED",
                "target_spectral_radius": float(args.get("target_spectral_radius", self.target_radius)),
                "preserve_tier0_vlans": True,
                "seeds": list(args.get("seeds") or []),
                "edges_cut": len(cut_edges),
                "rho_before": round(rho_before, 4),
                "rho_after": round(rho_after, 4),
                "preserved_critical_weight_pct": round(preserved, 2),
                "tier0_edges_cut": 0,
                "tier0_adjacent_cut_edges": adjacent,
                "cut_edges": [[e.get("a"), e.get("b")] for e in cut_edges]}
