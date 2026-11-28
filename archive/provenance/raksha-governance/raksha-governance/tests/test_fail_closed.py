"""Fail-closed rule: on any internal error the answer is no, and the
failure itself is recorded in the ledger."""
from __future__ import annotations

from raksha import Governor, HashChainLedger
from raksha.tcb import TwinA, TwinB
from tests.util import quarantine


class ExplodingTwin(TwinB):
    name = "twin-b (crashed)"

    def evaluate(self, action, topology, uptime_current, floor):
        raise ZeroDivisionError("simulated twin crash")


def test_internal_error_denies_fail_closed(clock):
    gov = Governor(clock=clock, ledger=HashChainLedger(),
                   twins=(TwinA(), ExplodingTwin()))
    out = gov.decide(quarantine("ws-11"))
    assert out.status == "DENY"
    assert out.reason == "INTERNAL_GUARD_FAILURE"
    ok, bad = gov.ledger.verify()
    assert ok and bad is None


def test_internal_failure_is_in_the_ledger(clock):
    gov = Governor(clock=clock, ledger=HashChainLedger(),
                   twins=(TwinA(), ExplodingTwin()))
    gov.decide(quarantine("ws-11"))
    reasons = [e.reason for e in gov.ledger.entries]
    assert "INTERNAL_GUARD_FAILURE" in reasons
