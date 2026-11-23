"""Tripwire — AI-crack-attempt detector.

An attacker who discovers the immune system exists will probe it: poisoned
PDFs, hostile filenames, sprayed injections, brute-force tool hallucination.
Each attempt against the Commander is *evidence of active compromise in
progress*. The tripwire watches the decision stream and, past threshold,
freezes the AI path entirely (organs keep defending; humans get the keys).

Trip conditions (any):
  * any canary hit in Commander output            -> trip (instant)
  * any TCB/mirror disagreement                   -> trip (instant)
  * >= 4 BLOCKED decisions in 60 s                -> trip
  * >= 3 injection markers in sanitized input     -> trip
  * >= 2 unverified disruptive-action requests    -> trip

Reset requires an explicit human step-up (`human_stepup=True`) with a note;
the reset itself is ledgered.
"""

import threading
import time
from collections import deque
from typing import Any

_WINDOW_SEC = 60
_BLOCKED_LIMIT = 4
_INJECTION_LIMIT = 3
_UNVERIFIED_LIMIT = 2


_shared: "Tripwire | None" = None
_shared_lock = threading.Lock()


def shared() -> "Tripwire":
    """Process-wide tripwire: organs/bus/governor all feed the same window."""
    global _shared
    with _shared_lock:
        if _shared is None:
            _shared = Tripwire()
        return _shared


class Tripwire:
    def __init__(self, window_sec: int = _WINDOW_SEC, sleeper=time.time):
        self.window_sec = window_sec
        self._clock = sleeper
        self._events: deque[tuple[float, str]] = deque()
        self._frozen_until: float = 0.0
        self._frozen_reason: str = ""
        self._lock = threading.Lock()
        self._trip_count = 0

    # ------------------------------------------------------------------ #
    def record(self, kind: str) -> None:
        with self._lock:
            now = self._clock()
            self._events.append((now, kind))
            if kind in ("canary_hit", "tcb_mismatch"):
                self._trip(now, f"instant trip: {kind}")
                return
            self._prune(now)
            blocked = sum(1 for _, k in self._events if k == "blocked")
            injections = sum(1 for _, k in self._events if k == "injection_marker")
            unverified = sum(1 for _, k in self._events if k == "unverified_disruptive")
            if blocked >= _BLOCKED_LIMIT:
                self._trip(now, f"{blocked} blocked decisions inside {self.window_sec}s")
            elif injections >= _INJECTION_LIMIT:
                self._trip(now, f"{injections} injection markers inside {self.window_sec}s")
            elif unverified >= _UNVERIFIED_LIMIT:
                self._trip(now, f"{unverified} unverified disruptive-action requests inside {self.window_sec}s")

    def is_frozen(self) -> bool:
        with self._lock:
            return self._clock() < self._frozen_until

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "frozen": self._clock() < self._frozen_until,
                "frozen_until_in_sec": round(max(0.0, self._frozen_until - self._clock()), 1),
                "frozen_reason": self._frozen_reason,
                "events_in_window": len(self._events),
                "trip_count": self._trip_count,
            }

    def reset(self, human_stepup: bool, note: str = "") -> dict[str, Any]:
        if not human_stepup:
            return {"reset": False, "reason": "human step-up required"}
        with self._lock:
            self._frozen_until = 0.0
            self._frozen_reason = ""
            self._events.clear()
        return {"reset": True, "note": note or "human acknowledged"}

    # ------------------------------------------------------------------ #
    def _prune(self, now: float) -> None:
        while self._events and now - self._events[0][0] > self.window_sec:
            self._events.popleft()

    def _trip(self, now: float, reason: str) -> None:
        self._frozen_until = now + self.window_sec
        self._frozen_reason = reason
        self._trip_count += 1
