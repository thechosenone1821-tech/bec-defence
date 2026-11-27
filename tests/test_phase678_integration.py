"""Deterministic Phase 6–8 integration tests. No AI models are imported."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from apps.infra.backend.app import create_app  # noqa: E402
from apps.infra.detectors import (  # noqa: E402
    ORGAN_FIXTURES, ORGAN_SPECS, detect, detector_card, known_organs,
)
from packages.contracts.config import DEFAULT_TOPOLOGY  # noqa: E402
from packages.contracts.envelope import sign_event  # noqa: E402
from packages.governance.commander import commander_card  # noqa: E402
from packages.governance.safety import (  # noqa: E402
    PLANNER_ID, Governor, DryRunExecutor, ExhaustivePlanner, Proposal,
    Topology, UnsafeProposal, safety_card,
)
from packages.ledger.runtime_ledger import RuntimeLedger  # noqa: E402

SENSOR_KEY = b"phase678-test-sensor-key"
ADMIN = "admin-test-token"
SENSOR = "sensor-test-token"
OBSERVER = "observer-test-token"
CONSOLE = "console-test-token"


def token_records():
    return [
        (ADMIN, "admin", ("admin", "read", "telemetry:write")),
        (SENSOR, "sensor", ("telemetry:write",)),
        (OBSERVER, "observer", ("read",)),
        (CONSOLE, "console", ("read",)),
    ]


def make_client(**overrides):
    params = dict(
        sensor_key=SENSOR_KEY, token_records=token_records(),
        console_token=CONSOLE, topology_path=str(DEFAULT_TOPOLOGY),
        seed_demo=False, rate_limit_epm=600, blast_cap=3,
    )
    params.update(overrides)
    app = create_app(**params)
    return TestClient(app), app.state.runtime, app


def raw_event(event_id="EV-TEST-1", organ="page_curve_trap", payload=None,
              leg="infra", entity="HOST_APP_SRV_07", case="CASE-TEST",
              campaign="C-TEST", severity=5):
    return {
        "event_id": event_id, "ts": "2026-11-26T09:00:00Z", "organ": organ,
        "campaign_id": campaign, "case_id": case, "leg": leg,
        "severity": severity, "entity": entity, "summary": "phase 678 test event",
        "payload": payload or {"parity_break": 1},
    }


def signed_event(**kwargs):
    return sign_event(raw_event(**kwargs), key=SENSOR_KEY)


def read_headers(token=OBSERVER):
    return {"Authorization": "Bearer " + token}


def write_headers(token=SENSOR):
    return {"Authorization": "Bearer " + token}


def test_phase678_checker_passes():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/check_phase678_integration.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK: Phase 6-8" in result.stdout


def test_phase6_one_registry_and_eight_fixture_pairs():
    card = detector_card()
    assert len(ORGAN_SPECS) == len(known_organs()) == len(ORGAN_FIXTURES) == 8
    assert card["registry_count"] == 1
    assert card["quarantine_before_detection"] is True
    assert card["frozen_voiceguard_integrated"] is False
    assert len({spec.ring for spec in ORGAN_SPECS}) == 4
    for spec in ORGAN_SPECS:
        bundle = ORGAN_FIXTURES[spec.name]
        assert set(bundle) == {"firing", "silent", "missing"}
        firing = detect(sign_event(raw_event(organ=spec.name, payload=bundle["firing"]),
                                   key=SENSOR_KEY), key=SENSOR_KEY)
        assert firing.status == "finding", (spec.name, firing.reason)
        assert firing.finding["organ"] == spec.name
        assert firing.finding["rule_id"] == spec.rules[0].rule_id
        silent = detect(sign_event(raw_event(event_id="EV-S-" + spec.name,
                                             organ=spec.name, payload=bundle["silent"]),
                                   key=SENSOR_KEY), key=SENSOR_KEY)
        missing = detect(sign_event(raw_event(event_id="EV-M-" + spec.name,
                                              organ=spec.name, payload=bundle["missing"]),
                                   key=SENSOR_KEY), key=SENSOR_KEY)
        assert silent.status == "no_detection" and silent.finding is None
        assert missing.status == "no_detection" and missing.finding is None


def test_phase6_unsigned_tampered_forged_and_unknown_are_quarantined():
    unsigned = raw_event(event_id="EV-UNSIGNED")
    tampered = signed_event(event_id="EV-TAMPERED")
    tampered["severity"] = 1
    forged = sign_event(raw_event(event_id="EV-FORGED"), key=b"wrong-key")
    unknown = signed_event(event_id="EV-UNKNOWN", organ="not_an_organ")
    results = [detect(item, key=SENSOR_KEY) for item in
               (unsigned, tampered, forged, unknown)]
    assert [r.status for r in results] == ["quarantined"] * 4
    assert results[0].state == "unsigned"
    assert results[1].state == "tampered"
    assert results[2].state == "tampered"
    assert results[3].state == "unknown_organ"
    assert all(r.finding is None and r.quarantine["detection_performed"] is False
               for r in results)


def test_phase7_crown_lock_exhaustive_planner_governor_and_dry_run():
    topology = Topology.from_path(DEFAULT_TOPOLOGY)
    with pytest.raises(UnsafeProposal):
        Proposal(
            campaign_id="C-BAD", action="node_quarantine",
            entity="HOST_ICU_MONITOR_01", assets_severed=("HOST_ICU_MONITOR_01",),
            edges_cut=(), blast_radius=("HOST_ICU_MONITOR_01",),
            detail="illegal crown cut", fallback_proposal_id=None,
            planner_id=PLANNER_ID, crown_assets=topology.crown_assets,
            crown_gateway_edges=topology.crown_gateway_edges,
        )
    planner = ExhaustivePlanner(topology)
    campaign = {"campaign_id": "C-P7", "case_id": "CASE-P7",
                "legs": ["citizen", "infra"], "organs": ["page_curve_trap"]}
    proposals = planner.proposals_for(campaign)
    assert len(proposals) >= len(topology.legal_edges()) + 2 * len(topology.legal_hosts())
    for proposal in proposals:
        assert not any(topology.is_crown(asset) for asset in proposal.assets_severed)
        assert not set(proposal.edges_cut) & set(topology.crown_gateway_edges)
    governor = Governor(blast_cap=3)
    decisions = [governor.decide(p) for p in proposals]
    assert any(d.verdict == "ALLOWED" for d in decisions)
    assert any(d.verdict == "REFUSED" for d in decisions)
    assert not hasattr(governor, "override")
    receipt = DryRunExecutor().execute(decisions[0])
    assert receipt["executed"] is False and receipt["real_action"] is False
    assert receipt["dry_run"] is True
    assert safety_card()["crown_cuts"] == "impossible_by_construction"


def test_phase7_runtime_ledger_and_optional_commander_card():
    ledger = RuntimeLedger()
    block = ledger.append(kind="probe", ref="R1", text="probe", payload={"ok": True})
    assert block["seq"] == 1 and ledger.verify()["ok"] is True
    card = commander_card()
    assert card["enabled"] is False and card["mode"] == "disabled"
    assert card["fallback_only"] is True and card["model_invoked"] is False
    assert card["ai_model_loaded"] is False


def test_phase8_unified_contract_routes_and_scoped_auth():
    client, _runtime, app = make_client()
    assert client.get("/healthz").status_code == 200
    assert client.get("/app/health").json()["no_ai_models"] is True
    contract = client.get("/app/contract").json()
    assert contract["route_check"]["ok"] is True
    assert contract["enterprise_route_check"]["ok"] is True
    assert client.get("/v1/state").status_code == 401
    assert client.get("/v1/state", headers=write_headers()).status_code == 403
    assert client.get("/v1/state", headers=read_headers()).status_code == 200
    response = client.post("/v1/telemetry", json=signed_event(), headers=write_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True and body["quarantined"] is False
    assert len(body["detections"]) == 1
    assert body["detections"][0]["ledger_seq"] >= 1
    assert app.state.no_ai_models is True


def test_phase8_unsigned_tampered_and_forged_api_quarantine():
    client, runtime, _app = make_client()
    unsigned = raw_event(event_id="EV-Q1")
    tampered = signed_event(event_id="EV-Q2")
    tampered["severity"] = 1
    forged = sign_event(raw_event(event_id="EV-Q3"), key=b"wrong-key")
    bodies = []
    for item in (unsigned, tampered, forged):
        response = client.post("/v1/telemetry", json=item, headers=write_headers())
        assert response.status_code == 200
        bodies.append(response.json())
    assert all(body["quarantined"] is True and not body["detections"] for body in bodies)
    quarantine = client.get("/v1/quarantine", headers=read_headers()).json()
    assert quarantine["count"] == 3
    assert {"unsigned", "tampered"} <= {item["state"] for item in quarantine["items"]}
    assert not any(item["kind"] == "detection" and item["data"]["event_id"].startswith("EV-Q")
                   for item in runtime.hub.history())


def test_phase8_dedupe_and_rate_limit_semantics():
    limited, runtime, _app = make_client(rate_limit_epm=1)
    first = limited.post("/v1/telemetry", json=signed_event(event_id="EV-R1"),
                         headers=write_headers()).json()
    second = limited.post("/v1/telemetry", json=signed_event(event_id="EV-R2"),
                          headers=write_headers()).json()
    assert first["accepted"] is True
    assert second["accepted"] is False and "rate limit" in second["reason"]
    assert runtime.metrics_snapshot()["counters"]["ingest.rate_limited"] >= 1

    duplicate, dup_runtime, _app = make_client(rate_limit_epm=10)
    event = signed_event(event_id="EV-D1")
    assert duplicate.post("/v1/telemetry", json=event, headers=write_headers()).json()["accepted"]
    again = duplicate.post("/v1/telemetry", json=event, headers=write_headers()).json()
    assert again["accepted"] is False and "duplicate" in again["reason"]
    assert dup_runtime.metrics_snapshot()["counters"]["ingest.duplicate"] >= 1


def test_phase8_refusals_ledgered_override_impossible_and_sealed_before_broadcast():
    client, runtime, _app = make_client(seed_demo=True)
    decisions = client.get("/v1/decisions", headers=read_headers()).json()
    assert decisions["count"] > 0
    assert {"containment", "refusal"} <= {row["kind"] for row in decisions["decisions"]}
    assert any(row["verdict"] == "REFUSED" for row in decisions["decisions"])
    assert client.get("/v1/ledger/verify", headers=read_headers()).json()["ok"] is True
    override = client.post("/v1/decisions/P-anything/override",
                           headers={"Authorization": "Bearer " + ADMIN})
    assert override.status_code == 403
    assert "append-only" in override.json()["detail"]
    for item in runtime.hub.history():
        if item["kind"] != "decision":
            continue
        seq = item["data"]["ledger_seq"]
        assert seq >= 1
        assert any(entry["stage"] == "ledger" and entry["ledger_seq"] == seq
                   and entry["step"] < item["step"] for entry in runtime.timeline)


def test_phase8_console_is_read_only_shows_full_sequence_and_ws_stream():
    client, runtime, app = make_client(seed_demo=True)
    html = client.get("/app/console").text
    js = client.get("/app/console.js").text
    assert client.get("/app/console").status_code == 200
    root = client.get("/", follow_redirects=False)
    assert root.status_code == 307 and root.headers["location"] == "/app/console"
    assert 'src="console.js"' in html
    assert "read-only" in html.lower()
    assert "Detection → proposal → decision → ledger sequence" in html
    for banned in ("POST", "override", "localhost", ADMIN, SENSOR):
        assert banned not in js
    assert "/v1/state" in js and "/v1/telemetry/stream" in js
    assert CONSOLE in js and OBSERVER not in js
    state = client.get("/v1/state", headers=read_headers()).json()
    stages = {entry["stage"] for entry in state["timeline"]}
    assert {"detection", "proposal", "decision", "ledger", "quarantine"} <= stages
    assert any(entry["kind"] == "refusal" for entry in state["timeline"])
    assert state["commander"]["model_invoked"] is False
    assert app.state.console_token == CONSOLE
    with client.websocket_connect("/v1/telemetry/stream?token=" + CONSOLE) as ws:
        first = ws.receive_json()
        assert {"step", "kind", "data"} <= set(first)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/v1/telemetry/stream?token=bad-token") as ws:
            ws.receive_json()
    assert runtime is app.state.runtime
