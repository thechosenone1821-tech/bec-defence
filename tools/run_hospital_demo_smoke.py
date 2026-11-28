#!/usr/bin/env python3
"""Functional smoke for the fake-hospital Infra attack exercise.

Proves that the UI surface and control API exist, that a series of synthetic
attacks traverses the detector/Governor/ledger/dry-run executor path, and that
the isolated scenario leaves the canonical live runtime untouched. No real
traffic, hospital data, Commander inference or live containment is involved.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from fastapi.testclient import TestClient  # noqa: E402

from apps.infra import features as infra_features  # noqa: E402
from apps.infra.backend.app import create_app  # noqa: E402

TOKENS = [
    ("hospital-admin", "admin", ("admin", "read", "telemetry:write")),
    ("hospital-sensor", "sensor", ("telemetry:write",)),
    ("hospital-observer", "observer", ("read",)),
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    try:
        app = create_app(
            sensor_key=b"hospital-demo-smoke-key",
            token_records=TOKENS,
            console_token="hospital-observer",
            seed_demo=False,
        )
        client = TestClient(app)
        headers = {"X-API-Token": "hospital-observer"}
        live_ledger_before = app.state.runtime.ledger.height()
        live_detections_before = len(app.state.runtime.detections)

        ui = client.get(infra_features.HOSPITAL_DEMO_PATH)
        ui_js = client.get(infra_features.HOSPITAL_DEMO_JS_PATH)
        require(ui.status_code == 200, "fake-hospital demo HTML did not load")
        require(ui_js.status_code == 200, "fake-hospital demo JS did not load")
        require("Start scenario" in ui.text and "Play all" in ui.text,
                "fake-hospital demo controls are missing")
        require("__RAKSHA_DEMO_TOKEN__" not in ui_js.text,
                "fake-hospital demo JS token was not injected")

        state = client.get(infra_features.HOSPITAL_STATE_PATH, headers=headers)
        require(state.status_code == 200, "fake-hospital demo state did not load")
        state_body = state.json()
        require(state_body["contract"] == infra_features.HOSPITAL_DEMO_CONTRACT,
                "fake-hospital demo contract changed")
        require(state_body["organization"]["kind"] == "fake_hospital",
                "fake-hospital organisation is not explicitly synthetic")
        require(state_body["scenario"]["steps_total"] >= 8,
                "fake-hospital attack series is too short")
        require(state_body["scenario"]["executor_mode"] == "dry-run",
                "fake-hospital demo is not dry-run")
        require(state_body["scenario"]["commander_enabled"] is False,
                "fake-hospital demo unexpectedly enabled Commander")
        print(f"ui: path={infra_features.HOSPITAL_DEMO_PATH} "
              f"steps={state_body['scenario']['steps_total']} "
              f"assets={len(state_body['assets'])}")

        unauth = TestClient(app).post(infra_features.HOSPITAL_STEP_PATH, json={})
        require(unauth.status_code == 401,
                "fake-hospital demo control accepted an unauthenticated request")
        query_only = TestClient(app).post(
            infra_features.HOSPITAL_STEP_PATH + "?access_token=hospital-observer",
            json={},
        )
        require(query_only.status_code == 401,
                "query token wrongly authorized a demo control mutation")

        reset = client.post(infra_features.HOSPITAL_RESET_PATH, headers=headers, json={})
        require(reset.status_code == 200
                and reset.json()["state"]["scenario"]["steps_completed"] == 0,
                "fake-hospital demo reset failed")
        start = client.post(infra_features.HOSPITAL_START_PATH, headers=headers, json={})
        require(start.status_code == 200 and start.json()["step"]["index"] == 1,
                "fake-hospital demo start did not expose attack one")
        require(start.json()["step"]["outcome"] == "finding",
                "first fake-hospital attack did not produce a finding")

        remaining = state_body["scenario"]["steps_total"] - 1
        last = None
        for _ in range(remaining):
            last = client.post(infra_features.HOSPITAL_STEP_PATH,
                               headers=headers, json={})
            require(last.status_code == 200, "fake-hospital demo step failed")
        require(last is not None, "fake-hospital demo produced no steps")
        final = last.json()["state"]
        scenario = final["scenario"]
        runtime = final["runtime"]
        require(scenario["done"] is True
                and scenario["steps_completed"] == scenario["steps_total"],
                "fake-hospital attack series did not complete")
        require(scenario["campaign_fused"] is True,
                "fake-hospital campaign did not fuse")
        require(runtime["finding_count"] >= 6,
                "fake-hospital series did not exercise the detector path")
        require(runtime["quarantine_count"] >= 3,
                "fake-hospital series did not exercise quarantine")
        require(runtime["decision_count"] >= 1,
                "fake-hospital series did not exercise the Governor")
        require(runtime["ledger_verify"]["ok"] is True,
                "fake-hospital demo ledger did not verify")
        require(scenario["real_action_count"] == 0
                and scenario["dry_run_action_count"] >= 1,
                "fake-hospital demo lost its dry-run/no-real-action boundary")
        require(app.state.runtime.ledger.height() == live_ledger_before
                and len(app.state.runtime.detections) == live_detections_before,
                "fake-hospital demo mutated the canonical live runtime")
        print(f"scenario: attacks={scenario['steps_completed']} "
              f"findings={runtime['finding_count']} "
              f"quarantine={runtime['quarantine_count']} "
              f"decisions={runtime['decision_count']} "
              f"ledger={runtime['ledger_height']} "
              f"dry_run_actions={scenario['dry_run_action_count']} "
              f"real_actions={scenario['real_action_count']}")
        print("OK: functional fake-hospital attack series passed UI/API/runtime smoke; "
              "isolated, deterministic, ledger-verified, dry-run only")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
