"""Telemetry MAC — organ events are HMAC-SHA256 signed at birth.

The /api/ingest endpoint is a public surface: anyone on the network could
POST a fake `PARITY_ENTROPY_COLLAPSE` with severity 0.96. Without
authentication, a garbage post — or a deliberate forgery — could trigger
real containment actions or drown the Commander.

Control: every event minted inside this process is signed with
HMAC-SHA256 over its canonical JSON (key from EIGENSHIELD_BUS_KEY, dev
default below). The bus accepts external posts only as UNVERIFIED: they are
visible (dashboard, logs) but can never (a) trigger auto-orchestration,
(b) back a host/VLAN-disruptive action — the executor requires verified
evidence — or (c) move a blast-radius budget.

Honest note: inside one process this is an integrity tag, not a boundary;
the boundary is created when the bus runs as a separate UID (see
sandbox_runner / docs/FORTRESS.md deployment checklist).
"""

import hashlib
import hmac
import json
import os
import time

_DEV_KEY = "eigenshield-dev-bus-key-change-in-production"


def _key() -> bytes:
    return os.environ.get("EIGENSHIELD_BUS_KEY", _DEV_KEY).encode()


def _canonical(event: dict) -> bytes:
    body = {k: v for k, v in event.items() if k not in ("mac", "verified")}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()


def sign_event(event: dict) -> dict:
    signed = {k: v for k, v in event.items() if k not in ("mac", "verified")}
    signed["mac"] = hmac.new(_key(), _canonical(signed), hashlib.sha256).hexdigest()
    return signed


def verify_event(event: dict) -> bool:
    mac = event.get("mac") if isinstance(event, dict) else None
    if not isinstance(mac, str) or len(mac) != 64:
        return False
    expected = hmac.new(_key(), _canonical(event), hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, expected)


class SeenEventCache:
    """Replay defense for the windowed feed: event_ids are single-use for
    10 minutes. Same-id resubmission is dropped, not re-executed."""

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
