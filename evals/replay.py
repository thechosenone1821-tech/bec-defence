#!/usr/bin/env python3
"""Phase 9 — the one deterministic end-to-end replay player.

The player POSTs the committed sandbox corpus into the active Infra API, then
reads state, ledger verification, decisions, quarantine and metrics. It signs
events with the shared envelope contract, never imports a model or legacy spine
bus, and proves that the only executor mode is dry-run. No host, VLAN, process,
session or network is changed. VoiceGuard is excluded from this runner.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from apps.infra.backend.app import create_app  # noqa: E402
from packages.contracts.envelope import sign_event  # noqa: E402
from evals.corpus import build_corpus  # noqa: E402

RESULTS_PATH = ROOT / "evals" / "results.json"
SENSOR_KEY = b"phase9-eval-sensor-key"
WRONG_KEY = b"phase9-eval-forged-key"
ADMIN = "phase9-eval-admin"
SENSOR = "phase9-eval-sensor"
OBSERVER = "phase9-eval-observer"


def _client() -> TestClient:
    app = create_app(
        sensor_key=SENSOR_KEY,
        token_records=[
            (ADMIN, "admin", ("admin", "read", "telemetry:write")),
            (SENSOR, "sensor", ("telemetry:write",)),
            (OBSERVER, "observer", ("read",)),
        ],
        console_token=OBSERVER,
        seed_demo=False,
        blast_cap=3,
    )
    return TestClient(app)


def _signed(step: dict[str, Any]) -> dict[str, Any]:
    raw = dict(step["raw"])
    kind = step["kind"]
    if kind == "unsigned":
        return raw
    key = WRONG_KEY if kind == "forged" else SENSOR_KEY
    body = sign_event(raw, key=key)
    if kind == "tampered":
        body = dict(body)
        body["severity"] = 2
    return body


def replay(corpus: dict[str, Any] | None = None) -> dict[str, Any]:
    corpus = corpus or build_corpus()
    steps = corpus["replay"]["steps"]
    client = _client()
    responses: list[dict[str, Any]] = []
    for step in steps:
        body = _signed(step)
        response = client.post("/v1/telemetry", json=body,
                               headers={"X-API-Token": SENSOR})
        if response.status_code != 200:
            raise RuntimeError(f"replay ingest failed for {step['id']}: {response.text}")
        responses.append(response.json())

    read = {"X-API-Token": OBSERVER}
    state = client.get("/v1/state", headers=read).json()
    verify = client.get("/v1/ledger/verify", headers=read).json()
    decisions = client.get("/v1/decisions", headers=read).json()
    quarantine = client.get("/v1/quarantine", headers=read).json()
    override = client.post("/v1/decisions/not-a-decision/override",
                           headers={"X-API-Token": ADMIN})
    health = client.get("/healthz").json()

    finding_count = sum(len(item.get("detections", [])) for item in responses)
    no_detection_count = sum(
        1 for item in responses
        if not item.get("quarantined") and not item.get("detections")
    )
    decision_count = sum(len(item.get("decisions", [])) for item in responses)
    execution_count = sum(len(item.get("executions", [])) for item in responses)
    quarantined_count = sum(1 for item in responses if item.get("quarantined"))
    real_action_count = sum(
        1 for item in responses for execution in item.get("executions", [])
        if execution.get("real_action") or execution.get("executed")
    )
    unsafe_decision_count = sum(
        1 for item in responses for decision in item.get("decisions", [])
        if decision.get("dry_run") is not True or decision.get("admin_override") is True
    )
    commander = state.get("commander") or {}
    model_invoked = bool(commander.get("model_invoked"))
    ok = (
        finding_count == sum(1 for s in steps if s["expected"] == "finding")
        and quarantined_count == sum(1 for s in steps if s["expected"] == "quarantined")
        and no_detection_count == sum(1 for s in steps if s["expected"] == "no_detection")
        and verify.get("valid") is True
        and real_action_count == 0
        and unsafe_decision_count == 0
        and state.get("no_ai_models") is True
        and state.get("dry_run") is True
        and model_invoked is False
        and override.status_code == 403
        and health.get("no_ai_models") is True
    )
    return {
        "condition": corpus["conditions"]["replay"],
        "source": "evals/replay.py + apps/infra/backend/app.py",
        "campaign_step_count": len(steps),
        "signed_event_count": sum(1 for s in steps if s["kind"] != "unsigned"),
        "finding_count": finding_count,
        "no_detection_count": no_detection_count,
        "quarantine_count": quarantined_count,
        "decision_count": decision_count,
        "execution_count": execution_count,
        "ledger_height": state.get("ledger_height"),
        "ledger_valid": bool(verify.get("valid")),
        "decisions_snapshot_count": decisions.get("count"),
        "quarantine_snapshot_count": quarantine.get("count"),
        "executor_real_action_count": real_action_count,
        "unsafe_decision_count": unsafe_decision_count,
        "admin_override_status_code": override.status_code,
        "no_ai_models": bool(state.get("no_ai_models")),
        "commander_model_invoked": model_invoked,
        "dry_run": bool(state.get("dry_run")),
        "voiceguard_included": False,
        "status": "ok" if ok else "fail",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify the committed replay section is current")
    args = parser.parse_args(argv)
    current = replay()
    if not args.check:
        print(json.dumps(current, sort_keys=True, indent=2))
        return 0 if current["status"] == "ok" else 1
    committed = json.loads(RESULTS_PATH.read_text(encoding="utf-8")) if RESULTS_PATH.exists() else {}
    if committed.get("sections", {}).get("replay") != current:
        print("FAIL: committed replay result is stale; rerun make eval", file=sys.stderr)
        return 1
    if current["status"] != "ok":
        print("FAIL: replay invariants did not hold", file=sys.stderr)
        return 1
    print("OK: one end-to-end sandbox replay is green; dry-run only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
