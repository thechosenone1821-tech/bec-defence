"""Integrated demo.

Shows the full Day-1 + Day-2 stack end-to-end:

1.  Normal traffic -> no alarm, no incident.
2.  Coordinated synthetic traffic -> spectral alarm + suspect list.
3.  Suspicious sandbox file modifications -> blackhole events, canary touch,
    entropy-delta and burst signals.
4.  Correlated alert -> the CorrelationEngine joins >= 2 events sharing an
    entity_id or resource into an :class:`Incident`.
5.  Dry-run response -> the :class:`DryRunResponseLayer` issues
    ``revoke_session`` against the in-memory demo identity (the ONLY
    enforced action), and ``would_*`` recommendations for everything else.

6.  Seeded scenario-matrix benchmark -> printed at the end.

All sandbox I/O happens under a temp directory created by ``tempfile``; no
real user files are touched, no processes are killed, no external endpoints
are contacted.
"""

from __future__ import annotations

import os
import tempfile
import time

import numpy as np

from engines.spectral import (
    SpectralCondensationDetector,
    RollingSpectralMonitor,
    MeanShiftBaseline,
    DistanceBaseline,
)
from engines.blackhole import InformationScramblingMonitor
from core.events import (
    UnifiedEvent,
    EventBus,
    JsonlAuditLog,
    CorrelationEngine,
)
from identity.registry import IdentityRegistry
from response.dryrun import DryRunResponseLayer
from sim.benchmark import run_scenario_matrix, summarize_matrix
from watch.fs_watcher import CanaryFixture, FileEventWatcher


def _setup_stack(audit_path: str):
    rng = np.random.default_rng(42)
    d = 8

    spectral = SpectralCondensationDetector(safety_margin=1.2, z_alert=2.5)
    spectral.fit_baseline(rng.normal(0, 1, size=(5000000, d)))

    mon = InformationScramblingMonitor(
        canary_patterns=("*.canary", "/vault/*"),
        entropy_threshold=7.2,
        entropy_delta_threshold=1.5,
        burst_window_seconds=10.0,
        burst_distinct_threshold=5,
    )

    audit = JsonlAuditLog(audit_path)
    bus = EventBus(audit_log=audit, suppress_seconds=1.0)
    corr = CorrelationEngine(window_seconds=60.0)

    # Wire the bus to the correlation engine.
    bus.subscribe(corr.ingest)

    registry = IdentityRegistry()
    registry.register(
        identity_id="alice",
        kind="human",
        declared_name="Alice (demo)",
        credential="hunter2",
        allowed_actions={"read", "write", "revoke_session"},
    )
    registry.register(
        identity_id="svc_backup",
        kind="service",
        declared_name="Backup service (demo)",
        credential="svc-token",
        allowed_actions={"read"},
    )
    response = DryRunResponseLayer(registry)

    return {
        "rng": rng,
        "d": d,
        "spectral": spectral,
        "monitor": mon,
        "audit": audit,
        "bus": bus,
        "corr": corr,
        "registry": registry,
        "response": response,
    }


def _print_section(title: str) -> None:
    print(f"\n--- {title} ---")


def _spectral_events_from_result(res, entity_prefix="session") -> list[UnifiedEvent]:
    """Emit one UnifiedEvent per suspect row, sharing the entity_id."""
    out = []
    if not res.get("suspect_indices"):
        return out
    for idx in res["suspect_indices"]:
        z = res["suspect_zscores"][list(res["suspect_indices"]).index(idx)]
        out.append(UnifiedEvent(
            engine="spectral",
            entity_id=f"{entity_prefix}",
            resource=f"session-matrix:{entity_prefix}",
            severity="high" if res["attack_detected"] else "low",
            score=min(abs(float(z)) / 5.0, 1.0),
            reason=res.get("reason", "SPECTRAL"),
            evidence=[f"suspect_index={idx}", f"z={z:.2f}"],
            recommended_action="log",
        ))
    return out


def demo_normal_traffic(stack) -> None:
    rng = stack["rng"]
    d = stack["d"]
    det = stack["spectral"]
    _print_section("TEST 1: Normal traffic (expect no alarm)")
    res = det.analyze_traffic(rng.normal(0, 1, size=(500, d)))
    print(f"  detected={res['attack_detected']}  alert_level={res['alert_level']}")
    print(f"  lambda_max={res['lambda_max']}  threshold={res['mp_threshold']}")
    print(f"  suspects={len(res['suspect_indices'])}  constant_features={res['constant_features']}")
    # Publish any candidate events (low severity) so the audit log is
    # populated even on benign traffic.
    for ev in _spectral_events_from_result(res):
        stack["bus"].publish(ev)


