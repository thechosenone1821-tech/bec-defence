"""Filesystem watcher for one sandbox directory.

Uses the ``watchdog`` library (in ``requirements.txt``) to observe a single
sandbox directory. Real filesystem watchers identify files and events but
**do not identify the writing process**; the watcher therefore emits events
with ``actor`` set to ``"unknown"`` unless an external telemetry source is
plugged in.

Observer selection
------------------

By default :class:`FileEventWatcher` uses :class:`watchdog.observers.polling.PollingObserver`
rather than the native ``Observer``. The native observer on Windows
(``WindowsApiObserver``) is known to miss events for short-lived file writes
(open-write-close within a single polling tick); the polling observer scans
the directory tree on a fixed interval and is reliable across platforms at
the cost of ``poll_interval_seconds`` latency (default 0.25s). Pass
``use_polling=False`` to fall back to the native observer for production
deployments that have tested it on their target platform.

What the watcher does:

* Creates synthetic canary files via :class:`CanaryFixture` on startup.
* Inspects create / modify / rename / delete events.
* Tracks per-path modification counts and modification bursts.
* Bounds reads (only the first ``max_read_bytes`` of each modified file are
  read for entropy / signature inspection) so a multi-GB file cannot stall
  the watcher.
* Debounces duplicate events on the same path within ``debounce_seconds``.
* Waits ``startup_delay_seconds`` after starting the observer so the first
  scan completes before callers begin writing files.

What it does **not** do:

* Attribute writes to a process. ``actor`` is always ``"unknown"``.
* Touch any file outside the sandbox directory.
* Block, kill or quarantine anything. All responses are dry-run.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from engines.blackhole import InformationScramblingMonitor, FileWriteAssessment
from core.events import UnifiedEvent, EventBus


@dataclass
class FileEventData:
    """Normalised view of a watchdog event."""

    kind: str               # "created" | "modified" | "moved" | "deleted"
    path: str
    actor: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    size: int | None = None
    chunk: bytes = field(default=b"")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "size": self.size,
            "chunk_len": len(self.chunk),
        }


class CanaryFixture:
    """Creates and tracks synthetic canary files in a sandbox directory."""

    def __init__(self, sandbox_dir: str, names: Iterable[str]):
        self.sandbox_dir = sandbox_dir
        self.names = list(names)
        self.paths: list[str] = []

    def install(self) -> list[str]:
        os.makedirs(self.sandbox_dir, exist_ok=True)
        for name in self.names:
            path = os.path.join(self.sandbox_dir, name)
            # Distinct, low-entropy, recognisable content.
            payload = f"canary:{name}:unchanged".encode("utf-8") * 4
            with open(path, "wb") as fh:
                fh.write(payload)
            self.paths.append(path)
        return list(self.paths)

    def matches(self, path: str) -> bool:
        return path in self.paths


class FileEventWatcher(FileSystemEventHandler):
    """Watchdog handler that bridges filesystem events to the blackhole engine.

    On each event it:

    1. Debounces duplicates on the same path within ``debounce_seconds``.
    2. Reads up to ``max_read_bytes`` from the file (if it still exists and
       is readable).
    3. Runs :meth:`InformationScramblingMonitor.inspect_file_write`.
    4. Publishes a :class:`UnifiedEvent` to the supplied :class:`EventBus`.
    """

    def __init__(
        self,
        monitor: InformationScramblingMonitor,
        bus: EventBus,
        sandbox_dir: str,
        canary: CanaryFixture | None = None,
        max_read_bytes: int = 4096,
        debounce_seconds: float = 0.25,
        clock=time.monotonic,
        use_polling: bool = True,
        poll_interval_seconds: float = 0.25,
        startup_delay_seconds: float = 0.3,
    ):
        self.monitor = monitor
        self.bus = bus
        self.sandbox_dir = sandbox_dir
        self.canary = canary
        self.max_read_bytes = int(max_read_bytes)
        self.debounce_seconds = float(debounce_seconds)
        self._clock = clock
        self.use_polling = bool(use_polling)
        self.poll_interval_seconds = float(poll_interval_seconds)
        self.startup_delay_seconds = float(startup_delay_seconds)
        self._last_event: dict[str, float] = {}
        self._per_path_count: dict[str, int] = {}
        self._lock = threading.Lock()
        self.events_seen = 0
        self.events_debounced = 0

    # -- public control ----------------------------------------------------- #
    def start(self):
        """Create and start the underlying watchdog observer.

        By default we use :class:`PollingObserver` rather than the native
        ``Observer``. The native observer on Windows (``WindowsApiObserver``)
        is known to miss events for short-lived file writes; the polling
        observer scans the directory tree on a fixed interval and is
        reliable across platforms at the cost of ``poll_interval_seconds``
        latency. Set ``use_polling=False`` to use the native observer.
        """
        if self.use_polling:
            obs = PollingObserver(timeout=self.poll_interval_seconds)
        else:
            obs = Observer()
        obs.schedule(self, self.sandbox_dir, recursive=True)
        obs.start()
        # Give the emitter thread time to attach and do its first scan
        # before callers start writing files. Without this, the very
        # first events can be missed on some platforms.
        if self.startup_delay_seconds > 0:
            time.sleep(self.startup_delay_seconds)
        return obs

    # -- watchdog hook ------------------------------------------------------ #
    def on_any_event(self, event: FileSystemEvent) -> None:
        src = getattr(event, "dest_path", None) or event.src_path
        if not isinstance(src, str):
            return
        # Normalise path.
        src = os.path.normpath(src)
        now = float(self._clock())

        with self._lock:
            last = self._last_event.get(src)
            if last is not None and (now - last) < self.debounce_seconds:
                self.events_debounced += 1
                return
            self._last_event[src] = now
            self._per_path_count[src] = self._per_path_count.get(src, 0) + 1
            self.events_seen += 1

        kind = self._classify(event)
        chunk = b""
        size: int | None = None
        if kind != "deleted":
            chunk, size = self._bounded_read(src)

        data = FileEventData(
            kind=kind,
            path=src,
            timestamp=now,
            size=size,
            chunk=chunk,
        )
        self._inspect_and_publish(data)

    # -- helpers ------------------------------------------------------------ #
    @staticmethod
    def _classify(event: FileSystemEvent) -> str:
        et = event.event_type
        if et == "created":
            return "created"
        if et == "modified":
            return "modified"
        if et in {"moved", "rename"}:
            return "moved"
        if et == "deleted":
            return "deleted"
        return et or "unknown"

    def _bounded_read(self, path: str) -> tuple[bytes, int | None]:
        try:
            if not os.path.exists(path):
                return b"", None
            if os.path.isdir(path):
                return b"", 0
            size = os.path.getsize(path)
            with open(path, "rb") as fh:
                chunk = fh.read(self.max_read_bytes)
            return chunk, size
        except (OSError, PermissionError):
            # File disappeared or is unreadable between the event and our
            # read. Treat as zero-length; the burst / canary signals still
            # fire.
            return b"", None

    def _inspect_and_publish(self, data: FileEventData) -> None:
        # Treat canary touches as their own reason, even on deletion.
        is_canary = bool(self.canary and self.canary.matches(data.path))

        if data.kind == "deleted":
            # Deletion of a canary is critical; other deletions are evidence
            # for the burst signal but cannot be entropy-scored.
            if is_canary:
                assessment = FileWriteAssessment(
                    alert=True,
                    severity="critical",
                    reason="CANARY_DELETED",
                    file=data.path,
                    score=1.0,
                    entropy=None,
                    entropy_delta=None,
                    signature=None,
                    signature_changed=False,
                    burst_score=0.0,
                    evidence=["canary file was deleted"],
                    recommended_action="quarantine",
                )
            else:
                # Feed the burst window with this path so a delete burst
                # still contributes to burst_score via inspect_file_write
                # of a zero-byte chunk.
                assessment = self.monitor.inspect_file_write(data.path, b"")
                # Override the reason to mark it as a deletion.
                if not assessment.alert:
                    assessment.reason = "DELETED"
                    assessment.evidence.append("file deleted")
            self._publish(data, assessment)
            return

        if is_canary:
            # Force a critical canary alert regardless of chunk content.
            assessment = FileWriteAssessment(
                alert=True,
                severity="critical",
                reason="CANARY_TOUCHED",
                file=data.path,
                score=1.0,
                entropy=None,
                entropy_delta=None,
                signature=None,
                signature_changed=False,
                burst_score=0.0,
                evidence=[f"canary {data.path} modified ({data.kind})"],
                recommended_action="quarantine",
            )
        else:
            assessment = self.monitor.inspect_file_write(data.path, data.chunk)

        self._publish(data, assessment)

    def _publish(self, data: FileEventData, assessment: FileWriteAssessment) -> None:
        severity = assessment.severity or "info"
        ev = UnifiedEvent(
            engine="blackhole",
            entity_id=data.path,            # file path is the joinable identity
            resource=data.path,
            severity=severity,
            score=float(assessment.score),
            reason=assessment.reason,
            evidence=assessment.evidence + [f"event_kind={data.kind}", f"actor={data.actor}"],
            recommended_action=assessment.recommended_action,
            source_ref={
                "kind": data.kind,
                "size": data.size,
                "chunk_len": len(data.chunk),
                "signature": assessment.signature,
                "entropy": assessment.entropy,
            },
        )
        self.bus.publish(ev)


def watch_loop(
    monitor: InformationScramblingMonitor,
    bus: EventBus,
    sandbox_dir: str,
    canary_names: Iterable[str] | None = None,
    duration_seconds: float = 5.0,
    max_read_bytes: int = 4096,
    use_polling: bool = True,
    poll_interval_seconds: float = 0.25,
    startup_delay_seconds: float = 0.3,
) -> tuple[FileEventWatcher, list[str]]:
    """Run the watcher for ``duration_seconds`` (blocking). Returns the watcher
    and the list of installed canary paths.

    Used by the demo. In production you would start the observer on a daemon
    thread and not call this function.
    """
    canary_names = list(canary_names or ("canary.canary", "canary.txt"))
    canary = CanaryFixture(sandbox_dir, canary_names)
    canary_paths = canary.install()

    handler = FileEventWatcher(
        monitor=monitor,
        bus=bus,
        sandbox_dir=sandbox_dir,
        canary=canary,
        max_read_bytes=max_read_bytes,
        use_polling=use_polling,
        poll_interval_seconds=poll_interval_seconds,
        startup_delay_seconds=startup_delay_seconds,
    )
    obs = handler.start()
    try:
        time.sleep(duration_seconds)
    finally:
        obs.stop()
        obs.join(timeout=2.0)
    return handler, canary_paths
