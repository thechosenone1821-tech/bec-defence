"""Unified event format, audit log, duplicate suppression and correlation.

Day-2 glue layer. Every detection engine emits :class:`UnifiedEvent` records
with a stable schema. An :class:`EventBus` collects them, a
:class:`JsonlAuditLog` appends them to disk, a :class:`CorrelationEngine`
groups events that share a defensible identity or resource relationship into
:class:`Incident` objects.

The schema is deliberately narrow:

    event_id, timestamp, engine, entity_id, resource,
    severity, score, reason, evidence, recommended_action

``entity_id`` is whatever identity token the producing engine can defensibly
attach. For the spectral engine this is a session id (if the caller supplied
one); for the file engine it is the file path. The correlation layer ONLY
joins events that share an ``entity_id`` or ``resource`` -- it does not
invent relationships.

Important honesty note: a credential establishes a registered identity, not
proof that its operator is human. The event schema does not have a
``is_human`` field.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable


@dataclass(frozen=True)
class UnifiedEvent:
    """One normalised detection event."""

    engine: str                 # "spectral" | "blackhole" | ...
    entity_id: str              # session id, file path, credential id, ...
    resource: str               # affected resource ("session-matrix", file path, ...)
    severity: str               # "info" | "low" | "medium" | "high" | "critical"
    score: float                # 0..1
    reason: str                 # engine-specific reason code
    evidence: list[str] = field(default_factory=list)
    recommended_action: str = "log"   # "log" | "quarantine" | "revoke_session" | ...
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Optional: which session matrix row / file write produced this event.
    source_ref: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def fingerprint(engine: str, entity_id: str, resource: str, reason: str) -> str:
        """Stable hash for duplicate suppression.

        Two events with the same (engine, entity, resource, reason) within a
        suppression window are treated as duplicates.
        """
        h = hashlib.sha1(
            f"{engine}|{entity_id}|{resource}|{reason}".encode("utf-8")
        )
        return h.hexdigest()


# --------------------------------------------------------------------------- #
# Audit log
# --------------------------------------------------------------------------- #
class JsonlAuditLog:
    """Append-only JSONL audit log. Thread-safe."""

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        # Open in append-binary; create if missing.
        self._fh = open(path, "ab", buffering=0)

    def write(self, event: UnifiedEvent) -> None:
        line = json.dumps(event.to_dict(), sort_keys=True)
        with self._lock:
            self._fh.write(line.encode("utf-8") + b"\n")
            self._fh.flush()

    def close(self) -> None:
        with self._lock:
            self._fh.close()


# --------------------------------------------------------------------------- #
# Event bus with duplicate suppression
# --------------------------------------------------------------------------- #
class EventBus:
    """In-memory event bus with time-windowed duplicate suppression.

    Events whose fingerprint has been seen in the last ``suppress_seconds``
    are dropped (and counted in ``dropped_duplicates``). All others are
    forwarded to all subscribers and optionally written to an audit log.
    """

    def __init__(
        self,
        audit_log: JsonlAuditLog | None = None,
        suppress_seconds: float = 5.0,
    ):
        if suppress_seconds < 0:
            raise ValueError("suppress_seconds must be >= 0")
        self.audit_log = audit_log
        self.suppress_seconds = float(suppress_seconds)
        self._subscribers: list = []
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()
        self.dropped_duplicates = 0
        self.published = 0

    def subscribe(self, callback) -> None:
        self._subscribers.append(callback)

    def publish(self, event: UnifiedEvent) -> bool:
        """Publish ``event``. Returns ``True`` if published, ``False`` if suppressed."""
        fp = UnifiedEvent.fingerprint(
            event.engine, event.entity_id, event.resource, event.reason
        )
        now = event.timestamp
        with self._lock:
            self._purge_old(now)
            last = self._seen.get(fp)
            if last is not None and (now - last) < self.suppress_seconds:
                self.dropped_duplicates += 1
                return False
            self._seen[fp] = now
            self.published += 1
        if self.audit_log is not None:
            self.audit_log.write(event)
        for cb in self._subscribers:
            cb(event)
        return True

    def _purge_old(self, now: float) -> None:
        cutoff = now - self.suppress_seconds
        for fp, ts in list(self._seen.items()):
            if ts < cutoff:
                del self._seen[fp]


# --------------------------------------------------------------------------- #
# Correlation
# --------------------------------------------------------------------------- #
@dataclass
class Incident:
    """A group of events that share an identity or resource relationship."""

    incident_id: str
    key: str                       # entity_id or resource used for grouping
    key_kind: str                  # "entity_id" | "resource"
    events: list[UnifiedEvent] = field(default_factory=list)
    severity: str = "info"
    score: float = 0.0
    opened_at: float = 0.0
    last_seen_at: float = 0.0

    def add(self, event: UnifiedEvent) -> None:
        self.events.append(event)
        self.last_seen_at = max(self.last_seen_at, event.timestamp)
        # Severity escalation: take the max along a fixed ladder.
        ladder = ["info", "low", "medium", "high", "critical"]
        if event.severity in ladder and ladder.index(event.severity) > ladder.index(self.severity):
            self.severity = event.severity
        self.score = max(self.score, event.score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "key": self.key,
            "key_kind": self.key_kind,
            "severity": self.severity,
            "score": round(float(self.score), 3),
            "opened_at": self.opened_at,
            "last_seen_at": self.last_seen_at,
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
        }


class CorrelationEngine:
    """Group events into incidents by shared identity or resource.

    Correlation is conservative: an incident is opened only when two or more
    events share the same ``entity_id`` or the same ``resource`` within
    ``window_seconds``. Single events do not form an incident (they are
    still audited, just not correlated).
    """

    def __init__(self, window_seconds: float = 60.0):
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self.window_seconds = float(window_seconds)
        self._by_entity: dict[str, list[UnifiedEvent]] = {}
        self._by_resource: dict[str, list[UnifiedEvent]] = {}
        self.incidents: list[Incident] = []
        self._lock = threading.Lock()

    def ingest(self, event: UnifiedEvent) -> Incident | None:
        """Add an event; return an :class:`Incident` if one was opened/extended."""
        with self._lock:
            self._purge_old(event.timestamp)
            bucket_e = self._by_entity.setdefault(event.entity_id, [])
            bucket_e.append(event)
            bucket_r = self._by_resource.setdefault(event.resource, [])
            bucket_r.append(event)

            # Find an existing incident that this event belongs to.
            for inc in self.incidents:
                if inc.key_kind == "entity_id" and inc.key == event.entity_id:
                    inc.add(event)
                    return inc
                if inc.key_kind == "resource" and inc.key == event.resource:
                    inc.add(event)
                    return inc

            # Open a new incident only if there are >= 2 events sharing a key.
            if len(bucket_e) >= 2:
                inc = Incident(
                    incident_id=str(uuid.uuid4()),
                    key=event.entity_id,
                    key_kind="entity_id",
                    opened_at=bucket_e[0].timestamp,
                )
                for e in bucket_e:
                    inc.add(e)
                self.incidents.append(inc)
                return inc
            if len(bucket_r) >= 2:
                inc = Incident(
                    incident_id=str(uuid.uuid4()),
                    key=event.resource,
                    key_kind="resource",
                    opened_at=bucket_r[0].timestamp,
                )
                for e in bucket_r:
                    inc.add(e)
                self.incidents.append(inc)
                return inc
            return None

    def _purge_old(self, now: float) -> None:
        cutoff = now - self.window_seconds
        for bucket in (self._by_entity, self._by_resource):
            for key in list(bucket.keys()):
                bucket[key] = [e for e in bucket[key] if e.timestamp >= cutoff]
                if not bucket[key]:
                    del bucket[key]

    def open_incidents(self) -> list[Incident]:
        """Return incidents that have at least one event in the last window."""
        now = time.time()
        with self._lock:
            return [
                inc for inc in self.incidents
                if inc.last_seen_at >= now - self.window_seconds
            ]
