"""SPINE — Zero-Trust Telemetry Sanitizer.

The ONLY trust boundary between raw organ telemetry and the AI Commander.
Guarantees:

* Zero raw strings are forwarded: filenames, URLs, usernames, prompts and
  payloads are replaced by opaque HMAC-SHA256 entity tokens (``HOST_042`` style)
  or digests.
* Abuse of telemetry as an indirect-prompt-injection channel is structurally
  eliminated: only fixed-shape enums, timestamps, graph edges and normalized
  [0.00, 1.00] anomaly scores reach Plane 3.
* Anything that does not fit the schema is dropped, never passed through.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
import uuid
from typing import Any, Dict, Optional

DEFAULT_SALT = "eigenshield-dev-salt-change-me"

_SIGNAL_RE = re.compile(r"^[A-Z0-9_]{3,64}$")
_PRINTABLE_RE = re.compile(r"[^ -~]")
_RING_RE = re.compile(r"^RING_[1-4]_[A-Z_]{3,48}$")

_ENTITY_PREFIX = {
    "host_id": "HOST",
    "user_id": "USER",
    "vlan_id": "VLAN",
    "session_id": "SESS",
    "process_hash": "PROC",
    "agent_id": "AGENT",
    "doc_hash": "DOC",
    "service_id": "SVC",
    "cluster_id": "CLUS",
}


def get_salt() -> bytes:
    return os.environ.get("EIGENSHIELD_SALT", DEFAULT_SALT).encode()


def opaque_token(prefix: str, raw: str, salt: Optional[bytes] = None) -> str:
    salt = salt or get_salt()
    digest = hmac.new(salt, str(raw).encode(), hashlib.sha256).hexdigest()
    return f"{prefix}_{digest[:6].upper()}"


def _digest(raw: Any) -> str:
    return "sha256:" + hashlib.sha256(str(raw).encode()).hexdigest()[:32]


def _clamp01(value: Any, default: float = 0.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, v))


_REASON_MAX = 240


def _clean_reason(value: Any) -> str:
    """Sanitise an organ's stated reason without destroying it.

    Part 4 Phase 1.3. `sanitize_event` whitelists its output, so every field not
    named in it is **deleted** — and `reason` was not named. The contract in
    specs/04 §3 requires "a reason, never only a score"; by the time an event
    reached the Commander the reason was gone.

    A reason cannot simply be routed through `_clean_metrics`, because that
    function digests every string ("zero raw strings") and a digested reason is
    unreadable. It also must not pass through untouched: an organ reading
    untrusted input could carry attacker-influenced text into the SOC feed.

    So: printable ASCII only, control characters and newlines collapsed, length
    bounded, and a comment. Reasons are written by the organ, not by the
    attacker; the shape constraint is the boundary.
    """
    text = str(value or "")
    text = _PRINTABLE_RE.sub(" ", text)
    text = " ".join(text.split())
    return text[:_REASON_MAX]


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
            if v.startswith(("sha256:", "pid:")) or v.startswith(("HOST_", "USER_", "VLAN_", "SESS_", "PROC_", "AGENT_", "DOC_", "SVC_", "CLUS_")):
                clean[k] = v[:64]  # already opaque / synthetic identifier
            else:
                clean[k] = opaque_token(prefix, v, salt)
        else:
            # Unknown entity keys are replaced by a digest, never raw text.
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
            # Byte counters etc. are bounded numerics, not strings.
            clean[k] = int(max(0, min(value, 10**12)))
        elif isinstance(value, float):
            clean[k] = _clamp01(value) if abs(value) <= 1.0 else float(max(-1e12, min(value, 1e12)))
        elif isinstance(value, str):
            # Zero raw strings: strings become digests.
            clean[k] = _digest(value)
        # lists/dicts/None are dropped entirely
    return clean


def sanitize_event(raw: Dict[str, Any], salt: Optional[bytes] = None) -> Dict[str, Any]:
    """Validate + sanitize one raw organ event into the Plane-2 schema.
    Raises ValueError if the event is structurally unusable."""
    if not isinstance(raw, dict):
        raise ValueError("event must be an object")
    salt = salt or get_salt()

    signal = str(raw.get("signal_type", "")).upper()
    if not _SIGNAL_RE.match(signal):
        # Never forward an attacker-controlled signal string either.
        signal = "UNPARSED_SIGNAL_" + hashlib.sha256(signal.encode()).hexdigest()[:8].upper()

    ring = str(raw.get("ring", "")).upper()
    if not _RING_RE.match(ring):
        ring = "RING_UNKNOWN"

    organ = str(raw.get("organ", "ORGAN_UNKNOWN")).upper()
    organ = organ if re.match(r"^[A-Z0-9_]{3,64}$", organ) else "ORGAN_UNKNOWN"

    event_id = str(raw.get("event_id") or f"evt_{uuid.uuid4().hex[:12]}")
    if not re.match(r"^[A-Za-z0-9_\-]{4,64}$", event_id):
        event_id = f"evt_{uuid.uuid4().hex[:12]}"

    ts = str(raw.get("timestamp_utc") or "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$", ts):
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return {
        "event_id": event_id,
        "timestamp_utc": ts,
        "ring": ring,
        "organ": organ,
        "signal_type": signal,
        "severity": _clamp01(raw.get("severity"), default=0.0),
        # Part 4 Phase 1.3: these two were being silently deleted here.
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
    """Heuristic spot-check used by the demo; the structural guarantee comes from
    the schema, not from this list."""
    lowered = text.lower()
    markers = ("ignore all rules", "ignore previous instructions", "disregard the above",
               "system prompt", "whitelist ", "you are now")
    return any(m in lowered for m in markers)
