"""Root-level deterministic Infra integration tests."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from apps.infra import features as infra_features  # noqa: E402
from apps.infra.backend.app import create_app  # noqa: E402
from apps.infra.console import console_card  # noqa: E402
from apps.infra.detectors.registry import ORGAN_SPECS, detector_card  # noqa: E402
from tools import check_phase678_integration, run_hospital_demo_smoke  # noqa: E402


def _tokens():
    return [
        ("admin", "admin", ("admin", "read", "telemetry:write")),
        ("sensor", "sensor", ("telemetry:write",)),
        ("observer", "observer", ("read",)),
    ]


def test_infra_checker_is_green():
    assert check_phase678_integration.main([]) == 0


def test_infra_is_deterministic_and_dry_run():
    card = detector_card()
    assert card["registry_count"] == 1
    assert card["quarantine_before_detection"] is True
    app = create_app(
        sensor_key=b"root-test-key",
        token_records=_tokens(),
        console_token="observer", seed_demo=False,
    )
    client = TestClient(app)
    health = client.get("/app/health").json()
    assert health["model_backed"] is False
    assert health["deterministic"] is True
    assert health["dry_run"] is True
    assert health["infra_ready"] is True
    assert app.state.model_backed is False
    assert app.state.infra_ready is True


def test_completed_infra_status_capabilities_and_detectors():
    app = create_app(
        sensor_key=b"root-status-key",
        token_records=_tokens(),
        console_token="observer", seed_demo=True,
    )
    client = TestClient(app)
    status = client.get(infra_features.STATUS_PATH)
    capabilities = client.get(infra_features.CAPABILITIES_PATH)
    detectors = client.get(infra_features.DETECTORS_PATH)
    assert status.status_code == 200
    assert capabilities.status_code == 200
    assert detectors.status_code == 200
    body = status.json()
    assert body["ready"] is True
    assert body["executor_mode"] == infra_features.EXECUTOR_MODE
    assert body["commander_enabled"] is False
    assert body["console_read_only"] is True
    assert body["model_backed"] is False
    assert body["deterministic"] is True
    assert body["status_path"] == infra_features.STATUS_PATH
    assert body["app_state"]["infra_ready"] is True
    assert capabilities.json()["contract"] == "raksha-infra-capabilities-v1"
    assert detectors.json()["organ_count"] == len(ORGAN_SPECS)
    assert detectors.json()["registry_count"] == 1
    assert console_card()["contract"] == "raksha-readonly-console-v2"
    assert app.state.infra_status_path == infra_features.STATUS_PATH
    assert app.state.capabilities_path == infra_features.CAPABILITIES_PATH
    assert app.state.detectors_path == infra_features.DETECTORS_PATH
    assert app.state.vigil_integrated is False
    assert app.state.commander_enabled is False


def test_infra_read_token_fallbacks_keep_write_boundary():
    app = create_app(
        sensor_key=b"root-auth-key",
        token_records=_tokens(),
        console_token="observer", seed_demo=False,
    )
    cookie_client = TestClient(app)
    assert cookie_client.get(infra_features.CONSOLE_PATH).status_code == 200
    assert cookie_client.get(infra_features.STATE_PATH).status_code == 200
    assert "access_token" in cookie_client.get(infra_features.CONSOLE_JS_PATH).text

    header_client = TestClient(app)
    assert header_client.get(
        infra_features.STATE_PATH,
        headers={"X-API-Token": "observer"},
    ).status_code == 200
    assert header_client.get(
        infra_features.STATE_PATH,
        headers={"Authorization": "Bearer observer"},
    ).status_code == 200

    query_client = TestClient(app)
    assert query_client.get(
        infra_features.STATE_PATH + "?access_token=observer",
    ).status_code == 200
    assert query_client.post(
        "/v1/telemetry?access_token=observer", json={},
    ).status_code == 401
    assert query_client.post(
        "/v1/decisions/probe/override",
        headers={"X-API-Token": "admin"},
    ).status_code == 403


def test_infra_websocket_streams_deterministic_history():
    app = create_app(
        sensor_key=b"root-ws-key",
        token_records=_tokens(),
        console_token="observer", seed_demo=True,
    )
    client = TestClient(app)
    with client.websocket_connect(
        "/v1/telemetry/stream?token=observer",
    ) as websocket:
        first = websocket.receive_json()
    assert first["kind"]
    assert isinstance(first.get("step"), int)


def test_fake_hospital_demo_is_functional_and_isolated():
    assert run_hospital_demo_smoke.main() == 0
    app = create_app(
        sensor_key=b"root-hospital-key",
        token_records=_tokens(),
        console_token="observer", seed_demo=False,
    )
    client = TestClient(app)
    headers = {"X-API-Token": "observer"}
    ui = client.get(infra_features.HOSPITAL_DEMO_PATH)
    ui_js = client.get(infra_features.HOSPITAL_DEMO_JS_PATH)
    state = client.get(infra_features.HOSPITAL_STATE_PATH, headers=headers)
    assert ui.status_code == 200
    assert ui_js.status_code == 200
    assert state.status_code == 200
    assert "Start scenario" in ui.text
    assert "Play all" in ui.text
    assert "__RAKSHA_DEMO_TOKEN__" not in ui_js.text
    body = state.json()
    assert body["contract"] == infra_features.HOSPITAL_DEMO_CONTRACT
    assert body["organization"]["kind"] == "fake_hospital"
    assert body["scenario"]["executor_mode"] == "dry-run"
    assert body["scenario"]["commander_enabled"] is False
    assert body["scenario"]["steps_total"] >= 8
    assert TestClient(app).post(
        infra_features.HOSPITAL_STEP_PATH, json={},
    ).status_code == 401
    assert TestClient(app).post(
        infra_features.HOSPITAL_STEP_PATH + "?access_token=observer", json={},
    ).status_code == 401
    live_ledger_before = app.state.runtime.ledger.height()
    live_detections_before = len(app.state.runtime.detections)
    last = None
    for _ in range(body["scenario"]["steps_total"]):
        last = client.post(infra_features.HOSPITAL_STEP_PATH,
                           headers=headers, json={})
        assert last.status_code == 200
    assert last is not None
    final = last.json()["state"]
    assert final["scenario"]["done"] is True
    assert final["scenario"]["campaign_fused"] is True
    assert final["runtime"]["finding_count"] >= 6
    assert final["runtime"]["quarantine_count"] >= 3
    assert final["runtime"]["decision_count"] >= 1
    assert final["runtime"]["ledger_verify"]["ok"] is True
    assert final["scenario"]["real_action_count"] == 0
    assert final["scenario"]["dry_run_action_count"] >= 1
    assert app.state.runtime.ledger.height() == live_ledger_before
    assert len(app.state.runtime.detections) == live_detections_before
