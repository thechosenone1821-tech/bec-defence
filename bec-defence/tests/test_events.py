"""Tests for core/events.py: unified event format, audit log, correlation."""

import json
import os
import tempfile
import time

import pytest

from core.events import (
    UnifiedEvent,
    EventBus,
    JsonlAuditLog,
    CorrelationEngine,
    Incident,
)


def _make_event(engine="spectral", entity="s1", resource="r1", reason="R", severity="low", timestamp=None):
    kwargs = dict(
        engine=engine,
        entity_id=entity,
        resource=resource,
        severity=severity,
        score=0.3,
        reason=reason,
    )
    if timestamp is not None:
        kwargs["timestamp"] = timestamp
    return UnifiedEvent(**kwargs)


def test_event_fingerprint_stable():
    a = UnifiedEvent.fingerprint("spectral", "s1", "r1", "R")
    b = UnifiedEvent.fingerprint("spectral", "s1", "r1", "R")
    assert a == b
    c = UnifiedEvent.fingerprint("spectral", "s2", "r1", "R")
    assert a != c


def test_event_bus_publishes():
    bus = EventBus()
    seen = []
    bus.subscribe(seen.append)
    e = _make_event()
    assert bus.publish(e)
    assert seen == [e]
    assert bus.published == 1


def test_event_bus_suppresses_duplicates():
    bus = EventBus(suppress_seconds=1.0)
    e1 = _make_event(timestamp=100.0)
    e2 = _make_event(timestamp=100.2)  # same fingerprint, within window
    assert bus.publish(e1)
    assert not bus.publish(e2)
    assert bus.dropped_duplicates == 1


def test_event_bus_allows_after_suppression_window():
    bus = EventBus(suppress_seconds=0.5)
    e1 = _make_event(timestamp=100.0)
    e2 = _make_event(timestamp=101.0)  # outside window
    assert bus.publish(e1)
    assert bus.publish(e2)
    assert bus.dropped_duplicates == 0


def test_jsonl_audit_log_appends_lines():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "audit.jsonl")
        log = JsonlAuditLog(path)
        log.write(_make_event())
        log.write(_make_event())
        log.close()
        with open(path) as fh:
            lines = fh.readlines()
        assert len(lines) == 2
        for ln in lines:
            obj = json.loads(ln)
            assert "event_id" in obj
            assert "engine" in obj


def test_correlation_opens_incident_on_two_events_same_entity():
    corr = CorrelationEngine(window_seconds=60.0)
    e1 = _make_event(entity="alice", severity="low")
    e2 = _make_event(entity="alice", severity="high")
    corr.ingest(e1)
    inc = corr.ingest(e2)
    assert inc is not None
    assert inc.key == "alice"
    assert inc.key_kind == "entity_id"
    assert inc.severity == "high"
    assert len(inc.events) == 2


def test_correlation_does_not_open_incident_on_single_event():
    corr = CorrelationEngine(window_seconds=60.0)
    inc = corr.ingest(_make_event())
    assert inc is None


def test_correlation_joins_by_resource():
    corr = CorrelationEngine(window_seconds=60.0)
    corr.ingest(_make_event(entity="a", resource="/data/x", severity="low"))
    inc = corr.ingest(_make_event(entity="b", resource="/data/x", severity="high"))
    assert inc is not None
    assert inc.key_kind == "resource"
    assert inc.severity == "high"


def test_correlation_purges_old_events():
    corr = CorrelationEngine(window_seconds=1.0)
    # Use real time but compressed.
    e1 = _make_event(entity="a", severity="low")
    e1 = UnifiedEvent(**{**e1.to_dict(), "timestamp": time.time() - 10})
    corr.ingest(e1)
    # New event with same entity, but the old one is outside the window.
    inc = corr.ingest(_make_event(entity="a", severity="low"))
    # Only one event in the window now -> no incident.
    assert inc is None
