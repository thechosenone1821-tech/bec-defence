"""Envelope tests: canonical JSON, HMAC round-trip, quarantine states, validation."""

from __future__ import annotations

import json

import pytest

from raksha.events import (Event, EventValidationError, VerifyState, canonical,
                           sign_event, tamper_event, verify_event)

KEY = b"events-test-key-0123456789abcdef"


def base_event() -> Event:
    return Event("EV-1", "2026-01-01T00:00:00Z", "voiceguard", "C-1", "case-1", "citizen",
                 4, "N-VICTIM-PHONE", "synthetic voice", {"synth_score": 0.93})


def test_canonical_is_stable_and_order_independent() -> None:
    a = canonical({"b": 1, "a": {"d": 2, "c": [1, 2]}})
    b = canonical({"a": {"c": [1, 2], "d": 2}, "b": 1})
    assert a == b == '{"a":{"c":[1,2],"d":2},"b":1}'


def test_sign_verify_roundtrip() -> None:
    event = base_event()
    sign_event(event, KEY)
    assert verify_event(event, KEY) is VerifyState.VALID


def test_tamper_after_signing_is_detected() -> None:
    event = base_event()
    sign_event(event, KEY)
    tamper_event(event)
    assert verify_event(event, KEY) is VerifyState.TAMPERED


def test_any_field_flip_is_detected() -> None:
    event = base_event()
    sign_event(event, KEY)
    event.entity = "N-OTHER"
    assert verify_event(event, KEY) is VerifyState.TAMPERED


def test_unsigned_is_unsigned() -> None:
    assert verify_event(base_event(), KEY) is VerifyState.UNSIGNED


def test_wrong_key_is_tampered() -> None:
    event = base_event()
    sign_event(event, KEY)
    assert verify_event(event, b"another-key-----------------------") is VerifyState.TAMPERED


def test_sig_excluded_from_signing_body() -> None:
    event = base_event()
    before = event.signing_body()
    assert "sig" not in before and "sig_alg" not in before  # nothing set yet
    sign_event(event, KEY)
    body = event.signing_body()
    assert "sig" not in body and body["sig_alg"] == "HMAC-SHA256"
    assert body == event.signing_body()  # stable after signing
    original_sig = event.sig
    event.sig = "f" * 64
    assert event.signing_body() == body  # the sig VALUE never affects the body
    event.sig = original_sig


@pytest.mark.parametrize("mutate, text", [
    (lambda d: d.pop("organ"), "missing envelope fields"),
    (lambda d: d.update(leg="space"), "leg must be one of"),
    (lambda d: d.update(severity=6), "severity"),
    (lambda d: d.update(severity="4"), "severity"),
    (lambda d: d.update(payload=[]), "payload must be a JSON object"),
    (lambda d: d.update(entity=""), "non-empty string"),
])
def test_validation_rejects_malformed_envelopes(mutate, text) -> None:
    raw = base_event().to_dict()
    mutate(raw)
    with pytest.raises(EventValidationError, match=text):
        Event.from_dict(raw)


def test_from_dict_roundtrip_preserves_signature() -> None:
    event = base_event()
    sign_event(event, KEY)
    rebuilt = Event.from_dict(json.loads(json.dumps(event.to_dict())))
    assert verify_event(rebuilt, KEY) is VerifyState.VALID
