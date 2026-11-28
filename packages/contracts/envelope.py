"""Phase 3 — one signed-event validation contract.

Three shipped envelope profiles are accepted and normalised identically:

* ``organ-telemetry-v1`` — spine/Citizen/RAAVAN/eval organ events (``mac`` field).
* ``organ-sealed-v1`` — legacy BaseOrgan events (``mac`` + ``signature``).
* ``enterprise-i1-v1`` — enterprise I1 dataclass envelopes (``sig`` + ``sig_alg``).

The wire shape is preserved for compatibility; validation normalises every
profile into one canonical result. Signature verification and Governor gating
are both required before an event can become actionable.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from .canonical import canonical_bytes
from .config import BUS_KEY_ENV, RPC_KEY_ENV, SENSOR_KEY_ENV

CONTRACT_VERSION = "raksha-event-v1"
PROFILE_ORGAN_TELEMETRY = "organ-telemetry-v1"
PROFILE_ORGAN_SEALED = "organ-sealed-v1"
PROFILE_ENTERPRISE_I1 = "enterprise-i1-v1"
SIG_ALG = "HMAC-SHA256"
SIG_FIELD = "sig"
MAC_FIELD = "mac"

_DEV_BUS_KEY = "eigenshield-dev-bus-key-change-in-production"
_DEV_RPC_KEY = "eigenshield-dev-rpc-secret-do-not-use-in-prod"
I1_REQUIRED = ("event_id", "ts", "organ", "campaign_id", "case_id", "leg",
               "severity", "entity", "summary", "payload")
I1_LEGS = ("citizen", "infra")
I1_STRING_FIELDS = ("event_id", "ts", "organ", "entity", "summary")


class EnvelopeValidationError(ValueError):
    """The envelope is structurally unusable and cannot be trusted."""


class VerificationState(str, Enum):
    VALID = "valid"
    TAMPERED = "tampered"
    UNSIGNED = "unsigned"
    KEY_MISSING = "key_missing"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class CanonicalEnvelope:
    contract: str
    profile: str
    event_id: str
    ts: str
    organ: str
    leg: str
    severity: float
    severity_raw: Any
    severity_scale: str
    signal_type: str
    reason: str
    entities: dict[str, Any]
    metrics: dict[str, Any]
    payload: dict[str, Any]
    signature: dict[str, Any]
    state: VerificationState
    verified: bool
    actionable: bool
    governor_required: bool
    signature_required: bool

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["state"] = self.state.value
        return out


def _coerce_key(key: Any) -> bytes | None:
    if key is None:
        return None
    if isinstance(key, bytes):
        return key
    return str(key).encode()


def bus_key() -> bytes:
    return os.environ.get(BUS_KEY_ENV, _DEV_BUS_KEY).encode()


def rpc_key() -> bytes:
    return os.environ.get(RPC_KEY_ENV, _DEV_RPC_KEY).encode()


DEFAULT_INGEST_KEY = b"raksha-phase678-dev-sensor-key"


def ingest_key() -> bytes:
    """Return the key the shared runtime verifies ingested envelopes with.

    ``SafetyRuntime`` resolves its sensor key from ``RAKSHA_SENSOR_KEY`` and
    falls back to the development default. Any producer that wants its
    envelopes to verify — the Python gateway, and the Citizen app forwarding a
    signed report — must resolve the key the same way, in one place.
    """
    raw = os.environ.get(SENSOR_KEY_ENV, "")
    return raw.encode() if raw else DEFAULT_INGEST_KEY


def sensor_key() -> bytes | None:
    raw = os.environ.get(SENSOR_KEY_ENV, "")
    if not raw:
        return None
    try:
        return bytes.fromhex(raw)
    except ValueError:
        return raw.encode()


def profile_for(raw: dict[str, Any]) -> str:
    if not isinstance(raw, dict):
        raise EnvelopeValidationError("envelope must be a JSON object")
    if SIG_FIELD in raw or "sig_alg" in raw or all(k in raw for k in I1_REQUIRED):
        return PROFILE_ENTERPRISE_I1
    if "signature" in raw and (MAC_FIELD not in raw or raw.get(MAC_FIELD) == raw.get("signature")):
        return PROFILE_ORGAN_SEALED
    if any(k in raw for k in ("timestamp_utc", "ring", "signal_type", "entities", "metrics", MAC_FIELD)):
        return PROFILE_ORGAN_TELEMETRY
    raise EnvelopeValidationError("unsupported envelope profile")


def _validate_i1(raw: dict[str, Any]) -> None:
    missing = [k for k in I1_REQUIRED if k not in raw]
    if missing:
        raise EnvelopeValidationError(f"missing envelope fields: {', '.join(missing)}")
    if raw.get("leg") not in I1_LEGS:
        raise EnvelopeValidationError(f"leg must be one of {I1_LEGS}, got {raw.get('leg')!r}")
    severity = raw["severity"]
    if not isinstance(severity, int) or not 1 <= severity <= 5:
        raise EnvelopeValidationError("severity must be an integer in [1,5]")
    if not isinstance(raw["payload"], dict):
        raise EnvelopeValidationError("payload must be a JSON object")
    for key in I1_STRING_FIELDS:
        if not isinstance(raw[key], str) or not raw[key]:
            raise EnvelopeValidationError(f"{key} must be a non-empty string")


def _signature_info(raw: dict[str, Any], profile: str) -> tuple[str, str | None, str | None]:
    if profile == PROFILE_ENTERPRISE_I1:
        return SIG_FIELD, raw.get(SIG_FIELD), raw.get("sig_alg")
    if profile == PROFILE_ORGAN_SEALED:
        return MAC_FIELD, raw.get(MAC_FIELD) or raw.get("signature"), SIG_ALG
    return MAC_FIELD, raw.get(MAC_FIELD), SIG_ALG


def _signing_body(raw: dict[str, Any], profile: str) -> dict[str, Any]:
    if profile == PROFILE_ENTERPRISE_I1:
        return {k: v for k, v in raw.items() if k != SIG_FIELD}
    if profile == PROFILE_ORGAN_SEALED:
        return {k: v for k, v in raw.items() if k not in (MAC_FIELD, "signature", "verified")}
    return {k: v for k, v in raw.items() if k not in (MAC_FIELD, "verified")}


def _key_for(profile: str, key: Any) -> bytes | None:
    supplied = _coerce_key(key)
    if supplied is not None:
        return supplied
    if profile == PROFILE_ENTERPRISE_I1:
        return sensor_key()
    if profile == PROFILE_ORGAN_SEALED:
        return rpc_key()
    return bus_key()


def _mac(body: dict[str, Any], key: bytes) -> str:
    return hmac.new(key, canonical_bytes(body), hashlib.sha256).hexdigest()


def sign_event(event: dict[str, Any], key: Any = None, *, profile: str | None = None) -> dict[str, Any]:
    """Sign one supported wire envelope using the shared canonical JSON rule."""
    raw = dict(event)
    profile = profile or profile_for(raw)
    if profile == PROFILE_ENTERPRISE_I1:
        _validate_i1(raw)
    signing_key = _key_for(profile, key)
    if signing_key is None:
        raise EnvelopeValidationError("enterprise I1 signing requires an explicit sensor key")
    body = _signing_body(raw, profile)
    if profile == PROFILE_ENTERPRISE_I1:
        body["sig_alg"] = SIG_ALG
        body[SIG_FIELD] = _mac({k: v for k, v in body.items() if k != SIG_FIELD}, signing_key)
        return body
    mac = _mac(body, signing_key)
    body[MAC_FIELD] = mac
    if profile == PROFILE_ORGAN_SEALED:
        body["signature"] = mac
    return body


def verify_signature(event: dict[str, Any], key: Any = None) -> VerificationState:
    """Return the verification state for any supported shipped envelope."""
    if not isinstance(event, dict):
        return VerificationState.UNSUPPORTED
    try:
        profile = profile_for(event)
    except EnvelopeValidationError:
        return VerificationState.UNSUPPORTED
    if profile == PROFILE_ENTERPRISE_I1:
        try:
            _validate_i1(event)
        except EnvelopeValidationError:
            return VerificationState.UNSUPPORTED
    field, value, _ = _signature_info(event, profile)
    if not isinstance(value, str) or len(value) != 64:
        return VerificationState.UNSIGNED
    signing_key = _key_for(profile, key)
    if signing_key is None:
        return VerificationState.KEY_MISSING
    expected = _mac(_signing_body(event, profile), signing_key)
    return VerificationState.VALID if hmac.compare_digest(expected, value.lower()) else VerificationState.TAMPERED


def verify_event(event: dict[str, Any], key: Any = None) -> bool:
    """Legacy-friendly boolean wrapper around :func:`verify_signature`."""
    return verify_signature(event, key=key) is VerificationState.VALID


def _normalised_severity(raw: dict[str, Any], profile: str) -> tuple[float, Any, str]:
    value = raw.get("severity", 0.0)
    if profile == PROFILE_ENTERPRISE_I1:
        try:
            return max(0.0, min(1.0, float(value) / 5.0)), value, "i1-integer-1-5"
        except (TypeError, ValueError):
            return 0.0, value, "i1-integer-1-5"
    try:
        return max(0.0, min(1.0, float(value))), value, "unit-interval"
    except (TypeError, ValueError):
        return 0.0, value, "unit-interval"


def validate_envelope(raw: dict[str, Any], key: Any = None, *, require_signature: bool = True) -> CanonicalEnvelope:
    """Validate and normalise one envelope without trusting its raw shape.

    ``require_signature=False`` can expose a normalised view of an unsigned
    event for inspection, but it never makes an unverified event actionable.
    """
    profile = profile_for(raw)
    if profile == PROFILE_ENTERPRISE_I1:
        _validate_i1(raw)
    state = verify_signature(raw, key=key)
    field, value, alg = _signature_info(raw, profile)
    severity, severity_raw, severity_scale = _normalised_severity(raw, profile)
    ts = str(raw.get("timestamp_utc") or raw.get("ts") or "")
    organ = str(raw.get("organ") or "ORGAN_UNKNOWN")
    leg = str(raw.get("leg") or ("citizen" if str(raw.get("ring", "")).startswith("RING_0_CITIZEN") or organ == "CITIZEN_APP" else "infra"))
    signal_type = str(raw.get("signal_type") or raw.get("summary") or raw.get("campaign_id") or "")
    reason = str(raw.get("reason") or raw.get("summary") or "")
    entities = raw.get("entities") if isinstance(raw.get("entities"), dict) else ({"entity": raw.get("entity")} if raw.get("entity") else {})
    metrics = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {
        "ring": raw.get("ring", ""), "signal_type": signal_type, "reason": reason,
        "entities": entities, "metrics": metrics,
    }
    verified = state is VerificationState.VALID
    return CanonicalEnvelope(
        contract=CONTRACT_VERSION, profile=profile,
        event_id=str(raw.get("event_id") or ""), ts=ts, organ=organ, leg=leg,
        severity=severity, severity_raw=severity_raw, severity_scale=severity_scale,
        signal_type=signal_type, reason=reason, entities=entities, metrics=metrics,
        payload=payload,
        signature={"field": field, "algorithm": alg or SIG_ALG, "value": value, "state": state.value},
        state=state, verified=verified,
        actionable=verified,  # signature verification is mandatory for action
        governor_required=True, signature_required=require_signature,
    )


validate_event = validate_envelope
canonical_envelope = validate_envelope


def require_valid_signature(raw: dict[str, Any], key: Any = None) -> CanonicalEnvelope:
    result = validate_envelope(raw, key=key, require_signature=True)
    if not result.actionable:
        raise EnvelopeValidationError(f"event is not actionable: {result.state.value}")
    return result


__all__ = [
    "CONTRACT_VERSION", "PROFILE_ORGAN_TELEMETRY", "PROFILE_ORGAN_SEALED",
    "PROFILE_ENTERPRISE_I1", "SIG_ALG", "SIG_FIELD", "MAC_FIELD",
    "EnvelopeValidationError", "VerificationState", "CanonicalEnvelope",
    "bus_key", "rpc_key", "sensor_key", "ingest_key", "DEFAULT_INGEST_KEY",
    "profile_for", "sign_event",
    "verify_signature", "verify_event", "validate_envelope", "validate_event",
    "canonical_envelope", "require_valid_signature",
]
