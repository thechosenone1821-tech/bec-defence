"""Invariant 4 -- FIDO2 step-up: Tier-0 needs a real, fresh signature."""
from __future__ import annotations

import base64

from raksha.fido2 import make_assertion
from raksha.tools import digest_for
from tests.util import quarantine, sign_into

TIER0_TERMINATE = {
    "tool": "session.terminate",
    "params": {"host": "ehr-primary", "user": "svc-backup"},
    "justification": "evict attacker sessions from the EHR host",
    "requested_by": "commander",
}


def test_tier0_without_assertion_is_escalated(gov):
    out = gov.decide(TIER0_TERMINATE)
    assert out.status == "ESCALATE"
    assert out.reason == "FIDO2_REQUIRED"


def test_tier0_with_valid_assertion_is_allowed(gov, signer_priv, now):
    raw = sign_into(TIER0_TERMINATE, signer_priv, "on-call", now)
    out = gov.decide(raw)
    assert out.status == "ALLOW"
    assert out.reason == "ALLOWED_WITH_TIER0_OVERRIDE"


def test_tier0_with_invalid_assertion_is_refused(gov, signer_priv, now):
    raw = sign_into(TIER0_TERMINATE, signer_priv, "on-call", now)
    raw["assertion"]["sig"] = base64.b64encode(b"\x00" * 64).decode("ascii")
    out = gov.decide(raw)
    assert out.status == "DENY"
    assert out.reason == "FIDO2_INVALID"


def test_replayed_assertion_is_refused(gov, signer_priv, now):
    raw = sign_into(TIER0_TERMINATE, signer_priv, "on-call", now)
    assert gov.decide(raw).allowed
    replay = gov.decide(raw)  # same counter again
    assert replay.status == "DENY"
    assert replay.reason == "FIDO2_REPLAY"


def test_stale_assertion_is_refused(gov, signer_priv, now):
    raw = sign_into(TIER0_TERMINATE, signer_priv, "on-call", now - 1000)
    out = gov.decide(raw)
    assert out.reason == "FIDO2_EXPIRED"


def test_assertion_bound_to_another_action_is_refused(gov, signer_priv, now):
    other = quarantine("ws-11")
    wrong = make_assertion(
        signer_priv, digest_for(other), now, 1, "on-call"
    )
    raw = {**TIER0_TERMINATE, "assertion": wrong}
    out = gov.decide(raw)
    assert out.reason == "FIDO2_INVALID"


def test_unknown_signer_is_refused(gov, signer_priv, now):
    raw = sign_into(TIER0_TERMINATE, signer_priv, "on-call", now)
    raw["assertion"]["signer"] = "ghost-admin"
    out = gov.decide(raw)
    assert out.reason == "FIDO2_INVALID"


def test_tier0_identity_rotation_needs_signoff_but_low_tier_does_not(gov):
    out = gov.decide(
        {
            "tool": "creds.rotate",
            "params": {"identity": "svc-ehr-backup"},
            "justification": "suspected credential theft",
            "requested_by": "commander",
        }
    )
    assert out.status == "ESCALATE"
    out = gov.decide(
        {
            "tool": "creds.rotate",
            "params": {"identity": "svc-print"},
            "justification": "routine rotation",
            "requested_by": "commander",
        }
    )
    assert out.allowed
