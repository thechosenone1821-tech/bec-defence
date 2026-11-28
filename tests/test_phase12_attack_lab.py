"""Phase 12: the Attack Lab — scripted simulated attacks on the real pipeline.

The Infrastructure console can trigger scripted attack scenarios (suspicious
logins, a ransomware sweep, a coordinated agent flood, a hostile document, an
infrastructure anomaly, a kernel tamper, a staged exfiltration and one benign
control). These tests pin the two properties that make that safe to put in front
of an audience:

* every scripted event is posted to the **active ingest route** — signed steps
  signed with the same key resolution the gateway uses (``ingest_key()``), untrusted
  steps posted untouched — and the runtime's own answer matches the outcome the
  script declares. No step may claim a rule fires that ``detect(event)`` would
  skip, and no quiet step may be dressed up as caught;
* the run is repeatable and clearly synthetic: unique per-run ids, ``SIMULATED``
  labels inside the event itself, the console's own counters moving on trigger, and
  zero real actions.

``tools/check_frontend_integration.py`` audits the script against the detector
registry statically; :mod:`tools.run_frontend_smoke` drives the same library over
HTTP through both apps, the gateway and the built bundle. This file owns the
in-process contract.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.infra import features as infra_features
from apps.infra.backend.app import create_app
from apps.infra.demo.scenarios import SCENARIOS, catalogue_snapshot
from packages.contracts.envelope import ingest_key, sign_event
from packages.frontend import FRONTEND_BUILD_DIR

ROOT = Path(__file__).resolve().parents[1]
READ_TOKEN = "attack-lab-test-token"
HEADERS = {"X-API-Token": READ_TOKEN}
#: the runtime keeps event stamps verbatim, so a fixed clock keeps this file
#: reproducible; the browser substitutes a live stamp at trigger time instead
TS = "2026-11-27T04:00:00Z"


def _client() -> TestClient:
    """The Infra app with the shipped key resolution.

    The runtime, the gateway signer and this test all resolve the ingest key
    through :func:`packages.contracts.envelope.ingest_key`, so a signature minted
    here verifies for the same reason the gateway's does. Deliberately passing no
    ``sensor_key`` override keeps a foreign key modelled where it belongs: the
    unsigned and forged steps, which have to be refused.
    """
    app = create_app(
        token_records=[(READ_TOKEN, "console", ("admin", "read", "telemetry:write"))],
        console_token=READ_TOKEN,
        seed_demo=False,
    )
    return TestClient(app)


def _json(response) -> dict:
    assert response.status_code == 200, response.text
    return json.loads(response.text)


def _materialise(event: dict, tag: str) -> dict:
    """Fill the two tokens the served script leaves in, exactly as the page does."""
    return json.loads(json.dumps(event).replace("{tag}", tag).replace("{ts}", TS))


def _catalogue(client: TestClient) -> dict:
    return _json(client.get(infra_features.SCENARIOS_PATH))


def _state(client: TestClient) -> dict:
    return _json(client.get("/v1/state", headers=HEADERS))


def run_scenario(client: TestClient, scenario: dict, tag: str) -> list[tuple[dict, dict, str, set[str]]]:
    """Send one scenario in script order and classify each runtime answer.

    Signed events are signed here; the untrusted variants are posted exactly as the
    console posts them, so the refusal is the runtime's, not the test's. The
    returned status mirrors what the page colours a row with.
    """
    key = ingest_key()
    rows: list[tuple[dict, dict, str, set[str]]] = []
    for step in scenario["steps"]:
        event = _materialise(step["event"], tag)
        if step["envelope"] == "signed":
            event = sign_event(event, key)
        res = client.post("/api/ingest", json=event, headers=HEADERS)
        assert res.status_code == 200, f"{scenario['id']}/{step['key']}: {res.text[:200]}"
        body = res.json()
        detections = body.get("detections") or []
        status = ("quarantine" if body.get("quarantined")
                  else "finding" if detections else "no_detection")
        rows.append((step, body, status, {str(item.get("rule_id")) for item in detections}))
    assert len(rows) == len(scenario["steps"])
    return rows


def test_catalogue_is_a_read_only_script_that_labels_itself() -> None:
    client = _client()
    body = _catalogue(client)
    assert body["contract"] == infra_features.SCENARIOS_CONTRACT
    assert body["status"] == "ok"
    assert body["simulated"] is True and body["synthetic"] is True
    assert body["attack_executed"] is False and body["live_action_paths"] == 0
    assert body["dry_run"] is True and body["model_backed"] is False
    assert body["commander_enabled"] is False
    assert body["label"] == "SIMULATED"
    assert len(body["scenarios"]) == len(SCENARIOS) >= 8
    assert len(body["organs"]) == 8
    assert {row["id"] for row in body["scenarios"]} >= {
        "suspicious-login", "infra-anomaly", "ai-agent-flood", "ransomware-sweep",
        "benign-baseline",
    }
    totals = body["totals"]
    assert totals["scenarios"] == len(body["scenarios"])
    assert totals["steps"] == sum(len(row["steps"]) for row in body["scenarios"])
    assert (totals["firing_steps"] + totals["quiet_steps"] + totals["held_steps"]
            == totals["steps"])
    assert "real-world detection accuracy" in body["claims_not_made"]
    assert any("append-only" in note for note in body["notes"])

    for scenario in body["scenarios"]:
        assert scenario["simulated"] is True
        assert scenario["campaign_id"].startswith("SIMULATED-")
        assert scenario["case_id"].startswith("SIMULATED-CASE-")
        assert scenario["step_count"] == len(scenario["steps"])
        assert [step["index"] for step in scenario["steps"]] == list(
            range(1, len(scenario["steps"]) + 1))
        for step in scenario["steps"]:
            event = step["event"]
            assert event["summary"].startswith("SIMULATED · "), step["key"]
            assert "{tag}" in event["event_id"], "ids must be re-tagged per run"
            assert "{ts}" in event["ts"], "timestamps must be live, not scripted"
            assert event["organ"] == step["organ"]
            assert set(event["payload"]) <= set(step["payload"])
            if step["expects"] == "finding":
                assert step["rule_reason"], f"{step['key']} lost its registry rule reason"
            elif step["expects"] == "no_detection":
                # a quiet step names no rule — that is the point of a control step
                assert not step["expects_rule"]
                assert step["fixture"] in {"silent", "missing"}
            else:
                # a held step still names the rule it *would* have fired, so the
                # console can say what was refused as well as how it was refused
                assert step["envelope"] in {"unsigned", "forged"}

    # the route serves a script; it must never accept a mutation
    assert client.post(infra_features.SCENARIOS_PATH, json={}).status_code == 405
    one = client.get(f"{infra_features.SCENARIOS_PATH}/suspicious-login")
    assert one.status_code == 200 and one.json()["id"] == "suspicious-login"
    missing = client.get(f"{infra_features.SCENARIOS_PATH}/not-a-scenario")
    assert missing.status_code == 404
    assert missing.json()["error"] == "unknown_scenario"
    assert not [route for route in client.app.routes
                if str(getattr(route, "path", "")).startswith(f"{infra_features.SCENARIOS_PATH}/")
                and "POST" in (getattr(route, "methods", None) or set())]

    capabilities = _json(client.get(infra_features.CAPABILITIES_PATH))
    card = capabilities["attack_scenarios"]
    # the capability card is the same object on both surfaces, so the console
    # cannot read a different scenario count than the status endpoint reports
    assert capabilities["infra"]["attack_scenarios"] == card
    assert capabilities["scenarios_path"] == infra_features.SCENARIOS_PATH
    assert _json(client.get(infra_features.STATUS_PATH))["attack_scenarios"] == card
    assert card["catalogue_path"] == infra_features.SCENARIOS_PATH
    assert card["scenario_count"] == len(SCENARIOS)
    assert card["step_count"] == totals["steps"]
    assert card["real_action_count"] == 0 and card["executor_mode"] == "dry-run"
    assert card["attack_tooling"] is False and card["functional"] is True
    assert "simulated_attack_scenarios" in infra_features.FEATURE_FLAGS
    # the app registers the route through the shared constant, not a literal
    source = (ROOT / "apps" / "infra" / "backend" / "app.py").read_text(encoding="utf-8")
    assert "infra_features.SCENARIOS_PATH" in source


def test_scenario_organs_cover_the_registry_and_match_their_fixtures() -> None:
    from apps.infra.detectors.registry import ORGAN_FIXTURES

    snapshot = catalogue_snapshot()
    scripted = {step["organ"] for scenario in snapshot["scenarios"] for step in scenario["steps"]}
    assert scripted == set(ORGAN_FIXTURES)
    for scenario in snapshot["scenarios"]:
        for step in scenario["steps"]:
            assert step["payload"] == ORGAN_FIXTURES[step["organ"]][step["fixture"]]
            assert step["ring"], f"{step['organ']} lost its ring label"
            assert 1 <= int(step["severity"]) <= 5
            assert step["expects"] in {"finding", "no_detection", "quarantine"}
    # both legs are exercised, so cross-leg fusion is demonstrable rather than claimed
    legs = {step["leg"] for scenario in snapshot["scenarios"] for step in scenario["steps"]}
    assert legs == {"citizen", "infra"}
    totals = snapshot["totals"]
    assert totals["firing_steps"] >= 15 and totals["quiet_steps"] >= 8
    assert totals["held_steps"] >= 4


def test_every_scenario_answers_exactly_as_scripted() -> None:
    client = _client()
    scenarios = {row["id"]: row for row in _catalogue(client)["scenarios"]}
    for index, scenario_id in enumerate(sorted(scenarios), start=1):
        scenario = scenarios[scenario_id]
        campaign = f"SIMULATED-{scenario_id}-script{index}"
        for step, body, status, rules in run_scenario(client, scenario, f"script{index}"):
            assert status == step["expects"], (
                f"{scenario_id}/{step['key']} claims {step['expects']}, runtime says "
                f"{status} ({body.get('reason')})")
            assert body, f"{scenario_id}/{step['key']} produced no ingest result"
            if step["expects"] == "finding":
                assert step["expects_rule"] in rules, (scenario_id, step["key"], rules)
                assert body["accepted"] is True and body["verified"] == "valid"
                detection = body["detections"][0]
                assert detection["campaign_id"] == campaign
                assert detection["organ"] == step["organ"]
                assert detection["reason"] == step["rule_reason"]
                assert detection["ts"] == TS
                assert detection["verified"] is True and detection["actionable"] is True
            elif step["expects"] == "no_detection":
                assert body["accepted"] is True and body["verified"] == "valid"
                assert not rules and not body["quarantined"]
            else:
                # an unverified event is still ingested — as evidence — but it must
                # never reach a detection, a proposal, a decision or an execution
                assert body["quarantined"] is True and body["verified"] in {"unsigned", "tampered"}
                assert not rules
                assert not body.get("proposals") and not body.get("decisions")
                assert not body.get("executions")
            # nothing on this surface ever executes for real
            for execution in body.get("executions") or []:
                # an allowed proposal is simulated, a refused one is skipped: both
                # are recorded and neither touches a host
                assert execution["status"] in {"SIMULATED", "SKIPPED_REFUSAL"}, execution
                assert execution["executed"] is False and execution["dry_run"] is True
                assert execution["real_action"] is False
            for decision in body.get("decisions") or []:
                assert decision.get("real_action") is not True


def test_trigger_moves_the_dashboard_and_the_control_path_stays_dry_run() -> None:
    client = _client()
    scenarios = {row["id"]: row for row in _catalogue(client)["scenarios"]}
    before = _state(client)
    assert before["detections"] == [] and before["ledger_height"] == 0
    assert before["dry_run"] is True and before["model_backed"] is False

    # a benign control must not move the alarm counters — a run that cannot stay
    # quiet is not a control
    benign = run_scenario(client, scenarios["benign-baseline"], "benign1")
    after_benign = _state(client)
    assert after_benign["detections"] == []
    assert after_benign["quarantine_count"] == 0
    assert all(status == "no_detection" for _, _, status, _ in benign)

    for scenario_id, tag in (("suspicious-login", "login1"), ("staged-exfil", "exfil1")):
        rows = run_scenario(client, scenarios[scenario_id], tag)
        assert any(status == "finding" for _, _, status, _ in rows), scenario_id

    after = _state(client)
    campaign_rows = {str(row["campaign_id"]): row for row in after["campaigns"]}
    assert {"SIMULATED-suspicious-login-login1", "SIMULATED-staged-exfil-exfil1"} <= set(campaign_rows)
    findings = [row for row in after["detections"] if str(row["event_id"]).startswith("evt_sim_")]
    assert findings, "the scripted attacks produced no sealed detections"
    assert all(str(row["campaign_id"]).startswith("SIMULATED-") for row in findings)
    assert any(row["fused"] and set(row["legs"]) == {"citizen", "infra"}
               for row in after["campaigns"]), "no scripted campaign fused across both legs"
    assert after["quarantine_count"] >= 3, "the unsigned and forged steps were not held"
    assert after["ledger_height"] > after_benign["ledger_height"], "the runs left no ledger evidence"
    organs = {str(row["organ"]) for row in findings}
    assert organs, "no organ reported the scripted findings"

    verify = _json(client.get("/v1/ledger/verify", headers=HEADERS))
    assert verify["ok"] is True and verify["valid"] is True, verify
    assert verify["height"] == after["ledger_height"]

    quarantine = _json(client.get("/v1/quarantine", headers=HEADERS))
    held_states = {str(item.get("state")) for item in quarantine["items"]}
    assert held_states <= {"unsigned", "tampered"} and held_states
    assert all(item.get("actionable") is False for item in quarantine["items"])
    assert all(item.get("detection_performed") is False for item in quarantine["items"])

    metrics = _json(client.get("/v1/metrics", headers=HEADERS))["counters"]
    assert metrics["detect.flagged"] >= len(findings)
    assert metrics["decide.allowed"] >= 1, "the Governor never ruled on the scripted campaigns"
    assert metrics["executor.simulated"] >= 1, "no simulated containment action was recorded"
    assert "executor.executed" not in metrics, "an executor reported real actions"

    decisions = _json(client.get("/v1/decisions", headers=HEADERS))
    rows = decisions if isinstance(decisions, list) else (decisions.get("decisions") or [])
    assert rows, "the decision log is empty after a run that produced Governor verdicts"
    for row in rows:
        assert row.get("real_action") is not True
        assert row.get("executed") is not True
    plan = _json(client.post("/api/orchestrate", json={}, headers=HEADERS))
    assert plan["ledger_height"] == after["ledger_height"]
    assert any(str(row["campaign_id"]).startswith("SIMULATED-") for row in plan["campaigns"])

    # and the console's own compat view reports the same run without inventing keys
    view = _json(client.get("/api/state", headers=HEADERS))
    assert view["detections"], "the state view lost the scripted findings"
    assert view["quarantine_count"] == after["quarantine_count"]


def test_a_run_can_be_repeated_and_a_replayed_id_is_refused_not_replayed() -> None:
    client = _client()
    scenario = _catalogue(client)["scenarios"][0]
    first = run_scenario(client, scenario, "repeat-a")
    second = run_scenario(client, scenario, "repeat-b")
    assert [status for _, _, status, _ in first] == [status for _, _, status, _ in second]
    assert [sorted(rules) for _, _, _, rules in first] == [sorted(rules) for _, _, _, rules in second]
    assert ([row[1]["event_id"] for row in first]
            != [row[1]["event_id"] for row in second]), "per-run tags did not change the ids"
    state = _state(client)
    sim_campaigns = [str(row["campaign_id"]) for row in state["campaigns"]
                     if str(row["campaign_id"]).startswith("SIMULATED-")]
    assert len(sim_campaigns) == 2, sim_campaigns

    # re-sending the same tag reuses event ids: the runtime must refuse the replay,
    # and the console has to tell that apart from a detection
    replayed = run_scenario(client, scenario, "repeat-a")
    signed = [(step, body, status) for step, body, status, _ in replayed
              if step["envelope"] == "signed"]
    assert signed, "the scenario has no signed steps to replay"
    for step, body, status in signed:
        assert status == "no_detection", (step["key"], body)
        assert "duplicate" in str(body.get("reason", "")).lower(), (step["key"], body)
        assert body["accepted"] is False

    metrics = _json(client.get("/v1/metrics", headers=HEADERS))["counters"]
    assert metrics["ingest.duplicate"] >= len(signed)
    after = _state(client)
    assert len([row for row in after["detections"]
                if str(row["event_id"]).startswith("evt_sim_")]) == (
        len([row for row in state["detections"]
             if str(row["event_id"]).startswith("evt_sim_")])
    ), "a replayed run added detections it did not earn"


def test_console_serves_the_attack_lab_as_its_own_document() -> None:
    client = _client()
    page = client.get("/console/attack-lab/")
    assert page.status_code == 200
    expected = (FRONTEND_BUILD_DIR / "console" / "attack-lab" / "index.html").read_bytes()
    assert page.content == expected, "the Attack Lab is not served as its own prerender"
    assert page.content != (FRONTEND_BUILD_DIR / "index.html").read_bytes()
    assert page.headers["cache-control"] == "no-store"
    assert "ARK OMNITEK" in page.text
    for secret in (READ_TOKEN, f"{infra_features.SCENARIOS_PATH}?token"):
        assert secret not in page.text

    apps_source = (ROOT / "frontend" / "src" / "lib" / "apps.ts").read_text(encoding="utf-8")
    assert 'id: "attack-lab"' in apps_source
    assert 'route: "/console/attack-lab"' in apps_source
    assert "Eight scripted attack scenarios" in apps_source
    assert 'mode: "organization"' in apps_source

    page_source = ROOT / "frontend" / "src" / "app" / "console" / "attack-lab" / "page.tsx"
    assert page_source.is_file(), "the console route needs its own page module"
    assert 'appId="attack-lab"' in page_source.read_text(encoding="utf-8")

    source = (ROOT / "frontend" / "src" / "components" / "features" / "attack-lab.tsx"
              ).read_text(encoding="utf-8")
    # one trigger per scenario, a reset, and no invented state on the client
    assert "onTrigger(scenario)" in source and "runScenario(" in source
    assert 'variant="danger"' in source and "Reset" in source
    for fabricated in ("setTimeout(() => setEvents", "localStorage", "sessionStorage"):
        assert fabricated not in source, f"the Attack Lab invents state with {fabricated}"
    assert '"/api/state"' in source, "the dashboard must read the runtime's own state view"
    assert "ALERT ·" in source, "a fired step has to raise a visible alert"
    assert "spineSigned" not in source, "signing must stay inside lib/gateway.ts"

    manifest = json.loads((ROOT / "apps" / "infra" / "BOOT_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["attack_scenarios_path"] == infra_features.SCENARIOS_PATH
    assert manifest["attack_scenarios_contract"] == infra_features.SCENARIOS_CONTRACT
    assert manifest["attack_scenarios_simulated"] is True
