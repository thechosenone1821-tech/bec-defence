"""SPINE — Zero-Trust Telemetry Sanitizer (Phase 3 shared rules).

Zero raw strings are forwarded; filenames, URLs, usernames, prompts and
payloads become opaque HMAC-SHA256 entity tokens or digests. The regexes,
prefixes and entity path are owned by ``packages.contracts.entities``.
"""
from __future__ import annotations

import hashlib
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from packages.contracts.entities import (
        DEFAULT_SALT, ENTITY_PATH, ENTITY_PREFIX, EVENT_ID_RE, ORGAN_RE,
        RING_RE, SIGNAL_RE, TIMESTAMP_RE, clean_reason, digest, get_salt,
        is_opaque_identifier, opaque_token,
    )
except ImportError:  # pragma: no cover - minimal standalone checkout
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from packages.contracts.entities import (
        DEFAULT_SALT, ENTITY_PATH, ENTITY_PREFIX, EVENT_ID_RE, ORGAN_RE,
        RING_RE, SIGNAL_RE, TIMESTAMP_RE, clean_reason, digest, get_salt,
        is_opaque_identifier, opaque_token,
    )

_SIGNAL_RE = SIGNAL_RE
_RING_RE = RING_RE
_ENTITY_PREFIX = ENTITY_PREFIX
_REASON_MAX = 240


def _clamp01(value: Any, default: float = 0.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, v))


_clean_reason = clean_reason
_digest = digest


def _clean_entities(raw_entities: Any, salt: bytes) -> Dict[str, str]:
    if not isinstance(raw_entities, dict):
        return {}
    clean: Dict[str, str] = {}
    for key, value in raw_entities.items():
        if value is None:
            continue
        k = str(key).lower()
        v = str(value)
        prefix = _ENTITY_PREFIX.get(k)
        if prefix is not None:
            if is_opaque_identifier(v):
                clean[k] = v[:64]
            else:
                clean[k] = opaque_token(prefix, v, salt)
        else:
            clean[k[:32]] = _digest(v)
    return clean


def _clean_metrics(raw_metrics: Any) -> Dict[str, Any]:
    if not isinstance(raw_metrics, dict):
        return {}
    clean: Dict[str, Any] = {}
    for key, value in raw_metrics.items():
        k = str(key)[:48]
        if isinstance(value, bool):
            clean[k] = value
        elif isinstance(value, int):
            clean[k] = int(max(0, min(value, 10**12)))
        elif isinstance(value, float):
            clean[k] = _clamp01(value) if abs(value) <= 1.0 else float(max(-1e12, min(value, 1e12)))
        elif isinstance(value, str):
            clean[k] = _digest(value)
    return clean


def sanitize_event(raw: Dict[str, Any], salt: Optional[bytes] = None) -> Dict[str, Any]:
    """Validate + sanitize one raw organ event into the Plane-2 schema."""
    if not isinstance(raw, dict):
        raise ValueError("event must be an object")
    salt = salt or get_salt()

    signal = str(raw.get("signal_type", "")).upper()
    if not _SIGNAL_RE.match(signal):
        signal = "UNPARSED_SIGNAL_" + hashlib.sha256(signal.encode()).hexdigest()[:8].upper()

    ring = str(raw.get("ring", "")).upper()
    if not _RING_RE.match(ring):
        ring = "RING_UNKNOWN"

    organ = str(raw.get("organ", "ORGAN_UNKNOWN")).upper()
    organ = organ if ORGAN_RE.match(organ) else "ORGAN_UNKNOWN"

    event_id = str(raw.get("event_id") or f"evt_{uuid.uuid4().hex[:12]}")
    if not EVENT_ID_RE.match(event_id):
        event_id = f"evt_{uuid.uuid4().hex[:12]}"

    ts = str(raw.get("timestamp_utc") or "")
    if not TIMESTAMP_RE.match(ts):
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return {
        "event_id": event_id,
        "timestamp_utc": ts,
        "ring": ring,
        "organ": organ,
        "signal_type": signal,
        "severity": _clamp01(raw.get("severity"), default=0.0),
        "reason": _clean_reason(raw.get("reason")),
        "severity_source": _clean_reason(raw.get("severity_source"))[:24],
        "entities": _clean_entities(raw.get("entities"), salt),
        "metrics": _clean_metrics(raw.get("metrics")),
    }


def sanitize_batch(events: list[Dict[str, Any]], salt: Optional[bytes] = None) -> list[Dict[str, Any]]:
    out = []
    for e in events:
        try:
            out.append(sanitize_event(e, salt))
        except ValueError:
            continue
    return out


def looks_like_injection(text: str) -> bool:
    lowered = text.lower()
    markers = ("ignore all rules", "ignore previous instructions", "disregard the above",
               "system prompt", "whitelist ", "you are now")
    return any(m in lowered for m in markers)


__all__ = [
    "DEFAULT_SALT", "ENTITY_PATH", "ENTITY_PREFIX", "clean_reason", "digest",
    "get_salt", "looks_like_injection", "opaque_token", "sanitize_batch",
    "sanitize_event",
]
