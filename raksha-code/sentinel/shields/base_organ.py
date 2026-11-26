"""sentinel/shields base organ: common telemetry emitter + signed RPC receiver.

Every reflex organ subclasses :class:`BaseOrgan` so Plane 2 (the telemetry
bus) can consume a uniform event shape, and Plane 4/3 can call back into any
organ through one signed-RPC envelope.

The RPC envelope is HMAC-SHA256 signed. In the demo the shared secret comes
from ``EIGENSHIELD_RPC_SECRET`` (default is a dev-only value). In production
this would be an mTLS identity; the envelope shape stays the same.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

DEV_RPC_SECRET = "eigenshield-dev-rpc-secret-do-not-use-in-prod"


def _rpc_secret() -> bytes:
    return os.environ.get("EIGENSHIELD_RPC_SECRET", DEV_RPC_SECRET).encode()


def sign_rpc(tool: str, args: Dict[str, Any], nonce: Optional[str] = None) -> Dict[str, Any]:
    """Build a signed RPC envelope (caller side, e.g. the Governor executor)."""
    envelope = {
        "rpc_id": f"rpc_{uuid.uuid4().hex[:12]}",
        "tool": tool,
        "args": args,
        "nonce": nonce or uuid.uuid4().hex,
        "ts": time.time(),
    }
    body = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    envelope["signature"] = hmac.new(_rpc_secret(), body, hashlib.sha256).hexdigest()
    return envelope


def verify_rpc(envelope: Dict[str, Any]) -> bool:
    """Constant-time verification of a signed RPC envelope."""
    if not isinstance(envelope, dict) or "signature" not in envelope:
        return False
    body_src = {k: v for k, v in envelope.items() if k != "signature"}
    body = json.dumps(body_src, sort_keys=True, separators=(",", ":")).encode()
    expected = hmac.new(_rpc_secret(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, str(envelope.get("signature", "")))


# --------------------------------------------------------------------------- #
# Coercion and sealing (Part 4, Phase 1.1-1.3)
# --------------------------------------------------------------------------- #
_SEVERITY_FLOOR = 0.0
_SEVERITY_CEIL = 1.0


def coerce_severity(value: Any) -> Tuple[float, str]:
    """Map anything to a severity in [0, 1] **without inventing an extreme**.

    Returns ``(severity, source)`` where source says what happened:

      ``supplied``   a usable finite number, clamped to range
      ``nan``        NaN/Infinity -> 0.0 (never 1.0: unknown is not an alarm)
      ``not_numeric`` unparseable -> 0.0

    A NaN that becomes 1.0 both cries wolf and hides the corruption. A NaN that
    becomes 0.0 is quiet and states why, which is the behaviour a detector should
    have when it does not know.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return _SEVERITY_FLOOR, "not_numeric"
    if v != v:                       # NaN
        return _SEVERITY_FLOOR, "nan"
    if v in (float("inf"), float("-inf")):
        # An infinite severity is a broken computation, not a maximal finding.
        return _SEVERITY_FLOOR, "infinite"
    if v < _SEVERITY_FLOOR:
        return _SEVERITY_FLOOR, "supplied"
    if v > _SEVERITY_CEIL:
        return _SEVERITY_CEIL, "supplied"
    return v, "supplied"


def _safe_dict(value: Any) -> Dict[str, Any]:
    """Copy a dict-ish payload without raising on junk."""
    try:
        return dict(value) if value else {}
    except (TypeError, ValueError):
        return {}


