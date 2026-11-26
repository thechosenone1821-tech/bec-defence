"""TCB twins: when the twins disagree, the answer is always no."""
from __future__ import annotations

from raksha import Decision, DENY, ESCALATE, EMPTY_METADATA, Governor, parse_action
from raksha.decisions import decisions_agree
from raksha.fixtures import hospital_fixture
from raksha.tcb import TwinA, TwinB
from tests.util import quarantine


class LyingTwin(TwinB):
    """A twin that always denies with the crown reason."""

    name = "twin-b (compromised)"

    def evaluate(self, action, topology, uptime_current, floor):
        return Decision(DENY, "CROWN_JEWEL_LOCK", EMPTY_METADATA, "no")



class PanickingTwin(TwinB):
    """A twin with the same reason but a different status."""

    name = "twin-b (panicking)"

    def evaluate(self, action, topology, uptime_current, floor):
        return Decision(
            ESCALATE,
            "FIDO2_REQUIRED",
            (("bucket", "quarantine"), ("crown", False),
             ("projected_uptime", 1.0), ("severed_critical", 0.0),
             ("tier0", True)),  # lies in the metadata
            "escalate everything",
        )


def test_twins_agree_on_a_benign_action(gov):
    out = gov.decide(quarantine("ws-11"))
    assert out.allowed


def test_disagreement_is_a_refusal(clock):
    gov = Governor(clock=clock, twins=(TwinA(), LyingTwin()))
    out = gov.decide(quarantine("ws-11"))
    assert out.status == "DENY"
    assert out.reason == "TCB_DISAGREEMENT"


def test_metadata_disagreement_is_also_a_refusal(clock):
    gov = Governor(clock=clock, twins=(TwinA(), PanickingTwin()))
    out = gov.decide(quarantine("ws-11"))
    assert out.reason == "TCB_DISAGREEMENT"


def test_disagreement_is_recorded_in_the_ledger(clock):
    gov = Governor(clock=clock, twins=(TwinA(), LyingTwin()))
    gov.decide(quarantine("ws-11"))
    assert any(
        e.reason == "TCB_DISAGREEMENT" for e in gov.ledger.entries
    )


def test_twin_b_independent_touch_checks_match_twin_a(gov):
    # Sanity: for every fixture host target, the two twins' policy verdicts
    # agree even before the Governor compares them.
    topo = hospital_fixture()
    for host in topo.hosts:
        action, _, _ = parse_action(quarantine(host), topo)
        assert action is not None
        va = TwinA().evaluate(action, topo, 1.0, topo.critical_floor)
        vb = TwinB().evaluate(action, topo, 1.0, topo.critical_floor)
        assert decisions_agree(va, vb), f"twins disagree for host {host}"