def demo_coordinated_swarm(stack) -> None:
    rng = stack["rng"]
    d = stack["d"]
    det = stack["spectral"]
    _print_section("TEST 2: Coordinated bot swarm (expect alarm)")
    humans = rng.normal(0, 1, size=(400, d))
    template = rng.normal(0, 1, size=d) * 1.5
    bots = template + rng.normal(0, 0.25, size=(100, d))
    res = det.analyze_traffic(np.vstack([humans, bots]))
    truth = set(range(400, 500))
    flagged = set(res["suspect_indices"])
    print(f"  detected={res['attack_detected']}  lambda_max={res['lambda_max']}")
    print(f"  condensation={res['condensation_ratio']}  mean_shift={res['mean_shift_stat']}")
    print(f"  flagged {len(flagged)}: {len(flagged & truth)} true bots, "
          f"{len(flagged - truth)} false positives")
    # Publish the suspect events to the bus -> correlation -> incident.
    for ev in _spectral_events_from_result(res):
        stack["bus"].publish(ev)


def demo_cusum(stack) -> None:
    # Fresh seed for determinism regardless of prior rng state.
    rng = np.random.default_rng(2024)
    d = stack["d"]
    det = stack["spectral"]
    _print_section("TEST 3: CUSUM catches weak persistent swarm")
    # Slightly more sensitive configuration than the rolling benchmark so
    # the demo reliably fires; TEST 7 reports multi-seed evidence with the
    # stricter configuration.
    roller = RollingSpectralMonitor(
        det, window=500, check_every=25, drift=0.05, alarm_h=0.3
    )
    weak_template = rng.normal(0, 1, size=d) * 1.0
    alarms = 0
    false_before = 0
    first_at = None
    for i in range(3000):
        if 1500 <= i < 2500 and rng.random() < 0.15:
            feats = weak_template + rng.normal(0, 0.25, size=d)
        else:
            feats = rng.normal(0, 1, size=d)
        a = roller.add_session(feats)
        if a:
            alarms += 1
            if first_at is None:
                first_at = i
            if i < 1500:
                false_before += 1
            if alarms <= 3:
                print(f"  CUSUM alarm #{alarms} at event {i}: "
                      f"lambda_max={a['lambda_max']}  S_after={a['cusum']['S_after']}")
    print(f"  CUSUM alarms: {alarms}  (first at event {first_at}, "
          f"{false_before} false alarms before attack window)")
    print("  (TEST 7 reports multi-seed evidence with the stricter drift=0.1, "
          "alarm_h=0.5 configuration.)")


def demo_file_monitor(stack) -> None:
    mon = stack["monitor"]
    rng = stack["rng"]
    _print_section("TEST 4: Black Hole file monitor (direct calls)")
    # Sequence of writes to the same path to demonstrate entropy delta.
    print("  normal write :", mon.inspect_file_write(
        "/data/notes.txt", b"Monthly hospital patient schedule and shift notes. " * 50
    ).to_dict())
    print("  ransomware   :", mon.inspect_file_write(
        "/data/notes.txt", bytes(rng.integers(0, 256, size=2048).astype(np.uint8).tolist())
    ).to_dict())
    print("  canary write :", mon.inspect_file_write("/vault/payroll.docx", b"hello").to_dict())


