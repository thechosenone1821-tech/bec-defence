"""Ingest gate: dedupe, rate limiting, signature verification, quarantine.

Rules (contract R3): only events whose HMAC verifies are actionable. Tampered
and unsigned events are stored with verified=0 and never reach detection —
the quarantine path is first-class, not an error.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass

from ..events import Event, VerifyState, verify_event
from ..metrics import Metrics


@dataclass(slots=True)
class IngestResult:
    accepted: bool
    verified: VerifyState
    reason: str


class IngestService:
    def __init__(self, sensor_key: bytes, store, metrics: Metrics, rate_limit_epm: int = 600) -> None:
        self._key = sensor_key
        self._store = store
        self._metrics = metrics
        self._rate_limit_epm = rate_limit_epm
        self._lock = threading.Lock()
        self._seen: set[str] = set()
        self._seen_order: deque[str] = deque(maxlen=200_000)
        self._windows: dict[str, deque[float]] = {}

    def _allow(self, source: str) -> bool:
        now = time.monotonic()
        with self._lock:
            window = self._windows.setdefault(source, deque())
            while window and now - window[0] > 60.0:
                window.popleft()
            if len(window) >= self._rate_limit_epm:
                return False
            window.append(now)
            return True

    def _mark_seen(self, event_id: str) -> bool:
        with self._lock:
            if event_id in self._seen:
                return False
            self._seen.add(event_id)
            self._seen_order.append(event_id)
            if len(self._seen_order) == self._seen_order.maxlen:
                self._seen.discard(self._seen_order[0])
            return True

    def submit(self, event: Event, source: str = "sensor") -> IngestResult:
        with self._metrics.timer("ingest"):
            self._metrics.inc("ingest.received")
            if not self._allow(source):
                self._metrics.inc("ingest.rate_limited")
                return IngestResult(False, VerifyState.UNSIGNED, "rate limit exceeded for source")
            if not self._mark_seen(event.event_id):
                self._metrics.inc("ingest.duplicate")
                return IngestResult(False, VerifyState.UNSIGNED, "duplicate event_id")

            state = verify_event(event, self._key)
            self._store.save_event(event, verified=(state is VerifyState.VALID))
            if state is VerifyState.VALID:
                self._metrics.inc("ingest.verified")
                return IngestResult(True, state, "signature verified")
            self._metrics.inc(f"ingest.quarantine.{state.value}")
            reason = ("signature mismatch — event altered after signing"
                      if state is VerifyState.TAMPERED else "unsigned event — unverified source")
            return IngestResult(True, state, reason)
