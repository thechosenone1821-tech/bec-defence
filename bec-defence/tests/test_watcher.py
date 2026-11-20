"""Tests for watch/fs_watcher.py -- run against a real temp sandbox dir."""

import os
import tempfile
import threading
import time

import pytest

watchdog = pytest.importorskip("watchdog")

from engines.blackhole import InformationScramblingMonitor
from core.events import EventBus, UnifiedEvent
from watch.fs_watcher import (
    FileEventWatcher,
    CanaryFixture,
    watch_loop,
)


def test_canary_install_creates_files():
    with tempfile.TemporaryDirectory() as td:
        canary = CanaryFixture(td, ["a.canary", "b.canary"])
        paths = canary.install()
        assert len(paths) == 2
        for p in paths:
            assert os.path.exists(p)


def test_modification_publishes_event():
    with tempfile.TemporaryDirectory() as td:
        bus = EventBus()
        received = []
        bus.subscribe(received.append)
        mon = InformationScramblingMonitor()
        canary = CanaryFixture(td, ["canary.canary"])
        canary.install()
        handler = FileEventWatcher(
            monitor=mon,
            bus=bus,
            sandbox_dir=td,
            canary=canary,
            debounce_seconds=0.05,
            poll_interval_seconds=0.1,
            startup_delay_seconds=0.3,
        )
        obs = handler.start()
        try:
            # Write a normal text file.
            with open(os.path.join(td, "notes.txt"), "wb") as fh:
                fh.write(b"hello world " * 200)
            # Polling observer at 0.1s interval -- allow at least two
            # full poll cycles plus margin for the event to be dispatched
            # and the subscriber callback to fire.
            time.sleep(1.0)
        finally:
            obs.stop()
            obs.join(timeout=2.0)
        # At least one event should have been published.
        assert len(received) >= 1, (
            f"expected >= 1 event, got {len(received)}; "
            f"events_seen={handler.events_seen} "
            f"events_debounced={handler.events_debounced}"
        )
        ev = received[0]
        assert isinstance(ev, UnifiedEvent)
        assert ev.engine == "blackhole"


def test_canary_modification_produces_critical_event():
    with tempfile.TemporaryDirectory() as td:
        bus = EventBus()
        received = []
        bus.subscribe(received.append)
        mon = InformationScramblingMonitor()
        canary = CanaryFixture(td, ["canary.canary"])
        canary.install()
        handler = FileEventWatcher(
            monitor=mon, bus=bus, sandbox_dir=td, canary=canary,
            debounce_seconds=0.05,
            poll_interval_seconds=0.1,
            startup_delay_seconds=0.3,
        )
        obs = handler.start()
        try:
            # Touch the canary.
            with open(os.path.join(td, "canary.canary"), "ab") as fh:
                fh.write(b"x")
            # Allow enough time for the polling observer to detect the
            # modification and dispatch the event.
            time.sleep(1.0)
        finally:
            obs.stop()
            obs.join(timeout=2.0)
        canary_events = [e for e in received if e.reason == "CANARY_TOUCHED"]
        assert canary_events, (
            f"canary touch should publish a critical event; "
            f"got {len(received)} total events, "
            f"events_seen={handler.events_seen}"
        )
        assert canary_events[0].severity == "critical"


def test_watch_loop_returns_handler_and_paths():
    with tempfile.TemporaryDirectory() as td:
        bus = EventBus()
        mon = InformationScramblingMonitor()
        handler, paths = watch_loop(
            monitor=mon, bus=bus, sandbox_dir=td,
            canary_names=["c1.canary"], duration_seconds=0.5,
            poll_interval_seconds=0.25,
            startup_delay_seconds=0.2,
        )
        assert os.path.exists(paths[0])
        assert isinstance(handler, FileEventWatcher)
