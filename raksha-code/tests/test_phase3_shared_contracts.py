"""Compatibility-cwd shared-contract tests for the active build."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from packages.contracts import (  # noqa: E402
    BACKEND_CONTRACT_VERSION, LEGACY_BANDS, REASON_CATALOGUE,
    canonical_json, contract_card, sign_event, validate_envelope,
)
from packages.contracts.reasons import reason_for  # noqa: E402


def test_canonical_json_is_stable():
    assert canonical_json({"b": 1, "a": {"d": 2, "c": [1, 2]}}) == '{"a":{"c":[1,2],"d":2},"b":1}'


def test_reason_catalogue_and_bands_are_single_source():
    assert len(REASON_CATALOGUE) == 29
    assert reason_for("MSG-CRED-OTP-SHARE") is not None
    assert LEGACY_BANDS["CRITICAL"] == 0.99


def test_signed_event_and_backend_card_are_actionable():
    event = {
        "event_id": "EV-ACTIVE-1", "timestamp_utc": "2026-11-26T09:00:00Z",
        "ring": "RING_0_CITIZEN", "organ": "CITIZEN_APP",
        "signal_type": "CITIZEN_REPORT_MESSAGE", "severity": 0.5,
        "entities": {}, "metrics": {},
    }
    signed = sign_event(event)
    assert validate_envelope(signed, require_signature=True).actionable is True
    card = contract_card()
    assert card["contract"] == BACKEND_CONTRACT_VERSION == "raksha-backend-v1"
    assert card["signature_required"] is True and card["governor_required"] is True
