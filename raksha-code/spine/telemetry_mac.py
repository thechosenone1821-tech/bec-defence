"""Telemetry MAC — organ events are HMAC-SHA256 signed at birth.

Phase 3 delegates canonical JSON and signed-envelope validation to
``packages.contracts`` while preserving the shipped ``mac``/``verified`` wire
shape. External posts remain UNVERIFIED: they are visible but cannot steer
the AI path, back a disruptive action, or move a blast-radius budget.

Honest note: inside one process this is an integrity tag, not a boundary;
the boundary is created when the bus runs as a separate UID.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import sys
import time
from pathlib import Path

try:
    from packages.contracts.canonical import (
        CANONICAL_JSON_RULE, canonical_bytes, canonical_json,
    )
    from packages.contracts.envelope import (
        CONTRACT_VERSION, VerificationState, bus_key, validate_envelope,
        verify_signature,
    )
except ImportError:  # pragma: no cover - minimal standalone checkout
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from packages.contracts.canonical import (
        CANONICAL_JSON_RULE, canonical_bytes, canonical_json,
    )
    from packages.contracts.envelope import (
        CONTRACT_VERSION, VerificationState, bus_key, validate_envelope,
        verify_signature,
    )

_DEV_KEY = "eigenshield-dev-bus-key-change-in-production"


def _key() -> bytes:
    return os.environ.get("EIGENSHIELD_BUS_KEY", _DEV_KEY).encode()


def _canonical(event: dict) -> bytes:
    body = {k: v for k, v in event.items() if k not in ("mac", "verified")}
    return canonical_bytes(body)


def sign_event(event: dict) -> dict:
    signed = {k: v for k, v in event.items() if k not in ("mac", "verified")}
    signed["mac"] = hmac.new(_key(), _canonical(signed), hashlib.sha256).hexdigest()
    return signed


def verify_event(event: dict) -> bool:
    return verify_signature(event, key=_key()) is VerificationState.VALID


def validate_event(event: dict, key: bytes | None = None):
    """Phase 3 compatibility entry point returning a CanonicalEnvelope."""
    return validate_envelope(event, key=key or bus_key(), require_signature=True)


class SeenEventCache:
    """Replay defense for the windowed feed: event_ids are single-use."""

    def __init__(self, window_sec: int = 600, max_size: int = 100_000):
        self.window_sec = window_sec
        self.max_size = max_size
        self._seen: dict[str, float] = {}

    def check_and_mark(self, event_id: str) -> bool:
        """True iff this id is fresh; False iff it is a replay."""
        now = time.time()
        if len(self._seen) > self.max_size:  # hard cap, fail closed on floods
            self._seen.clear()
            return False
        expired = [k for k, t in self._seen.items() if now - t > self.window_sec]
        for k in expired:
            del self._seen[k]
        if event_id in self._seen:
            return False
        self._seen[event_id] = now
        return True


__all__ = [
    "CANONICAL_JSON_RULE", "CONTRACT_VERSION", "SeenEventCache",
    "canonical_bytes", "canonical_json", "sign_event", "validate_event",
    "verify_event", "verify_signature",
]
