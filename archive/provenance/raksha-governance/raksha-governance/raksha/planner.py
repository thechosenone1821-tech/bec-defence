"""Containment planner (Part 3 of the governance build).

    minimise   J = C + lambda*D + mu*R + nu*A
      C = cut size (edges severed)
      D = fraction of non-crown, non-Tier-0-adjacent candidate flow severed
      R = mission-critical flow still reachable from the seeds
      A = severed edges touching a Tier-0 asset
    constraint  reach(seeds -> Tier-0) = empty

The candidate space is the fixture topology's non-crown edges the TCB
twins would not outright refuse (crown-adjacent edges are excluded by the
crown-jewel lock, floor-fatal edges excluded because no sign-off can buy
the uptime floor). Sign-off-requiring edges (ESCALATE) stay in the space
and are priced by nu*A: the planner may propose them, the Governor then
parks them until a human signs. The consolidated fixture yields exactly
ten candidates, so the optimiser is EXHAUSTIVE over all 2^10 subsets:
deterministic, no randomness, no ML. Calling it "AI-optimised" would be a
lie. Ties break to the lexicographically smallest cut set.

Honesty notes (carried from the spec, still true):
  * all flow numbers are FIXTURE-measured (fixtures.py edge weights);
  * lambda, mu, nu are HAND-PICKED below, not yet tuned from outcomes.

The planner proposes; it never executes. Its output is a raw action list
in which every entry must pass Governor.decide() like everything else.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from .fixtures import Topology, hospital_fixture
from .policy import severed_critical_weight
from .tcb import DEFAULT_TWINS
from .tools import parse_action

# Hand-picked objective weights (spec, known gap 3). Changing these is a
# governance act: it changes which cuts the hospital considers "cheap".
PLANNER_LAMBDA = 2.0   # collateral: share of non-Tier-0 candidate flow severed
PLANNER_MU = 10.0      # residual: critical flow still reachable from seeds
PLANNER_NU = 8.0       # adverse: each severed edge touching a Tier-0 asset


@dataclass(frozen=True)
class Plan:
    plan_id: str
    seeds: Tuple[str, ...]           # seed host ids
    cuts: Tuple[str, ...]            # edge ids, sorted
    feasible: bool
    J: float
    C: int
    D: float
    R: float
    A: int
    subsets_evaluated: int
    candidates: Tuple[str, ...]
    note: str = ""

    def as_actions(self) -> List[dict]:
        """The plan as raw action envelopes. Each one still has to pass
        Governor.decide() -- the planner proposes, it never executes."""
        return [
            {
                "tool": "edge.sever",
                "params": {"edge": edge_id},
                "justification": f"containment plan {self.plan_id}: isolate seeds",
                "requested_by": "planner",
            }
            for edge_id in self.cuts
        ]


def _tier0_hosts(topology: Topology) -> FrozenSet[str]:
    return frozenset(h for h in topology.hosts if topology.is_tier0_host(h))


def _reachable_from(seeds: Sequence[str], topology: Topology,
                    removed: FrozenSet[str]) -> FrozenSet[str]:
    adj: Dict[str, set] = {}
    for e in topology.edges.values():
        if e.id in removed:
            continue
        adj.setdefault(e.a, set()).add(e.b)
        adj.setdefault(e.b, set()).add(e.a)
    seen: set = set()
    stack = list(seeds)
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for nb in adj.get(cur, ()):
            if nb not in seen:
                stack.append(nb)
    return frozenset(seen)


def _reachable_critical_weight(seeds: Sequence[str], topology: Topology,
                               removed: FrozenSet[str]) -> float:
    """R: total weight of critical edges the seeds can still touch."""
    seen = _reachable_from(seeds, topology, removed)
    return sum(
        e.weight
        for e in topology.edges.values()
        if e.critical and (e.a in seen or e.b in seen)
    )


class ContainmentPlanner:
    def __init__(self, topology: Optional[Topology] = None,
                 twins=None, floor: Optional[float] = None) -> None:
        self.topo = topology if topology is not None else hospital_fixture()
        self.floor = floor if floor is not None else self.topo.critical_floor
        self.twin_a, self.twin_b = twins if twins is not None else DEFAULT_TWINS
        self.tier0 = _tier0_hosts(self.topo)
        self.candidates = self._candidate_edges()

    # ------------------------------------------------------------------
    def _candidate_edges(self) -> Tuple[str, ...]:
        """Non-crown edges the twins would not outright refuse.

        Probe each edge.sever through TwinA at full uptime: DENY means the
        Governor must refuse it (crown lock or uptime floor), so the
        planner never proposes it. ESCALATE (sign-off required) stays --
        it is priced by nu*A and gated by FIDO2 downstream.
        """
        candidates: List[str] = []
        for edge_id in sorted(self.topo.edges):
            raw = {
                "tool": "edge.sever",
                "params": {"edge": edge_id},
                "justification": "planner candidate feasibility probe",
                "requested_by": "planner",
            }
            action, reason, _ = parse_action(raw, self.topo)
            if action is None:
                raise RuntimeError(f"probe failed schema for {edge_id}: {reason}")
            verdict = self.twin_a.evaluate(action, self.topo, 1.0, self.floor)
            if verdict.status != "DENY":
                candidates.append(edge_id)
        return tuple(candidates)

    # ------------------------------------------------------------------
    def plan_for_hosts(self, seed_hosts: Sequence[str]) -> Plan:
        unknown = [h for h in seed_hosts if h not in self.topo.hosts]
        if unknown:
            raise ValueError(f"unknown seed hosts {unknown}")
        return self.plan(tuple(seed_hosts))

    def plan(self, seeds: Tuple[str, ...]) -> Plan:
        cand_ids = list(self.candidates)
        n = len(cand_ids)
        non_t0 = [eid for eid in cand_ids
                  if not (self.topo.edges[eid].a in self.tier0
                          or self.topo.edges[eid].b in self.tier0)]
        non_t0_total = sum(self.topo.edges[eid].weight for eid in non_t0) or 1.0

        best_key = None
        best = None
        feasible_found = 0
        for mask in range(1 << n):
            cuts = frozenset(eid for i, eid in enumerate(cand_ids)
                             if (mask >> i) & 1)
            # HARD CONSTRAINT: no Tier-0 host reachable from the seeds.
            if _reachable_from(seeds, self.topo, cuts) & self.tier0:
                continue
            feasible_found += 1
            c = len(cuts)
            severed = sum(self.topo.edges[eid].weight
                          for eid in cuts if eid in set(non_t0))
            d = severed / non_t0_total
            r = _reachable_critical_weight(seeds, self.topo, cuts)
            a = sum(1 for eid in cuts if eid not in set(non_t0))
            j = c + PLANNER_LAMBDA * d + PLANNER_MU * r + PLANNER_NU * a
            key = (j, sorted(cuts))
            if best_key is None or key < best_key:
                best_key = key
                best = (cuts, c, d, r, a, j)

        seeds = tuple(sorted(seeds))
        if best is None:
            return Plan(
                plan_id="plan-infeasible", seeds=seeds, cuts=(), feasible=False,
                J=float("inf"), C=0, D=0.0,
                R=_reachable_critical_weight(seeds, self.topo, frozenset()),
                A=0, subsets_evaluated=1 << n, candidates=tuple(cand_ids),
                note=("no subset of candidate cuts satisfies "
                      "reach(seeds->Tier-0)=empty; escalate to humans"),
            )

        cuts, c, d, r, a, j = best
        # defense in depth: crown uplinks are never candidates, assert it
        crown_edges = {e.id for e in self.topo.edges.values()
                       if self.topo.is_crown_host(e.a) or self.topo.is_crown_host(e.b)}
        assert not (cuts & crown_edges), "plan touches a crown edge"
        plan_id = "plan-" + hashlib.sha256(
            ("|".join(seeds) + "|" + ",".join(sorted(cuts))).encode()
        ).hexdigest()[:10]
        return Plan(
            plan_id=plan_id, seeds=seeds, cuts=tuple(sorted(cuts)),
            feasible=True, J=j, C=c, D=d, R=r, A=a,
            subsets_evaluated=1 << n, candidates=tuple(cand_ids),
            note=(f"exhaustive over {1 << n} subsets, {feasible_found} feasible; "
                  f"constraint reach(seeds->Tier-0)=empty enforced"),
        )
