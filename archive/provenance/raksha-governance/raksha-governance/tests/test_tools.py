"""Invariant 1 -- the 10-tool schema lock: drop, never repair."""
from __future__ import annotations

from raksha import Governor
from raksha.tools import TOOL_REGISTRY


def test_exactly_ten_tools():
    assert len(TOOL_REGISTRY) == 10


def test_unknown_tool_is_dropped(gov):
    out = gov.decide(
        {
            "tool": "os.kill",
            "params": {"pid": "4102"},
            "justification": "kill the malware process",
            "requested_by": "commander",
        }
    )
    assert out.status == "DENY"
    assert out.reason == "UNKNOWN_TOOL"


def test_unlisted_vlan_tool_is_dropped(gov):
    out = gov.decide(
        {
            "tool": "vlan.isolate",
            "params": {"vlan": "icu-7"},
            "justification": "isolate ICU",
            "requested_by": "commander",
        }
    )
    assert out.reason == "UNKNOWN_TOOL"


def test_extra_envelope_field_is_dropped_not_repaired(gov):
    raw = {
        "tool": "host.quarantine",
        "params": {"host": "ws-11"},
        "justification": "contain workstation",
        "requested_by": "commander",
        "sudo": True,
    }
    out = gov.decide(raw)
    assert out.status == "DENY"
    assert out.reason == "SCHEMA_VIOLATION"


def test_missing_justification_is_dropped(gov):
    out = gov.decide({"tool": "host.quarantine", "params": {"host": "ws-11"},
                      "requested_by": "commander"})
    assert out.reason == "SCHEMA_VIOLATION"


def test_extra_param_key_is_dropped(gov):
    out = gov.decide(
        {
            "tool": "host.quarantine",
            "params": {"host": "ws-11", "force": "yes"},
            "justification": "contain workstation",
            "requested_by": "commander",
        }
    )
    assert out.reason == "SCHEMA_VIOLATION"


def test_wrong_param_type_is_dropped(gov):
    out = gov.decide(
        {
            "tool": "host.quarantine",
            "params": {"host": 12345},
            "justification": "contain workstation",
            "requested_by": "commander",
        }
    )
    assert out.reason == "SCHEMA_VIOLATION"


def test_unknown_target_is_dropped(gov):
    out = gov.decide(
        {
            "tool": "host.quarantine",
            "params": {"host": "web-99"},
            "justification": "contain the web server",
            "requested_by": "commander",
        }
    )
    assert out.reason == "UNKNOWN_TARGET"


def test_non_dict_action_is_dropped(gov):
    out = gov.decide("quarantine everything on ward-3")
    assert out.reason == "MALFORMED_ACTION"


def test_digest_is_deterministic(gov):
    raw = {
        "tool": "host.quarantine",
        "params": {"host": "ws-11"},
        "justification": "contain workstation",
        "requested_by": "commander",
    }
    assert gov.decide(raw).action_digest == gov.decide(raw).action_digest


def test_dropped_actions_still_reach_the_ledger(gov):
    gov.decide({"tool": "os.kill", "params": {}, "justification": "x",
                "requested_by": "c"})
    gov.decide("not even a dict")
    assert len(gov.ledger) == 2
    ok, bad_seq = gov.ledger.verify()
    assert ok and bad_seq is None
