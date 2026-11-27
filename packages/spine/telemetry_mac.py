"""Compatibility facade for shared signed-telemetry helpers."""
from __future__ import annotations

from spine.telemetry_mac import *  # noqa: F401,F403
from spine.telemetry_mac import (  # noqa: F401
    CANONICAL_JSON_RULE, CONTRACT_VERSION, SeenEventCache, canonical_bytes,
    canonical_json, sign_event, validate_event, verify_event,
    verify_signature,
)
from packages.contracts.envelope import CONTRACT_VERSION as EVENT_CONTRACT_VERSION
from packages.contracts.envelope import validate_envelope

__all__ = [
    "CANONICAL_JSON_RULE", "CONTRACT_VERSION", "EVENT_CONTRACT_VERSION",
    "SeenEventCache", "canonical_bytes", "canonical_json", "sign_event",
    "validate_event", "validate_envelope", "verify_event", "verify_signature",
]