def demo_filesystem_watcher(stack, sandbox_dir: str) -> None:
    mon = stack["monitor"]
    bus = stack["bus"]
    _print_section("TEST 5: Filesystem watcher on a sandbox directory")
    canary = CanaryFixture(sandbox_dir, ["canary.canary", "canary.txt"])
    canary_paths = canary.install()
    print(f"  installed canaries: {canary_paths}")

    # use_polling=True (default) for cross-platform reliability -- the
    # native Windows observer misses short-lived writes.
    handler = FileEventWatcher(
        monitor=mon, bus=bus, sandbox_dir=sandbox_dir, canary=canary,
        debounce_seconds=0.05,
        poll_interval_seconds=0.1,
        startup_delay_seconds=0.3,
    )
    obs = handler.start()
    try:
        # Normal write.
        with open(os.path.join(sandbox_dir, "notes.txt"), "wb") as fh:
            fh.write(b"hello world " * 200)
        time.sleep(0.4)
        # Suspicious write to a NEW path -- high entropy.
        rng = stack["rng"]
        with open(os.path.join(sandbox_dir, "weird.bin"), "wb") as fh:
            fh.write(bytes(rng.integers(0, 256, size=4096).astype(np.uint8).tolist()))
        time.sleep(0.4)
        # Burst: write to several distinct small files in a short window.
        for i in range(8):
            with open(os.path.join(sandbox_dir, f"f{i}.dat"), "wb") as fh:
                fh.write(bytes(rng.integers(0, 256, size=256).astype(np.uint8).tolist()))
        time.sleep(0.4)
        # Canary touch.
        with open(os.path.join(sandbox_dir, "canary.canary"), "ab") as fh:
            fh.write(b"x")
        # Final wait: allow the polling observer at least two full poll
        # cycles to detect the last writes.
        time.sleep(1.2)
    finally:
        obs.stop()
        obs.join(timeout=2.0)
    print(f"  watcher saw {handler.events_seen} events, "
          f"debounced {handler.events_debounced}")
    print(f"  bus published {bus.published} events, "
          f"dropped {bus.dropped_duplicates} duplicates")
    print(f"  burst snapshot: {mon.modification_burst()}")


def demo_correlation_and_response(stack) -> None:
    corr = stack["corr"]
    response = stack["response"]
    registry = stack["registry"]
    _print_section("TEST 6: Correlation + dry-run response")

    # Synthesise a correlated incident: two events with the same entity_id
    # 'alice', both high severity.
    from core.events import UnifiedEvent
    e1 = UnifiedEvent(
        engine="spectral",
        entity_id="alice",
        resource="session-matrix:alice",
        severity="high",
        score=0.8,
        reason="SUSPECTS_PRESENT",
        evidence=["z=3.1"],
    )
    e2 = UnifiedEvent(
        engine="blackhole",
        entity_id="alice",
        resource="/vault/payroll.docx",
        severity="critical",
        score=1.0,
        reason="CANARY_TOUCHED",
        evidence=["canary touched"],
    )
    bus = stack["bus"]
    bus.publish(e1)
    bus.publish(e2)

    incidents = corr.open_incidents()
    print(f"  open incidents: {len(incidents)}")
    for inc in incidents:
        print(f"  - {inc.incident_id} key={inc.key} ({inc.key_kind}) "
              f"severity={inc.severity} events={len(inc.events)}")
        decisions = response.evaluate_incident(inc)
        for d in decisions:
            print(f"    decision action={d.action} would={d.would_execute} "
                  f"executed={d.executed} reason={d.reason}")
    alice = registry.get("alice")
    print(f"  alice revoked={alice.revoked} reason={alice.revoked_reason}")


def demo_benchmark(stack) -> None:
    rng = stack["rng"]
    d = stack["d"]
    _print_section("TEST 7: Seeded scenario-matrix benchmark")

    # Fresh detectors for a clean comparison.
    spectral = SpectralCondensationDetector(safety_margin=1.2, z_alert=2.5)
    mean_b = MeanShiftBaseline(z_alert=3.0)
    dist_b = DistanceBaseline(z_alert=3.0)
    mat = run_scenario_matrix(
        detectors={"spectral": spectral, "mean_shift": mean_b, "distance": dist_b},
        n_seeds=3, n_humans=400, n_bots=100, d=d,
        base_seed=int(rng.integers(0, 1_000_000)),
    )
    print(summarize_matrix(mat))


def main():
    with tempfile.TemporaryDirectory() as td:
        audit_path = os.path.join(td, "audit.jsonl")
        sandbox = os.path.join(td, "sandbox")
        os.makedirs(sandbox, exist_ok=True)
        stack = _setup_stack(audit_path)

        try:
            demo_normal_traffic(stack)
            demo_coordinated_swarm(stack)
            demo_cusum(stack)
            demo_file_monitor(stack)
            demo_filesystem_watcher(stack, sandbox)
            demo_correlation_and_response(stack)
            demo_benchmark(stack)
        finally:
            stack["audit"].close()

        # Print the audit log path and a short tail.
        print(f"\nAudit log written to: {audit_path}")
        try:
            with open(audit_path) as fh:
                lines = fh.readlines()
            print(f"  ({len(lines)} lines)")
            if lines:
                print(f"  first: {lines[0].strip()[:200]}")
        except OSError:
            pass

        print("\nDone. All responses were dry-run except in-memory demo revocation.")


if __name__ == "__main__":
    main()
