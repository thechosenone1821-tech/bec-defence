"""PLANE 4 — 15-second Uptime Auto-Rollback Watchdog.

After any containment action the watchdog pings Tier-0 health probes every
``probe_interval_sec``. If critical latency breaches ``max_tier0_latency_ms``
for a continuous ``failure_window_sec`` (default 15 s), it automatically
invokes the action's revert callback and records the rollback in the ledger.

Testability: ``probe_fn`` (returns list[latency_ms]) and ``sleep`` are
injectable, so tests can compress 15 seconds into milliseconds.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional


class RollbackWatchdog:
    def __init__(self, policy: Dict[str, Any], ledger: Optional[Any] = None,
                 sleeper: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.time):
        cfg = policy.get("auto_rollback", {})
        self.enabled = bool(cfg.get("enabled", True))
        self.probe_interval = float(cfg.get("probe_interval_sec", 3))
        self.failure_window = float(cfg.get("failure_window_sec", 15))
        self.max_latency = float(cfg.get("max_tier0_latency_ms", 120))
        self.ledger = ledger
        self.sleep = sleeper
        self.clock = clock

    def watch(self, action_id: str,
              probe_fn: Callable[[], List[float]],
              revert_fn: Callable[[str], Dict[str, Any]],
              max_cycles: int = 40) -> Dict[str, Any]:
        """Block until the failure window clears cleanly or a rollback fires."""
        if not self.enabled:
            return {"action_id": action_id, "watched": False, "reason": "watchdog_disabled"}

        breached_since: Optional[float] = None
        cycles = 0
        while cycles < max_cycles:
            cycles += 1
            latencies = probe_fn()
            healthy = bool(latencies) and all(l <= self.max_latency for l in latencies)
            now = self.clock()

            if healthy:
                breached_since = None
                if cycles >= max(2, int(self.failure_window / max(self.probe_interval, 1e-6)) + 1) or max_cycles <= 3:
                    return self._finish("WATCHDOG_CLEAR", action_id, cycles)
                self.sleep(self.probe_interval)
                continue

            breached_since = breached_since if breached_since is not None else now
            if now - breached_since >= self.failure_window:
                revert_result = revert_fn(action_id)
                record = {"action_id": action_id, "revert": revert_result,
                          "max_latency_ms": self.max_latency,
                          "failure_window_sec": self.failure_window}
                if self.ledger is not None:
                    self.ledger.append("rollback_executed", record)
                record["rolled_back"] = True
                return record
            self.sleep(self.probe_interval)

        return self._finish("WATCHDOG_TIMEOUT_NO_ROLLBACK", action_id, cycles)

    def _finish(self, status: str, action_id: str, cycles: int) -> Dict[str, Any]:
        record = {"action_id": action_id, "status": status, "cycles": cycles,
                  "rolled_back": False}
        if self.ledger is not None:
            self.ledger.append("watchdog_event", record)
        return record
