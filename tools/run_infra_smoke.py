#!/usr/bin/env python3
"""HTTP smoke for the completed deterministic Infra app.

This gate uses FastAPI's in-process TestClient. It proves the owned status,
capability, detector and console surfaces, read-token fallbacks, signed
telemetry ingest, dry-run decisions, append-only override refusal, ledger
verification and WebSocket history. It performs no live containment action.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from fastapi.testclient import TestClient  # noqa: E402

from apps.infra import features as infra_features  # noqa: E402
from apps.infra.backend.app import create_app  # noqa: E402
from apps.infra.console import console_card  # noqa: E402
from apps.infra.detectors.registry import ORGAN_FIXTURES, ORGAN_SPECS  # noqa: E402
from packages.contracts.envelope import sign_event  # noqa: E402

SENSOR_KEY = b"infra-http-smoke-key"
TOKENS = [
    ("smoke-admin", "admin", ("admin", "read", "telemetry:write")),
    ("smoke-sensor", "sensor", ("telemetry:write",)),
    ("smoke-observer", "observer", ("read",)),
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def signed_fixtures() -> list[dict[str, Any]]:
    """Two signed firing events across two legs fuse one deterministic campaign."""
    specs = (
        ("EV-INFRA-HTTP-SMOKE-CITIZEN", "cookie_fluid_turbulence", "citizen",
         "N-SMOKE-PHONE"),
        ("EV-INFRA-HTTP-SMOKE-INFRA", "page_curve_trap", "infra",
         "HOST_SMOKE"),
    )
    out: list[dict[str, Any]] = []
    for index, (event_id, organ, leg, entity) in enumerate(specs, start=1):
        raw = {
            "event_id": event_id,
            "ts": f"2026-11-26T00:00:{58 + index:02d}Z",
            "organ": organ,
            "campaign_id": "C-INFRA-HTTP-SMOKE",
            "case_id": "CASE-INFRA-HTTP-SMOKE",
            "leg": leg,
            "severity": 4,
            "entity": entity,
            "summary": "signed Infra HTTP smoke fixture",
            "payload": dict(ORGAN_FIXTURES[organ]["firing"]),
        }
        out.append(sign_event(raw, key=SENSOR_KEY))
    return out


def main() -> int:
    try:
        app = create_app(
            sensor_key=SENSOR_KEY,
            token_records=TOKENS,
            console_token="smoke-observer",
            seed_demo=True,
        )
        client = TestClient(app)

        health = client.get(infra_features.HEALTH_PATH)
        require(health.status_code == 200, "Infra health did not respond")
        health_body = health.json()
        require(health_body["infra_ready"] is True, "Infra is not marked complete")
        require(health_body["model_backed"] is False, "Infra became model-backed")
        require(health_body["deterministic"] is True, "Infra lost deterministic status")
        require(health_body["commander_enabled"] is False, "Commander became enabled")
        print("health: ready=yes deterministic=yes dry_run=yes Commander=disabled")

        status = client.get(infra_features.STATUS_PATH)
        capabilities = client.get(infra_features.CAPABILITIES_PATH)
        detectors = client.get(infra_features.DETECTORS_PATH)
        require(status.status_code == 200, "Infra status endpoint failed")
        require(capabilities.status_code == 200, "Infra capabilities endpoint failed")
        require(detectors.status_code == 200, "Infra detector endpoint failed")
        status_body = status.json()
        detector_body = detectors.json()
        require(status_body["status_path"] == infra_features.STATUS_PATH,
                "Infra status path changed")
        require(status_body["console_read_only"] is True,
                "Infra console is not read-only")
        require(detector_body["organ_count"] == len(ORGAN_SPECS),
                "Infra detector organ count changed")
        require(detector_body["registry_count"] == 1,
                "Infra has more than one detector registry")
        require(console_card()["contract"] == "raksha-readonly-console-v2",
                "completed console contract changed")
        print(f"status: ready=yes path={status_body['status_path']} "
              f"organs={detector_body['organ_count']} "
              f"registry={detector_body['registry_count']}")

        console = client.get(infra_features.CONSOLE_PATH)
        console_js = client.get(infra_features.CONSOLE_JS_PATH)
        require(console.status_code == 200, "Infra console HTML failed")
        require(console_js.status_code == 200, "Infra console JS failed")
        require("access_token" in console_js.text,
                "console JS lost read-token recovery")
        cookie_state = client.get(infra_features.STATE_PATH)
        require(cookie_state.status_code == 200, "read-cookie fallback failed")
        header_state = TestClient(app).get(
            infra_features.STATE_PATH,
            headers={"X-API-Token": "smoke-observer"},
        )
        require(header_state.status_code == 200, "read-header fallback failed")
        query_state = TestClient(app).get(
            infra_features.STATE_PATH + "?access_token=smoke-observer",
        )
        require(query_state.status_code == 200, "read-query fallback failed")
        write_query = TestClient(app).post(
            "/v1/telemetry?access_token=smoke-observer", json={},
        )
        require(write_query.status_code == 401,
                "query token must not authorize telemetry writes")
        print("auth: header/cookie/query read fallbacks OK; query write rejected")

        ingest_bodies = []
        for event in signed_fixtures():
            ingest = client.post(
                "/v1/telemetry",
                headers={"X-API-Token": "smoke-sensor"},
                json=event,
            )
            require(ingest.status_code == 200, "signed telemetry ingest failed")
            ingest_bodies.append(ingest.json())
        require(all(body["accepted"] is True for body in ingest_bodies),
                "a signed fixture was not accepted")
        require(all(body["verified"] == "valid" for body in ingest_bodies),
                "a signed fixture was not verified")
        detections = [item for body in ingest_bodies for item in body["detections"]]
        decisions = [item for body in ingest_bodies for item in body["decisions"]]
        executions = [item for body in ingest_bodies for item in body["executions"]]
        require(len(detections) >= 2,
                "signed firing fixtures did not produce findings")
        require(len(decisions) >= 1,
                "fused campaign did not produce dry-run decisions")
        require(len(executions) >= 1,
                "fused campaign did not traverse the dry-run executor")
        require(all(item.get("dry_run") is True and item.get("real_action") is False
                    for item in executions),
                "dry-run executor reported a real containment action")
        print(f"ingest: accepted=yes detections={len(detections)} "
              f"decisions={len(decisions)} "
              f"dry_run_executions={len(executions)}")

        read_paths = (
            "/v1/state", "/v1/decisions", "/v1/ledger/head",
            "/v1/ledger/verify", "/v1/quarantine", "/v1/metrics",
            "/v1/campaigns",
        )
        for path in read_paths:
            response = client.get(path + "?access_token=smoke-observer")
            require(response.status_code == 200, f"read route failed: {path}")
        verify = client.get("/v1/ledger/verify?access_token=smoke-observer").json()
        require(verify["ok"] is True, "runtime ledger did not verify")
        override = client.post(
            "/v1/decisions/smoke-probe/override",
            headers={"X-API-Token": "smoke-admin"},
        )
        require(override.status_code == 403,
                "append-only decision override was not refused")
        print(f"read: {len(read_paths)} routes OK; ledger=valid "
              f"height={verify['height']}; override=403")

        with client.websocket_connect(
            "/v1/telemetry/stream?token=smoke-observer",
        ) as websocket:
            first = websocket.receive_json()
        require(first.get("kind") is not None,
                "WebSocket stream returned no history item")
        print(f"websocket: connected first_kind={first['kind']}")

        demo_ui = client.get(infra_features.HOSPITAL_DEMO_PATH)
        demo_js = client.get(infra_features.HOSPITAL_DEMO_JS_PATH)
        require(demo_ui.status_code == 200,
                "fake-hospital demo UI failed")
        require(demo_js.status_code == 200,
                "fake-hospital demo JS failed")
        require("Play all" in demo_ui.text,
                "fake-hospital demo lost play control")
        demo_state = client.get(
            infra_features.HOSPITAL_STATE_PATH + "?access_token=smoke-observer",
        )
        require(demo_state.status_code == 200,
                "fake-hospital demo state failed")
        demo_body = demo_state.json()
        require(demo_body["contract"] == infra_features.HOSPITAL_DEMO_CONTRACT,
                "fake-hospital demo contract changed")
        require(demo_body["organization"]["kind"] == "fake_hospital",
                "fake-hospital organisation is not synthetic")
        total_demo_steps = int(demo_body["scenario"]["steps_total"])
        require(total_demo_steps >= 8, "fake-hospital attack series is too short")
        unauth_demo_step = TestClient(app).post(
            infra_features.HOSPITAL_STEP_PATH, json={},
        )
        require(unauth_demo_step.status_code == 401,
                "unauthenticated fake-hospital demo control was accepted")
        query_demo_step = TestClient(app).post(
            infra_features.HOSPITAL_STEP_PATH + "?access_token=smoke-observer",
            json={},
        )
        require(query_demo_step.status_code == 401,
                "query token wrongly authorized fake-hospital demo control")
        live_ledger_before = app.state.runtime.ledger.height()
        live_detections_before = len(app.state.runtime.detections)
        demo_headers = {"X-API-Token": "smoke-observer"}
        demo_reset = client.post(infra_features.HOSPITAL_RESET_PATH,
                                 headers=demo_headers, json={})
        require(demo_reset.status_code == 200
                and demo_reset.json()["state"]["scenario"]["steps_completed"] == 0,
                "fake-hospital demo reset failed")
        last_demo_step = None
        for _ in range(total_demo_steps):
            last_demo_step = client.post(infra_features.HOSPITAL_STEP_PATH,
                                         headers=demo_headers, json={})
            require(last_demo_step.status_code == 200,
                    "fake-hospital demo step failed")
        require(last_demo_step is not None, "fake-hospital demo produced no step")
        final_demo_state = last_demo_step.json()["state"]
        final_scenario = final_demo_state["scenario"]
        final_runtime = final_demo_state["runtime"]
        require(final_scenario["done"] is True
                and final_scenario["campaign_fused"] is True,
                "fake-hospital attack series did not fuse and complete")
        require(final_runtime["finding_count"] >= 6
                and final_runtime["quarantine_count"] >= 3
                and final_runtime["decision_count"] >= 1,
                "fake-hospital series did not exercise the runtime pipeline")
        require(final_runtime["ledger_verify"]["ok"] is True,
                "fake-hospital demo ledger did not verify")
        require(final_scenario["real_action_count"] == 0
                and final_scenario["dry_run_action_count"] >= 1,
                "fake-hospital demo lost dry-run boundary")
        require(app.state.runtime.ledger.height() == live_ledger_before
                and len(app.state.runtime.detections) == live_detections_before,
                "fake-hospital demo mutated the canonical live runtime")
        print(f"fake-hospital demo: attacks={final_scenario['steps_completed']} "
              f"findings={final_runtime['finding_count']} "
              f"quarantine={final_runtime['quarantine_count']} "
              f"decisions={final_runtime['decision_count']} "
              f"ledger={final_runtime['ledger_height']} "
              f"real_actions={final_scenario['real_action_count']}")

        require(app.state.infra_ready is True, "Infra app state lost ready flag")
        require(app.state.infra_status_path == infra_features.STATUS_PATH,
                "Infra app state lost status path")
        require(app.state.model_backed is False,
                "Infra app state became model-backed")
        require(app.state.vigil_integrated is False,
                "Infra app state imported VIGIL")
        print("app state: infra_ready=yes model_backed=no vigil_integrated=no")
        print("OK: Infra deterministic console + API smoke passed; "
              "read-token fallbacks work, fake-hospital exercise is functional "
              "and isolated, executor dry-run, Commander disabled")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
