"""PLANE 1 base organ: common telemetry emitter + signed RPC receiver.

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
from typing import Any, Callable, Dict, List, Optional

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
    ) -> Dict[str, Any]:
        """Emit a *raw local* event. The Plane-2 sanitizer is the trust boundary:
        this dict may still contain raw-ish identifiers and MUST pass through
        ``bus.sanitizer.sanitize_event`` before it reaches the Commander."""
        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
            + f".{int((time.time() % 1) * 1000):03d}Z",
            "ring": self.ring,
            "organ": self.organ,
            "signal_type": signal_type,
            "severity": float(max(0.0, min(1.0, severity))),
            "entities": dict(entities or {}),
            "metrics": dict(metrics or {}),
        }
        self._local_events.append(event)
        if self.event_sink:
            self.event_sink(event)
        return event

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
