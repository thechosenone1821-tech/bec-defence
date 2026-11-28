"""I1 telemetry envelope: canonical JSON, HMAC-SHA256 signing and verification.

The canonical form is json.dumps(obj, sort_keys=True, separators=(",", ":")) —
the same byte-for-byte form the browser console and the eval harness use, so a
signature created by any Raksha component verifies in every other component.

Integrity rules (contract R3):
  * a signed event whose signature verifies  -> actionable
  * a signed event whose signature mismatches -> quarantined, never actionable
  * an unsigned event                        -> quarantined, never actionable
"""

from __future__ import annotations

import hashlib
import hmac
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

SIG_FIELD = "sig"
SIG_ALG = "HMAC-SHA256"
_REQUIRED = ("event_id", "ts", "organ", "campaign_id", "case_id", "leg",
             "severity", "entity", "summary", "payload")
_LEGS = ("citizen", "infra")


class EventValidationError(ValueError):
    """The envelope is malformed and cannot be trusted at all."""


class VerifyState(str, Enum):
    VALID = "valid"
    TAMPERED = "tampered"
    UNSIGNED = "unsigned"


@dataclass(slots=True)
class Event:
    event_id: str
    ts: str
    organ: str
    campaign_id: str
    case_id: str
    leg: str
    severity: int
    entity: str
    summary: str
    payload: dict[str, Any]
    sig_alg: str | None = None
    sig: str | None = None

    # -- envelope ------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        out = {
            "event_id": self.event_id, "ts": self.ts, "organ": self.organ,
            "campaign_id": self.campaign_id, "case_id": self.case_id,
            "leg": self.leg, "severity": self.severity, "entity": self.entity,
            "summary": self.summary, "payload": self.payload,
        }
        # sig_alg is part of the signed body and must appear whenever it is
        # set — not only when sig is present — or sign/verify bodies diverge.
        if self.sig_alg is not None:
            out["sig_alg"] = self.sig_alg
        if self.sig is not None:
            out[SIG_FIELD] = self.sig
        return out

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Event":
        if not isinstance(raw, dict):
            raise EventValidationError("envelope must be a JSON object")
        missing = [k for k in _REQUIRED if k not in raw]
        if missing:
            raise EventValidationError(f"missing envelope fields: {', '.join(missing)}")
        if raw.get("leg") not in _LEGS:
            raise EventValidationError(f"leg must be one of {_LEGS}, got {raw.get('leg')!r}")
        severity = raw["severity"]
        if not isinstance(severity, int) or not 1 <= severity <= 5:
            raise EventValidationError("severity must be an integer in [1,5]")
        if not isinstance(raw["payload"], dict):
            raise EventValidationError("payload must be a JSON object")
        for key in ("event_id", "ts", "organ", "entity", "summary"):
            if not isinstance(raw[key], str) or not raw[key]:
                raise EventValidationError(f"{key} must be a non-empty string")
        return cls(
            event_id=raw["event_id"], ts=raw["ts"], organ=raw["organ"],
            campaign_id=raw.get("campaign_id", ""), case_id=raw.get("case_id", ""),
            leg=raw["leg"], severity=severity, entity=raw["entity"],
            summary=raw["summary"], payload=raw["payload"],
            sig_alg=raw.get("sig_alg"), sig=raw.get(SIG_FIELD),
        )

    # -- canonicalization ----------------------------------------------------
    def signing_body(self) -> dict[str, Any]:
        body = self.to_dict()
        body.pop(SIG_FIELD, None)
        return body

    def canonical(self) -> str:
        return canonical(self.signing_body())


def canonical(obj: Any) -> str:
    """Byte-exact canonical JSON shared by every RAKSHA component."""
    try:
        from packages.contracts.canonical import canonical_json
    except ImportError:  # pragma: no cover - standalone historical checkout
        sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
        from packages.contracts.canonical import canonical_json
    return canonical_json(obj)


def sign_event(event: Event, key: bytes) -> str:
    # sig_alg must be set BEFORE canonicalization: it is part of the signed body.
    event.sig_alg = SIG_ALG
    mac = hmac.new(key, event.canonical().encode(), hashlib.sha256)
    event.sig = mac.hexdigest()
    return event.sig


def verify_event(event: Event, key: bytes) -> VerifyState:
    if not event.sig:
        return VerifyState.UNSIGNED
    expected = hmac.new(key, event.canonical().encode(), hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected, event.sig.lower()):
        return VerifyState.VALID
    return VerifyState.TAMPERED


def tamper_event(event: Event) -> Event:
    """Flip a field AFTER signing — used by RAAVAN and tests to exercise R3."""
    event.severity = 1 if event.severity != 1 else 2
    return event
