"""Invariant 2 -- the crown-jewel lock: the ICU VLAN is never touched.

The lock is absolute. A valid FIDO2 assertion signed by a real key cannot
buy it, because human sign-off overrides Tier-0 actions, never crown ones.
"""
from __future__ import annotations

from tests.util import quarantine, sever, sign_into


def test_quarantine_icu_pump_is_refused(gov):
    out = gov.decide(quarantine("pump-01", "suspected compromise in ICU"))
    assert out.status == "DENY"
    assert out.reason == "CROWN_JEWEL_LOCK"


def test_severing_an_icu_edge_is_refused(gov):
    out = gov.decide(sever("e_pump"))
    assert out.reason == "CROWN_JEWEL_LOCK"


def test_moving_an_icu_host_is_refused(gov):
    out = gov.decide(
        {
            "tool": "vlan.move",
            "params": {"host": "vent-02", "to_vlan": "remediation-9"},
            "justification": "move ventilator to remediation VLAN",
            "requested_by": "commander",
        }
    )
    assert out.reason == "CROWN_JEWEL_LOCK"


def test_valid_fido2_cannot_buy_the_crown_lock(gov, signer_priv, now):
    raw = sign_into(quarantine("pump-01"), signer_priv, "on-call", now)
    out = gov.decide(raw)
    assert out.status == "DENY"
    assert out.reason == "CROWN_JEWEL_LOCK"


def test_read_only_snapshot_of_crown_host_is_allowed(gov):
    # The crown lock stops DISRUPTION. Read-only observation is permitted
    # (and still logged like every other decision).
    out = gov.decide(
        {
            "tool": "snapshot.capture",
            "params": {"host": "pump-01"},
            "justification": "forensic image of infusion pump",
            "requested_by": "commander",
        }
    )
    assert out.status == "ALLOW"
    assert out.reason == "ALLOWED_STANDARD"


def test_crown_refusals_are_in_the_ledger(gov):
    gov.decide(quarantine("pump-01"))
    reasons = [e.reason for e in gov.ledger.entries]
    assert "CROWN_JEWEL_LOCK" in reasons
