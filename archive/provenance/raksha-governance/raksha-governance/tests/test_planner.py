"""Part 3 -- containment planner: determinism, the hard constraint, the
objective math, and the promise that it never proposes what the Governor
must refuse."""
from __future__ import annotations

import pytest

from raksha.fixtures import hospital_fixture
from raksha.planner import ContainmentPlanner, Plan

SEEDS = ("prn-01", "ws-11")   # compromised guest-5 printer + ward-3 workstation


def test_candidate_space_is_exactly_ten_and_never_crown():
    topo = hospital_fixture()
    planner = ContainmentPlanner(topo)
    assert len(planner.candidates) == 10
    crown_edges = {e.id for e in topo.edges.values()
                   if topo.is_crown_host(e.a) or topo.is_crown_host(e.b)}
    assert crown_edges == {"e_pump", "e_vent"}
    assert not (set(planner.candidates) & crown_edges)
    # floor-fatal edges are excluded too: no sign-off can buy the floor
    assert "e_ehr" not in planner.candidates
    assert "e_ad" not in planner.candidates


def test_optimal_plan_for_the_lateral_movement_incident():
    """Seeds prn-01 (guest) and ws-11 (ward). The lateral links x1/x2/x3
    mean no single uplink cut contains them; the unique minimum-J feasible
    cut set is {e_prn1, e_ws, x2, x3}:
      J = 4 + 2 * (15/32) + 0 + 0 = 4.9375
    It touches no Tier-0 edge (A=0) and no critical flow (R=0)."""
    plan = ContainmentPlanner(hospital_fixture()).plan_for_hosts(SEEDS)
    assert plan.feasible
    assert plan.cuts == ("e_prn1", "e_ws", "x2", "x3")
    assert plan.C == 4
    assert plan.A == 0
    assert plan.R == 0
    assert plan.D == pytest.approx(15 / 32)
    assert plan.J == pytest.approx(4 + 2 * (15 / 32))


def test_hard_constraint_holds_and_is_recomputed():
    from raksha.planner import _reachable_from, _tier0_hosts

    topo = hospital_fixture()
    plan = ContainmentPlanner(topo).plan_for_hosts(SEEDS)
    reachable = _reachable_from(plan.seeds, topo, frozenset(plan.cuts))
    assert not (reachable & _tier0_hosts(topo))


def test_plan_never_touches_crown_edges_and_critical_uplinks():
    topo = hospital_fixture()
    plan = ContainmentPlanner(topo).plan_for_hosts(SEEDS)
    for eid in plan.cuts:
        edge = topo.edges[eid]
        assert not edge.critical                       # critical flow untouched
        assert not (topo.is_tier0_host(edge.a) or topo.is_tier0_host(edge.b))


def test_planner_is_deterministic():
    p1 = ContainmentPlanner(hospital_fixture()).plan_for_hosts(SEEDS)
    p2 = ContainmentPlanner(hospital_fixture()).plan_for_hosts(SEEDS)
    assert p1 == p2


def test_plan_actions_pass_the_governor_individually():
    """DoD: every emitted edge-sever is independently re-verified by the
    Governor; the optimal plan needs no sign-off at all."""
    from raksha import BudgetConfig, Governor

    plan = ContainmentPlanner(hospital_fixture()).plan_for_hosts(SEEDS)
    gov = Governor(budget_config=BudgetConfig(max_cuts=6))
    for raw in plan.as_actions():
        out = gov.decide(raw)
        assert out.allowed, (raw, out.reason)


def test_tier0_adjacent_edge_is_priced_but_not_chosen():
    """x4 lands on the EHR host: legal with sign-off, priced by nu*A, and
    correctly LOSES to the collateral route because a sign-off-free
    feasible plan exists."""
    planner = ContainmentPlanner(hospital_fixture())
    assert "x4" in planner.candidates           # in the space...
    plan = planner.plan_for_hosts(SEEDS)
    assert "x4" not in plan.cuts                # ...but not chosen


def test_single_seed_needs_a_single_cut():
    """A seed whose only route is its own uplink is contained by cutting
    exactly that uplink (plus nothing else)."""
    plan = ContainmentPlanner(hospital_fixture()).plan_for_hosts(("prn-02",))
    assert plan.feasible
    assert plan.cuts == ("e_prn2",)
    # J = 1 cut + 2 * (1/32 non-Tier-0 flow share)
    assert plan.J == pytest.approx(1 + 2 * (1 / 32))


def test_crown_seed_is_infeasible_and_escalates():
    """A seed already inside the ICU VLAN cannot be contained by cuts the
    planner is allowed to make: refuse and escalate, never improvise."""
    plan = ContainmentPlanner(hospital_fixture()).plan_for_hosts(("pump-01",))
    assert not plan.feasible
    assert plan.cuts == ()
    assert "escalate" in plan.note
