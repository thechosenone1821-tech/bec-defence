"""Blast-radius budgets: max cuts / quarantines / splices per 5-minute window.

This is invariant 3 of the Governor. Even a correct action, repeated enough
times, becomes an outage. The budget caps how many actions of each class the
system may take inside a rolling window.

Design notes:

- The window is rolling, not fixed: an action's reservation expires exactly
  ``window_seconds`` after it was made.
- The clock is injected. Production passes ``time.time``; tests pass a fake
  clock, which is how the 5-minute window is proven without sleeping.
- Reservations are committed only when a decision ends in ALLOW. A refused or
  escalated action consumes no budget.
- A simple lock guards the counters; Part 1 assumes a single process. Part 2
  moves budgets into the hardened spine where they are shared state.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from .tools import BUCKET_CUT, BUCKET_QUARANTINE, BUCKET_SPLICE


@dataclass(frozen=True)
class BudgetConfig:
    max_cuts: int = 4
    max_quarantines: int = 3
    max_splices: int = 4
    window_seconds: float = 300.0

    def cap_for(self, bucket: str) -> int:
        return {
            BUCKET_CUT: self.max_cuts,
            BUCKET_QUARANTINE: self.max_quarantines,
            BUCKET_SPLICE: self.max_splices,
        }[bucket]


class BudgetWindow:
    """Rolling-window reservation ledger for one Governor instance."""

    def __init__(
        self,
        config: BudgetConfig,
        clock: Callable[[], float],
    ) -> None:
        self._config = config
        self._clock = clock
        self._events: List[Tuple[float, str]] = []
        self._lock = threading.Lock()

    def used(self, bucket: str) -> int:
        """Reservations of `bucket` still inside the rolling window."""
        now = self._clock()
        cutoff = now - self._config.window_seconds
        with self._lock:
            return sum(
                1 for ts, b in self._events if b == bucket and ts > cutoff
            )

    def check(self, bucket: Optional[str]) -> Tuple[bool, int]:
        """Would one more action of this class fit the budget?

        Returns (ok, used_now). bucket=None is always allowed (unbounded
        tools such as snapshot.capture are still logged and policy-checked).
        """
        if bucket is None:
            return True, 0
        with self._lock:
            now = self._clock()
            cutoff = now - self._config.window_seconds
            used = sum(
                1 for ts, b in self._events if b == bucket and ts > cutoff
            )
            return used < self._config.cap_for(bucket), used

    def cap_for(self, bucket: str) -> int:
        """Public access to the configured cap for one bucket."""
        return self._config.cap_for(bucket)

    def reserve(self, bucket: Optional[str]) -> None:
        """Commit one reservation. Called only on a final ALLOW."""
        if bucket is None:
            return
        with self._lock:
            self._events.append((self._clock(), bucket))

    def snapshot(self) -> Dict[str, int]:
        """Current window usage per bucket (for consoles and audits)."""
        return {
            BUCKET_CUT: self.used(BUCKET_CUT),
            BUCKET_QUARANTINE: self.used(BUCKET_QUARANTINE),
            BUCKET_SPLICE: self.used(BUCKET_SPLICE),
        }
