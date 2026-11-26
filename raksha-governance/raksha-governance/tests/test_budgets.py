"""Invariant 3 -- blast-radius budgets over a rolling 5-minute window."""
from __future__ import annotations

from raksha import BudgetConfig, Governor
from tests.util import quarantine, sever


def small_budget_gov(clock):
    return Governor(
        clock=clock,
        budget_config=BudgetConfig(max_cuts=2, max_quarantines=2, max_splices=2),
    )


def test_third_quarantine_inside_window_is_refused(clock):
    gov = small_budget_gov(clock)
    assert gov.decide(quarantine("ws-11")).allowed
    assert gov.decide(quarantine("hvac-01")).allowed
    out = gov.decide(quarantine("prn-01"))
    assert out.status == "DENY"
    assert out.reason == "BUDGET_EXCEEDED"


def test_window_slide_re_allows_after_five_minutes(clock):
    gov = small_budget_gov(clock)
    gov.decide(quarantine("ws-11"))
    gov.decide(quarantine("hvac-01"))
    assert gov.decide(quarantine("prn-01")).reason == "BUDGET_EXCEEDED"
    clock.advance(301)  # both reservations fall out of the window
    assert gov.decide(quarantine("prn-01")).allowed


def test_buckets_are_independent(clock):
    gov = small_budget_gov(clock)
    gov.decide(quarantine("ws-11"))
    gov.decide(quarantine("hvac-01"))
    # quarantine budget exhausted, but the cut budget is untouched
    out = gov.decide(sever("e_ws"))  # non-critical edge -> safe cut
    assert out.allowed


def test_escalated_action_consumes_no_budget(gov):
    # Tier-0 without sign-off is escalated, and escalations must not eat
    # the blast-radius budget.
    before = gov.budgets.snapshot()["quarantine"]
    out = gov.decide(
        {
            "tool": "session.terminate",
            "params": {"host": "ehr-primary", "user": "svc-backup"},
            "justification": "evict attacker sessions from EHR host",
            "requested_by": "commander",
        }
    )
    assert out.status == "ESCALATE"
    assert gov.budgets.snapshot()["quarantine"] == before


def test_refused_action_consumes_no_budget(clock):
    gov = small_budget_gov(clock)
    gov.decide(quarantine("pump-01"))  # crown refusal
    assert gov.budgets.snapshot()["quarantine"] == 0
