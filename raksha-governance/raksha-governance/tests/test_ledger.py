"""Evidence ledger: every decision lands in a tamper-evident hash chain."""
from __future__ import annotations

import json

from tests.util import quarantine, sever


def test_every_decision_is_appended_whatever_the_outcome(gov):
    gov.decide(quarantine("ws-11"))                 # ALLOW
    gov.decide(quarantine("pump-01"))               # DENY (crown)
    gov.decide(                                     # ESCALATE (tier0)
        {
            "tool": "session.terminate",
            "params": {"host": "ehr-primary", "user": "svc-backup"},
            "justification": "evict attacker",
            "requested_by": "commander",
        }
    )
    gov.decide(sever("e_ehr"))                      # DENY (uptime floor)
    assert len(gov.ledger) == 4
    ok, bad = gov.ledger.verify()
    assert ok and bad is None


def test_chain_links_each_entry_to_its_predecessor(gov):
    gov.decide(quarantine("ws-11"))
    gov.decide(sever("e_ws"))
    entries = gov.ledger.entries
    assert entries[0].prev_hash == "0" * 64
    assert entries[1].prev_hash == entries[0].entry_hash


def test_tampering_is_detected_and_located(gov):
    gov.decide(quarantine("ws-11"))
    gov.decide(sever("e_ws"))
    gov.decide(quarantine("hvac-01"))
    # an attacker (or a careless admin) edits history in the middle:
    gov.ledger.entries[1].status = "DENY"
    ok, bad_seq = gov.ledger.verify()
    assert not ok
    assert bad_seq == 1


def test_jsonl_export_round_trips(gov):
    gov.decide(quarantine("ws-11"))
    gov.decide(sever("e_ws"))
    lines = [json.loads(line) for line in gov.ledger.to_jsonl().splitlines()]
    assert len(lines) == 2
    assert {"seq", "ts", "actor", "tool", "status", "reason",
            "entry_hash"} <= set(lines[0])
    assert lines[0]["entry_hash"] == gov.ledger.entries[0].entry_hash


def test_ledger_entries_carry_human_explanations(gov):
    gov.decide(quarantine("pump-01"))
    detail = gov.ledger.entries[0].detail
    assert "ICU" in detail  # the generalist can read why