def seal_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Sign an organ event with HMAC-SHA256 over its canonical body.

    Deliberately does not import `spine.telemetry_mac`: the organ must be able to
    sign its own event without the bus being importable, because the point of
    signing at the source is that it does not depend on the transport.
    """
    body = {k: v for k, v in event.items() if k not in ("mac", "signature")}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"),
                           default=str).encode()
    mac = hmac.new(_rpc_secret(), canonical, hashlib.sha256).hexdigest()
    sealed = dict(body)
    sealed["mac"] = mac
    sealed["signature"] = mac       # same value; two names because both are expected
    return sealed


def verify_sealed(event: Dict[str, Any]) -> bool:
    """True iff this event was sealed by an organ and not altered since."""
    if not isinstance(event, dict):
        return False
    mac = event.get("mac") or event.get("signature")
    if not isinstance(mac, str) or len(mac) != 64:
        return False
    body = {k: v for k, v in event.items() if k not in ("mac", "signature")}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"),
                           default=str).encode()
    expected = hmac.new(_rpc_secret(), canonical, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, mac)


class BaseOrgan:
    """Common behaviour for all eight reflex organs."""

    ring: str = "RING_UNSET"
    organ: str = "ORGAN_UNSET"

    def __init__(self, event_sink: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.event_sink = event_sink
        self._local_events: List[Dict[str, Any]] = []
        self._rpc_handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    # ------------------------------------------------------------------ #
    # Telemetry emission (Plane 1 -> Plane 2)
    # ------------------------------------------------------------------ #
    def emit(
        self,
        signal_type: str,
        severity: float,
        entities: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Emit a signed event with a stated severity and a reason.

        Part 4 Phase 1 changed three things here, each because the old version
        was wrong in a way that no test noticed:

        1. **A NaN was promoted to 1.0.** ``max(0.0, min(1.0, nan))`` returns
           ``1.0`` in Python: both comparisons against NaN are False, so ``min``
           keeps its first argument and ``max`` then picks the larger. A corrupt
           float therefore became the *most severe possible* event. Unknown is
           now a stated default, never a fabricated extreme — the same rule the
           rest of this codebase follows.

        2. **A malformed severity raised.** A crash inside an organ is precisely
           the case that must never pass traffic, so ``emit`` is total: it never
           raises, and anything it has to coerce is recorded on the event.

        3. **The event was not signed.** "Unsigned events are inert" is the
           contract; a caller reading ``drain_events()`` could hold one unsigned.
           It is now sealed at birth.

        ``reason`` is required by the contract ("a reason, never only a score").
        An organ may supply its own; ``BaseOrgan`` guarantees the field exists.
        """
        value, severity_source = coerce_severity(severity)
        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
            + f".{int((time.time() % 1) * 1000):03d}Z",
            "ring": self.ring,
            "organ": self.organ,
            "signal_type": str(signal_type),
            "severity": value,
            "severity_source": severity_source,
            "reason": str(reason) if reason else (
                f"{self.organ} reported {signal_type} at severity {value:.3f}"
                + ("" if severity_source == "supplied" else f" ({severity_source})")),
            "entities": _safe_dict(entities),
            "metrics": _safe_dict(metrics),
        }
        sealed = seal_event(event)
        self._local_events.append(sealed)
        if self.event_sink:
            try:
                self.event_sink(sealed)
            except Exception:
                # A broken consumer must not stop the organ from reporting.
                pass
        return sealed

    def drain_events(self) -> List[Dict[str, Any]]:
        """Return and clear buffered local events (used by demos/tests)."""
        events, self._local_events = self._local_events, []
        return events

    # ------------------------------------------------------------------ #
    # Signed RPC reception (Plane 4 executor -> Plane 1 organ)
    # ------------------------------------------------------------------ #
    def register_rpc(self, tool: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._rpc_handlers[tool] = handler

    def handle_rpc(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        if not verify_rpc(envelope):
            return {"status": "REJECTED", "reason": "bad_signature", "rpc_id": envelope.get("rpc_id")}
        handler = self._rpc_handlers.get(envelope.get("tool"))
        if handler is None:
            return {"status": "REJECTED", "reason": "unknown_tool", "rpc_id": envelope.get("rpc_id")}
        try:
            result = handler(envelope.get("args", {}))
            return {"status": "OK", "rpc_id": envelope.get("rpc_id"), "result": result}
        except Exception as exc:  # defensive: organs must never crash the bus
            return {"status": "ERROR", "rpc_id": envelope.get("rpc_id"), "reason": str(exc)}
