"""End-to-end pipeline: the full c2247 scenario through ingest->decide->seal."""

from __future__ import annotations

from raksha.config import Settings
from raksha.events import Event, sign_event, tamper_event, verify_event, VerifyState
from raksha.ledger import LedgerStore
from raksha.metrics import Metrics
from raksha.pipeline import Pipeline
from raksha.raavan.player import RaavanPlayer, embedded_transport, load_scenario
from raksha.storage import EventStore

from conftest import SENSOR_KEY, make_event


def build(tmp_path) -> tuple[Pipeline, LedgerStore, EventStore]:
    settings = Settings(data_dir=tmp_path, log_level="ERROR", rate_limit_epm=600)
    store = EventStore(settings.events_db_path)
    ledger = LedgerStore(settings.ledger_db_path)
    pipeline = Pipeline(settings, SENSOR_KEY, ledger, store, Metrics())
    return pipeline, ledger, store


def test_raavan_scenario_passes_end_to_end(tmp_path) -> None:
    pipeline, ledger, _store = build(tmp_path)
    player = RaavanPlayer(embedded_transport(pipeline), SENSOR_KEY, load_scenario(), ledger=ledger)
    report = player.run()
    assert report["ok"], report["failures"]
    assert report["total_detections"] == 13
    assert report["refusals"] == ["PROP-C-2247-ICU-CUT"]
    assert len(report["allowances"]) == 3
    assert report["ledger_height_after"] - report["ledger_height_before"] == 9


def test_ledger_contents_after_scenario(tmp_path) -> None:
    pipeline, ledger, _store = build(tmp_path)
    player = RaavanPlayer(embedded_transport(pipeline), SENSOR_KEY, load_scenario(), ledger=ledger)
    player.run()
    kinds = [b["kind"] for b in ledger.entries()]
    # genesis + fuse + 4 proposals + 4 decisions
    assert kinds.count("genesis") == 1
    assert kinds.count("detection") == 1
    assert kinds.count("proposal") == 4
    assert kinds.count("containment") == 3
    assert kinds.count("refusal") == 1
    refusal = ledger.by_kind("refusal")[0]
    assert refusal["ref"] == "PROP-C-2247-ICU-CUT"
    assert refusal["payload"]["rule_id"] == "G1-CROWN-GATEWAY"
    assert refusal["payload"]["fallback_proposal_id"] == "PROP-C-2247-N-BUILD-SRV-EGRESS"


def test_unsigned_and_tampered_never_actionable(tmp_path) -> None:
    pipeline, ledger, store = build(tmp_path)
    unsigned = make_event("EV-U", organ="fileguard", leg="infra", entity="N-BUILD-SRV",
                          payload={"encrypt_events_per_min": 900})
    tampered = make_event("EV-T", organ="fileguard", leg="infra", entity="N-BUILD-SRV",
                          payload={"encrypt_events_per_min": 900}, campaign="C-TEST", case="case-test")
    sign_event(tampered, SENSOR_KEY)
    tamper_event(tampered)
    assert verify_event(unsigned, SENSOR_KEY) is VerifyState.UNSIGNED
    assert verify_event(tampered, SENSOR_KEY) is VerifyState.TAMPERED

    for event in (unsigned, tampered):
        result = pipeline.process(event)
        assert result["verified"] in ("unsigned", "tampered")
        assert result["detections"] == []
        assert "decisions" not in result or not result.get("decisions")
    assert store.counts()["detections"] == 0
    assert len(store.list_quarantined()) == 2


def test_duplicate_event_id_rejected(tmp_path) -> None:
    pipeline, _ledger, _store = build(tmp_path)
    event = signed_event_for("EV-DUP-1")
    first = pipeline.process(event)
    second = pipeline.process(event)
    assert first["accepted"] and second["accepted"] is False
    assert "duplicate" in second["reason"]


def test_rate_limit(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path, log_level="ERROR", rate_limit_epm=2)
    store = EventStore(settings.events_db_path)
    ledger = LedgerStore(settings.ledger_db_path)
    pipeline = Pipeline(settings, SENSOR_KEY, ledger, store, Metrics())
    outcomes = [pipeline.process(make_event(f"EV-RL-{i}", campaign="", case=""))["accepted"]
                for i in range(4)]
    assert outcomes == [True, True, False, False]


def test_unknown_organ_quarantined_from_detection(tmp_path) -> None:
    pipeline, _ledger, store = build(tmp_path)
    event = make_event("EV-X", organ="ghostguard")
    sign_event(event, SENSOR_KEY)
    result = pipeline.process(event)
    assert result["verified"] == "valid"
    assert result["detections"] == []
    assert "unknown organ" in result["reason"]
    assert store.counts()["detections"] == 0


def signed_event_for(event_id: str) -> Event:
    event = make_event(event_id, campaign="", case="")
    sign_event(event, SENSOR_KEY)
    return event


def test_cli_embedded_path(tmp_path) -> None:
    """`python -m raksha.raavan.player --data-dir ...` must work end-to-end:
    seeds a sensor key on first boot, runs the scenario, returns a JSON report."""
    import io
    import json as jsonlib
    from contextlib import redirect_stdout

    from raksha.raavan.player import main as raavan_main

    data_dir = tmp_path / "raavan-cli"
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = raavan_main(["--data-dir", str(data_dir)])
    assert code == 0
    report = jsonlib.loads(buf.getvalue())  # stdout must be pure JSON (no bootstrap noise)
    assert report["ok"] and report["total_detections"] == 13
    assert (data_dir / "keys" / "sensor.key").exists()
