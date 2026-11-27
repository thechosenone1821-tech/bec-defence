"""Thread-safe metrics: counters and stage latency histograms (p50/p95).

The pipeline records one latency sample per stage per event; /v1/metrics and
the eval harness both read from this registry, so runtime numbers and eval
numbers share one implementation.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque


def _pctl(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, round(q * (len(sorted_vals) - 1)))
    return sorted_vals[idx]


@dataclass
class LatencyStat:
    n: int = 0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    mean_ms: float = 0.0


class _Histogram:
    __slots__ = ("_lock", "_vals", "_max")

    def __init__(self, max_samples: int = 4096) -> None:
        self._lock = threading.Lock()
        self._vals: Deque[float] = deque(maxlen=max_samples)
        self._max = max_samples

    def observe(self, ms: float) -> None:
        with self._lock:
            self._vals.append(ms)

    def stat(self) -> LatencyStat:
        with self._lock:
            vals = sorted(self._vals)
        if not vals:
            return LatencyStat()
        return LatencyStat(
            n=len(vals),
            p50_ms=round(_pctl(vals, 0.50), 3),
            p95_ms=round(_pctl(vals, 0.95), 3),
            mean_ms=round(sum(vals) / len(vals), 3),
        )


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}
        self._latencies: dict[str, _Histogram] = {}
        self._t0 = time.time()

    def inc(self, name: str, by: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + by

    def observe(self, stage: str, ms: float) -> None:
        hist = self._latencies.get(stage)
        if hist is None:
            with self._lock:
                hist = self._latencies.setdefault(stage, _Histogram())
        hist.observe(ms)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            counters = dict(self._counters)
            hists = dict(self._latencies)
        uptime = round(time.time() - self._t0, 1)
        return {
            "uptime_s": uptime,
            "counters": counters,
            "latency_ms": {name: h.stat().__dict__ for name, h in sorted(hists.items())},
        }

    # context helper for stage timing
    class _Timer:
        def __init__(self, metrics: "Metrics", stage: str) -> None:
            self._m, self._stage, self._t0 = metrics, stage, 0.0

        def __enter__(self) -> "Metrics._Timer":
            self._t0 = time.perf_counter()
            return self

        def __exit__(self, *exc: object) -> None:
            self._m.observe(self._stage, (time.perf_counter() - self._t0) * 1000)

    def timer(self, stage: str) -> "Metrics._Timer":
        return Metrics._Timer(self, stage)
