"""Invariant 5 -- the uptime watchdog: floor pre-check and force-revert."""
from __future__ import annotations

from raksha import BudgetConfig, Governor
from raksha.fido2 import generate_signer
from tests.util import sever, sign_into


def test_projected_floor_refuses_severing_the_ehr_uplink(gov, signer_priv, now):
    # e_ehr carries 40 of 100.05 critical weight: projected uptime 0.60.
    # Even a valid FIDO2 signature cannot buy this; the floor is physics.
    raw = sign_into(sever("e_ehr"), signer_priv, "on-call", now)
    out = gov.decide(raw)
    assert out.status == "DENY"
    assert out.reason == "UPTIME_FLOOR"


def test_tiny_critical_cut_passes_floor_with_signoff(gov, signer_priv, now):
    # e_ad2 carries 0.05 of 100.05: projected 0.9995 >= floor 0.999.
    raw = sign_into(sever("e_ad2"), signer_priv, "on-call", now)
    out = gov.decide(raw)
    assert out.status == "ALLOW"
    assert out.reason == "ALLOWED_WITH_TIER0_OVERRIDE"


def test_watchdog_force_reverts_below_floor_even_when_budget_exhausted(clock):
    gov = Governor(clock=clock, budget_config=BudgetConfig(max_cuts=1))
    raw = {
        "tool": "edge.sever",
        "params": {"edge": "e_ad2"},
        "justification": "contain lateral movement",
        "requested_by": "commander",
    }
    priv, pub = generate_signer()
    gov.fido.register("on-call", pub)
    signed = sign_into(raw, priv, "on-call", clock())
    assert gov.decide(signed).allowed  # uses the single allowed cut

    # budget now exhausted for cuts:
    out = gov.decide(sever("e_ws"))
    assert out.reason == "BUDGET_EXCEEDED"

    # monitor reports critical uptime below the floor:
    revert = gov.force_revert(0.9985)
    assert revert.allowed
    assert revert.reason == "WATCHDOG_FORCE_REVERT"
    assert revert.tool == "edge.restore"
    assert len(gov.reverts) == 0  # registry emptied: change has been reverted


def test_watchdog_escalates_when_nothing_is_revertible(gov):
    out = gov.force_revert(0.5)
    assert out.status == "ESCALATE"
    assert out.reason == "HUMAN_REQUIRED"


def test_watchdog_idle_when_uptime_is_above_floor(gov):
    out = gov.force_revert(0.9999)
    assert out.reason == "WATCHDOG_IDLE"


def test_watchdog_decisions_are_in_the_ledger(gov):
    gov.force_revert(0.5)
    entries = [(e.actor, e.reason) for e in gov.ledger.entries]
    assert ("watchdog", "HUMAN_REQUIRED") in entries
