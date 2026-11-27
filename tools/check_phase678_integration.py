#!/usr/bin/env python3
"""Active deterministic Infra integration checker.

Proves one detector registry, one quarantine-before-detection contract, a
disabled Commander card, a dry-run Governor/executor/ledger path, read-only
state surfaces and no VIGIL import from the Infra app.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from fastapi.testclient import TestClient  # noqa: E402
from apps.infra import features as infra_features  # noqa: E402
from apps.infra.backend.app import create_app  # noqa: E402
from apps.infra.console import console_card  # noqa: E402
from apps.infra.detectors.registry import ORGAN_SPECS, detector_card  # noqa: E402
from packages.governance.commander import COMMANDER_CONTRACT  # noqa: E402


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main(argv: list[str] | None = None) -> int:
    try:
        card = detector_card()
        check(card["registry_count"] == 1, "Infra detector registry count changed")
        check(card["organ_count"] == len(ORGAN_SPECS), "Infra organ card changed")
        check(card["quarantine_before_detection"] is True,
              "quarantine-before-detection contract was weakened")
        check(COMMANDER_CONTRACT["enabled"] is False, "Commander card became enabled")
        check(COMMANDER_CONTRACT["model_invoked"] is False, "Commander model was invoked")
        check(COMMANDER_CONTRACT["live_endpoint"] is None, "Commander live endpoint was added")

        app = create_app(
            sensor_key=b"integration-checker-key",
            token_records=[
                ("integration-admin", "admin", ("admin", "read", "telemetry:write")),
                ("integration-sensor", "sensor", ("telemetry:write",)),
                ("integration-observer", "observer", ("read",)),
            ],
            console_token="integration-observer",
            seed_demo=False,
        )
        client = TestClient(app)
        health = client.get("/app/health")
        check(health.status_code == 200, "Infra health route failed")
        health_body = health.json()
        check(health_body["model_backed"] is False, "Infra health lost deterministic status")
        check(health_body["deterministic"] is True, "Infra health lost deterministic flag")
        check(health_body["dry_run"] is True, "Infra health lost dry-run flag")
        check(app.state.model_backed is False, "Infra app state lost deterministic status")
        check(client.get("/", follow_redirects=False).status_code == 307,
              "Infra root redirect failed")
        check(client.get("/app/contract").status_code == 200, "Infra contract route failed")
        health_status = client.get(infra_features.STATUS_PATH)
        check(health_status.status_code == 200, "Infra owned status endpoint failed")
        status_body = health_status.json()
        check(status_body["ready"] is True, "Infra is not marked complete")
        check(status_body["executor_mode"] == infra_features.EXECUTOR_MODE,
              "Infra status lost dry-run executor mode")
        check(status_body["commander_enabled"] is False,
              "Infra status unexpectedly enabled Commander")
        check(status_body["console_read_only"] is True,
              "Infra status lost read-only console")
        check(client.get(infra_features.CAPABILITIES_PATH).status_code == 200,
              "Infra capabilities endpoint failed")
        detectors = client.get(infra_features.DETECTORS_PATH)
        check(detectors.status_code == 200, "Infra detector-card endpoint failed")
        check(detectors.json()["organ_count"] == len(ORGAN_SPECS),
              "Infra detector card lost the active organ set")
        console = client.get(infra_features.CONSOLE_PATH)
        check(console.status_code == 200, "Infra console HTML failed")
        console_js = client.get(infra_features.CONSOLE_JS_PATH)
        check(console_js.status_code == 200, "Infra console JS failed")
        check("access_token" in console_js.text,
              "Infra console JS lost the read-token fallback")
        cookie_state = client.get(infra_features.STATE_PATH)
        check(cookie_state.status_code == 200, "Infra read-cookie fallback failed")
        query_state = TestClient(app).get(
            infra_features.STATE_PATH + "?access_token=integration-observer")
        check(query_state.status_code == 200, "Infra read-query fallback failed")
        write_query = TestClient(app).post(
            "/v1/telemetry?access_token=integration-observer", json={})
        check(write_query.status_code == 401,
              "query token must not authorize telemetry writes")
        override = client.post(
            "/v1/decisions/integration-probe/override",
            headers={"X-API-Token": "integration-admin"})
        check(override.status_code == 403, "append-only decision override was not refused")
        card = console_card()
        check(card["contract"] == "raksha-readonly-console-v2",
              "completed console contract changed")
        check(card["read_only"] is True and card["write_methods"] == [],
              "console is no longer read-only")
        check(app.state.infra_ready is True, "Infra app state lost ready flag")
        check(app.state.infra_status_path == infra_features.STATUS_PATH,
              "Infra app state lost status path")
        check(app.state.model_backed is False, "Infra app state is no longer deterministic")
        check(app.state.vigil_integrated is False, "Infra app state imported VIGIL")
        state = client.get("/v1/state", headers={"X-API-Token": "integration-observer"})
        check(state.status_code == 200, "Infra state route failed")
        state_body = state.json()
        check(state_body["model_backed"] is False and state_body["deterministic"] is True,
              "Infra state is not deterministic")
        check(state_body["dry_run"] is True, "Infra state is not dry-run")
        check(state_body["console_read_only"] is True, "Infra console is not read-only")

        hospital_ui = client.get(infra_features.HOSPITAL_DEMO_PATH)
        hospital_js = client.get(infra_features.HOSPITAL_DEMO_JS_PATH)
        check(hospital_ui.status_code == 200, "fake-hospital demo UI failed")
        check(hospital_js.status_code == 200, "fake-hospital demo JS failed")
        check("Play all" in hospital_ui.text, "fake-hospital demo lost play control")
        check("__RAKSHA_DEMO_TOKEN__" not in hospital_js.text,
              "fake-hospital demo JS token was not injected")
        hospital_state = client.get(infra_features.HOSPITAL_STATE_PATH)
        check(hospital_state.status_code == 200, "fake-hospital demo state failed")
        hospital_body = hospital_state.json()
        check(hospital_body["contract"] == infra_features.HOSPITAL_DEMO_CONTRACT,
              "fake-hospital demo contract changed")
        check(hospital_body["organization"]["kind"] == "fake_hospital",
              "fake-hospital organisation is not synthetic")
        total_steps = int(hospital_body["scenario"]["steps_total"])
        check(total_steps >= 8, "fake-hospital attack series is too short")
        unauth_step = TestClient(app).post(infra_features.HOSPITAL_STEP_PATH, json={})
        check(unauth_step.status_code == 401,
              "unauthenticated fake-hospital demo control was accepted")
        query_step = TestClient(app).post(
            infra_features.HOSPITAL_STEP_PATH + "?access_token=integration-observer",
            json={},
        )
        check(query_step.status_code == 401,
              "query token wrongly authorized fake-hospital demo control")
        live_ledger_before = app.state.runtime.ledger.height()
        live_detections_before = len(app.state.runtime.detections)
        last_demo_step = None
        for _ in range(total_steps):
            last_demo_step = client.post(infra_features.HOSPITAL_STEP_PATH, json={})
            check(last_demo_step.status_code == 200,
                  "fake-hospital demo step failed")
        check(last_demo_step is not None, "fake-hospital demo produced no step")
        final_demo_state = last_demo_step.json()["state"]
        demo_scenario = final_demo_state["scenario"]
        demo_runtime = final_demo_state["runtime"]
        check(demo_scenario["done"] is True
              and demo_scenario["campaign_fused"] is True,
              "fake-hospital attack series did not fuse and complete")
        check(demo_runtime["finding_count"] >= 6
              and demo_runtime["quarantine_count"] >= 3
              and demo_runtime["decision_count"] >= 1,
              "fake-hospital series did not exercise the runtime pipeline")
        check(demo_runtime["ledger_verify"]["ok"] is True,
              "fake-hospital demo ledger did not verify")
        check(demo_scenario["real_action_count"] == 0
              and demo_scenario["dry_run_action_count"] >= 1,
              "fake-hospital demo lost dry-run boundary")
        check(app.state.runtime.ledger.height() == live_ledger_before
              and len(app.state.runtime.detections) == live_detections_before,
              "fake-hospital demo mutated the canonical live runtime")
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("OK: completed deterministic, read-only Infra runtime; functional fake-hospital demo isolated and dry-run; Commander disabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
