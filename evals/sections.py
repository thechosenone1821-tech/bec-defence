"""Active capability sections for the one eval runner.

Citizen, MessageGuard, organ, governance and VIGIL measurements are computed
from committed fixtures, local model artifacts and the one active detector
registry. Infra remains deterministic and dry-run. VIGIL local training metrics
are reported without inferring real-world privacy efficacy.
"""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from apps.citizen import features  # noqa: E402
from apps.citizen.api import build_app as build_citizen_app  # noqa: E402
from apps.infra import features as infra_features  # noqa: E402
from apps.infra.backend.app import create_app as build_infra_app  # noqa: E402
from apps.infra.console import console_card  # noqa: E402
from apps.infra.detectors.registry import (  # noqa: E402
    ORGAN_FIXTURES, ORGAN_SPECS, detect, detector_card,
)
from packages.contracts.config import DEFAULT_TOPOLOGY  # noqa: E402
from packages.contracts.envelope import sign_event  # noqa: E402
from packages.governance.safety import (  # noqa: E402
    ALLOWED_ACTIONS, PLANNER_ID, DryRunExecutor, ExhaustivePlanner, Governor,
    Proposal, Topology, UnsafeProposal,
)
from packages.vigil.config import (  # noqa: E402
    DEFAULT_WEIGHTS_CANDIDATES, HARDWARE_CONFIG, PROTECTION_POLICIES,
    SEMANTIC_CLASSES,
)
from evals.messageguard import compute_results as messageguard_results  # noqa: E402

SENSOR_KEY = b"active-sections-sensor-key"
INFRA_SENSOR_KEY = b"active-infra-sections-key"
MANIFEST_PATH = ROOT / "packages" / "vigil" / "model_manifest.json"
HISTORY_PATH = ROOT / "packages" / "vigil" / "privacynet_history.json"


def _raw(event_id: str, organ: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "ts": "2026-11-26T09:00:00Z",
        "organ": organ,
        "campaign_id": "C-ACTIVE-SECTIONS",
        "case_id": "CASE-ACTIVE-SECTIONS",
        "leg": "infra",
        "severity": 4,
        "entity": "HOST_EVAL_SECTIONS",
        "summary": f"active section fixture {event_id}",
        "payload": dict(payload),
    }


def citizen_section() -> dict[str, Any]:
    app = build_citizen_app(bus_url="", poster=lambda event: {"accepted": 1})
    client = TestClient(app)
    health = client.get("/api/citizen/health")
    feature_response = client.get("/api/citizen/features")
    manifest = client.get("/app/manifest.json")
    root = client.get("/", follow_redirects=False)
    dashboard = client.get("/vigil/", follow_redirects=False)
    static_asset = client.get("/vigil/static/app.js")
    status_endpoint = client.get(features.VIGIL_STATUS_PATH)
    health_body = health.json() if health.status_code == 200 else {}
    status_body = status_endpoint.json() if status_endpoint.status_code == 200 else {}
    model_active = bool((status_body.get("model_status") or {}).get("is_neural_active"))
    ok = (
        health.status_code == 200
        and feature_response.status_code == 200
        and manifest.status_code == 200
        and root.status_code == 307
        and dashboard.status_code == 200
        and static_asset.status_code == 200
        and status_endpoint.status_code == 200
        and model_active is True
        and (status_body.get("vigil") or {}).get("status_path") == features.VIGIL_STATUS_PATH
        and health_body.get("model_backed") is True
        and health_body.get("active_model") == features.ACTIVE_MODEL
        and (health_body.get("vigil") or {}).get("enabled") is True
        and getattr(app.state, "model_backed", False) is True
        and getattr(app.state, "vigil_integrated", False) is True
    )
    return {
        "condition": "fixture / sandbox",
        "source": "apps/citizen/api.py + packages/vigil/main.py",
        "health_status_code": health.status_code,
        "features_status_code": feature_response.status_code,
        "manifest_status_code": manifest.status_code,
        "root_redirect_status_code": root.status_code,
        "vigil_dashboard_status_code": dashboard.status_code,
        "vigil_static_status_code": static_asset.status_code,
        "vigil_status_status_code": status_endpoint.status_code,
        "feature_flag_count": len(features.FEATURE_FLAGS),
        "app_route_count": len(app.routes),
        "model_backed": bool(health_body.get("model_backed")),
        "active_model": str(health_body.get("active_model")),
        "vigil_enabled": bool((health_body.get("vigil") or {}).get("enabled")),
        "vigil_model_active": model_active,
        "app_state_model_backed": bool(getattr(app.state, "model_backed", False)),
        "app_state_vigil_integrated": bool(getattr(app.state, "vigil_integrated", False)),
        "status": "ok" if ok else "fail",
    }



def infra_section() -> dict[str, Any]:
    """Exercise the completed deterministic Infra app and console auth paths."""
    app = build_infra_app(
        sensor_key=INFRA_SENSOR_KEY,
        token_records=[
            ("sections-admin", "admin", ("admin", "read", "telemetry:write")),
            ("sections-sensor", "sensor", ("telemetry:write",)),
            ("sections-observer", "observer", ("read",)),
        ],
        console_token="sections-observer",
        seed_demo=True,
    )
    client = TestClient(app)
    health = client.get(infra_features.HEALTH_PATH)
    console = client.get(infra_features.CONSOLE_PATH)
    console_js = client.get(infra_features.CONSOLE_JS_PATH)
    status = client.get(infra_features.STATUS_PATH)
    capabilities = client.get(infra_features.CAPABILITIES_PATH)
    detectors = client.get(infra_features.DETECTORS_PATH)

    cookie_state = client.get(infra_features.STATE_PATH)
    header_state = TestClient(app).get(
        infra_features.STATE_PATH,
        headers={"X-API-Token": "sections-observer"},
    )
    query_state = TestClient(app).get(
        infra_features.STATE_PATH + "?access_token=sections-observer",
    )
    read_routes = {
        name: client.get(path + "?access_token=sections-observer").status_code
        for name, path in {
            "decisions": "/v1/decisions",
            "ledger_head": "/v1/ledger/head",
            "ledger_verify": "/v1/ledger/verify",
            "quarantine": "/v1/quarantine",
            "metrics": "/v1/metrics",
            "campaigns": "/v1/campaigns",
        }.items()
    }
    override = client.post(
        "/v1/decisions/sections-probe/override",
        headers={"X-API-Token": "sections-admin"},
    )
    write_query = TestClient(app).post(
        "/v1/telemetry?access_token=sections-observer", json={},
    )
    with client.websocket_connect(
        "/v1/telemetry/stream?token=sections-observer",
    ) as websocket:
        first_stream_item = websocket.receive_json()

    hospital_ui = client.get(infra_features.HOSPITAL_DEMO_PATH)
    hospital_js = client.get(infra_features.HOSPITAL_DEMO_JS_PATH)
    hospital_state = client.get(
        infra_features.HOSPITAL_STATE_PATH,
        headers={"X-API-Token": "sections-observer"},
    )
    hospital_unauth = TestClient(app).post(
        infra_features.HOSPITAL_STEP_PATH, json={},
    )
    hospital_query_control = TestClient(app).post(
        infra_features.HOSPITAL_STEP_PATH + "?access_token=sections-observer",
        json={},
    )
    hospital_headers = {"X-API-Token": "sections-observer"}
    hospital_reset = client.post(
        infra_features.HOSPITAL_RESET_PATH, headers=hospital_headers, json={},
    )
    hospital_state_body = hospital_state.json() if hospital_state.status_code == 200 else {}
    hospital_total_steps = int(hospital_state_body.get("scenario", {}).get("steps_total", 0))
    live_ledger_before = app.state.runtime.ledger.height()
    live_detections_before = len(app.state.runtime.detections)
    hospital_step_status_codes: list[int] = []
    last_hospital_response = None
    for _ in range(hospital_total_steps):
        last_hospital_response = client.post(
            infra_features.HOSPITAL_STEP_PATH,
            headers=hospital_headers,
            json={},
        )
        hospital_step_status_codes.append(last_hospital_response.status_code)
    hospital_final = (last_hospital_response.json()["state"]
                      if last_hospital_response is not None
                      and last_hospital_response.status_code == 200 else {})
    hospital_scenario = hospital_final.get("scenario", {})
    hospital_runtime = hospital_final.get("runtime", {})
    hospital_ledger_verify = hospital_runtime.get("ledger_verify", {})
    hospital_live_runtime_unchanged = (
        app.state.runtime.ledger.height() == live_ledger_before
        and len(app.state.runtime.detections) == live_detections_before
    )

    status_body = status.json() if status.status_code == 200 else {}
    capabilities_body = capabilities.json() if capabilities.status_code == 200 else {}
    detectors_body = detectors.json() if detectors.status_code == 200 else {}
    state_body = cookie_state.json() if cookie_state.status_code == 200 else {}
    card = console_card()
    ok = (
        health.status_code == 200
        and console.status_code == 200
        and console_js.status_code == 200
        and status.status_code == 200
        and capabilities.status_code == 200
        and detectors.status_code == 200
        and cookie_state.status_code == 200
        and header_state.status_code == 200
        and query_state.status_code == 200
        and all(code == 200 for code in read_routes.values())
        and override.status_code == 403
        and write_query.status_code == 401
        and "access_token" in console_js.text
        and status_body.get("ready") is True
        and status_body.get("executor_mode") == infra_features.EXECUTOR_MODE
        and status_body.get("commander_enabled") is False
        and status_body.get("console_read_only") is True
        and status_body.get("model_backed") is False
        and status_body.get("deterministic") is True
        and capabilities_body.get("contract") == "raksha-infra-capabilities-v1"
        and detectors_body.get("registry_count") == 1
        and detectors_body.get("organ_count") == len(ORGAN_SPECS)
        and state_body.get("console_read_only") is True
        and state_body.get("dry_run") is True
        and getattr(app.state, "infra_ready", False) is True
        and getattr(app.state, "infra_status_path", None) == infra_features.STATUS_PATH
        and getattr(app.state, "model_backed", True) is False
        and getattr(app.state, "vigil_integrated", True) is False
        and card["contract"] == "raksha-readonly-console-v2"
        and card["read_only"] is True
        and card["write_methods"] == []
        and card["mutating_routes"] == []
        and first_stream_item.get("kind") is not None
        and hospital_ui.status_code == 200
        and hospital_js.status_code == 200
        and hospital_state.status_code == 200
        and hospital_unauth.status_code == 401
        and hospital_query_control.status_code == 401
        and hospital_reset.status_code == 200
        and hospital_total_steps >= 8
        and len(hospital_step_status_codes) == hospital_total_steps
        and all(code == 200 for code in hospital_step_status_codes)
        and hospital_final.get("organization", {}).get("kind") == "fake_hospital"
        and hospital_final.get("contract") == infra_features.HOSPITAL_DEMO_CONTRACT
        and hospital_scenario.get("done") is True
        and hospital_scenario.get("campaign_fused") is True
        and hospital_scenario.get("executor_mode") == "dry-run"
        and hospital_scenario.get("commander_enabled") is False
        and hospital_scenario.get("real_action_count") == 0
        and hospital_scenario.get("dry_run_action_count", 0) >= 1
        and hospital_runtime.get("finding_count", 0) >= 6
        and hospital_runtime.get("quarantine_count", 0) >= 3
        and hospital_runtime.get("decision_count", 0) >= 1
        and hospital_ledger_verify.get("ok") is True
        and hospital_live_runtime_unchanged is True
    )
    return {
        "condition": "fixture / sandbox",
        "source": "apps/infra/backend/app.py + apps/infra/features.py + apps/infra/console/ + apps/infra/demo/",
        "health_status_code": health.status_code,
        "console_status_code": console.status_code,
        "console_js_status_code": console_js.status_code,
        "status_endpoint_status_code": status.status_code,
        "capabilities_endpoint_status_code": capabilities.status_code,
        "detectors_endpoint_status_code": detectors.status_code,
        "cookie_fallback_status_code": cookie_state.status_code,
        "header_fallback_status_code": header_state.status_code,
        "query_fallback_status_code": query_state.status_code,
        "read_route_status_codes": read_routes,
        "admin_override_status_code": override.status_code,
        "write_query_rejected_status_code": write_query.status_code,
        "read_auth_fallback_count": len(infra_features.READ_AUTH_FALLBACKS),
        "detector_organ_count": int(detectors_body.get("organ_count", 0)),
        "detector_registry_count": int(detectors_body.get("registry_count", 0)),
        "app_state_infra_ready": bool(getattr(app.state, "infra_ready", False)),
        "app_state_status_path": str(getattr(app.state, "infra_status_path", "")),
        "app_state_model_backed": bool(getattr(app.state, "model_backed", True)),
        "app_state_vigil_integrated": bool(getattr(app.state, "vigil_integrated", True)),
        "console_contract": card["contract"],
        "console_read_only": bool(card["read_only"]),
        "console_write_methods": len(card["write_methods"]),
        "console_mutating_routes": len(card["mutating_routes"]),
        "executor_mode": infra_features.EXECUTOR_MODE,
        "commander_enabled": infra_features.COMMANDER_ENABLED,
        "model_backed": infra_features.MODEL_BACKED,
        "deterministic": infra_features.DETERMINISTIC,
        "websocket_first_kind": str(first_stream_item.get("kind") or ""),
        "hospital_demo_ui_status_code": hospital_ui.status_code,
        "hospital_demo_js_status_code": hospital_js.status_code,
        "hospital_demo_state_status_code": hospital_state.status_code,
        "hospital_demo_unauth_status_code": hospital_unauth.status_code,
        "hospital_demo_query_control_status_code": hospital_query_control.status_code,
        "hospital_demo_reset_status_code": hospital_reset.status_code,
        "hospital_demo_attack_steps": len(hospital_step_status_codes),
        "hospital_demo_step_status_codes_ok": sum(
            code == 200 for code in hospital_step_status_codes
        ),
        "hospital_demo_synthetic_organization": bool(
            hospital_final.get("organization", {}).get("kind") == "fake_hospital"
        ),
        "hospital_demo_campaign_fused": bool(hospital_scenario.get("campaign_fused")),
        "hospital_demo_findings": int(hospital_runtime.get("finding_count", 0)),
        "hospital_demo_quarantine_count": int(hospital_runtime.get("quarantine_count", 0)),
        "hospital_demo_decision_count": int(hospital_runtime.get("decision_count", 0)),
        "hospital_demo_ledger_height": int(hospital_runtime.get("ledger_height", 0)),
        "hospital_demo_dry_run_action_count": int(hospital_scenario.get("dry_run_action_count", 0)),
        "hospital_demo_real_action_count": int(hospital_scenario.get("real_action_count", 0)),
        "hospital_demo_ledger_valid": bool(hospital_ledger_verify.get("ok")),
        "hospital_demo_live_runtime_unchanged": bool(hospital_live_runtime_unchanged),
        "hospital_demo_executor_mode": str(hospital_scenario.get("executor_mode", "")),
        "hospital_demo_commander_enabled": bool(hospital_scenario.get("commander_enabled")),
        "status": "ok" if ok else "fail",
    }


def messageguard_section() -> dict[str, Any]:
    return messageguard_results()


def organ_section() -> dict[str, Any]:
    firing = silent = missing = 0
    for index, spec in enumerate(ORGAN_SPECS, start=1):
        for bundle in ("firing", "silent", "missing"):
            raw = _raw(f"EV-ORG-{index:02d}-{bundle}", spec.name,
                       ORGAN_FIXTURES[spec.name][bundle])
            result = detect(sign_event(raw, key=SENSOR_KEY), key=SENSOR_KEY).to_dict()
            status = result["status"]
            if bundle == "firing" and status == "finding":
                firing += 1
            elif bundle == "silent" and status == "no_detection":
                silent += 1
            elif bundle == "missing" and status == "no_detection":
                missing += 1

    quarantine = 0
    unknown = 0
    for index, kind in enumerate(("unsigned", "tampered", "forged", "unknown_organ"), start=1):
        organ = "not_a_registered_organ" if kind == "unknown_organ" else "page_curve_trap"
        raw = _raw(f"EV-Q-{index:02d}", organ,
                   ORGAN_FIXTURES["page_curve_trap"]["firing"])
        if kind == "unsigned":
            body = raw
        else:
            key = b"active-forged-key" if kind == "forged" else SENSOR_KEY
            body = sign_event(raw, key=key)
            if kind == "tampered":
                body = dict(body)
                body["severity"] = 1
        result = detect(body, key=SENSOR_KEY).to_dict()
        if result["status"] == "quarantined" and not (result.get("quarantine") or {}).get("detection_performed"):
            quarantine += 1
            if kind == "unknown_organ":
                unknown += 1

    card = detector_card()
    ok = (
        firing == len(ORGAN_SPECS)
        and silent == len(ORGAN_SPECS)
        and missing == len(ORGAN_SPECS)
        and quarantine == 4
        and unknown == 1
        and card["registry_count"] == 1
        and card["quarantine_before_detection"] is True
    )
    return {
        "condition": "synthetic / sandbox",
        "source": "apps/infra/detectors/registry.py",
        "organ_count": len(ORGAN_SPECS),
        "registry_count": card["registry_count"],
        "fixture_bundle_count": sum(len(bundle) for bundle in ORGAN_FIXTURES.values()),
        "firing_findings": firing,
        "silent_no_detection": silent,
        "missing_no_detection": missing,
        "quarantine_before_detection": quarantine,
        "unknown_organ_quarantine": unknown,
        "status": "ok" if ok else "fail",
    }


def governance_section() -> dict[str, Any]:
    topology = Topology.from_path(DEFAULT_TOPOLOGY)
    planner = ExhaustivePlanner(topology)
    governor = Governor(blast_cap=3)
    executor = DryRunExecutor()
    campaign = {"campaign_id": "C-ACTIVE-GOVERNANCE", "case_id": "CASE-ACTIVE-GOVERNANCE"}
    proposals = planner.proposals_for(campaign)
    decisions = [governor.decide(proposal) for proposal in proposals]
    executions = [executor.execute(decision) for decision in decisions]
    allowed = sum(1 for decision in decisions if decision.verdict == "ALLOWED")
    refused = len(decisions) - allowed
    real_actions = sum(1 for item in executions if item.get("real_action") or item.get("executed"))

    crown_rejected = 0
    crown_asset = sorted(topology.crown_assets)[0]
    try:
        Proposal(
            campaign_id=campaign["campaign_id"], action="node_quarantine",
            entity=crown_asset, assets_severed=(crown_asset,), edges_cut=(),
            blast_radius=(crown_asset,), detail="crown cut must be impossible",
            fallback_proposal_id=None, planner_id=PLANNER_ID,
            crown_assets=topology.crown_assets,
            crown_gateway_edges=topology.crown_gateway_edges,
        )
    except UnsafeProposal:
        crown_rejected = 1

    ok = (
        len(proposals) > 0
        and allowed + refused == len(proposals)
        and real_actions == 0
        and crown_rejected == 1
        and all(item["dry_run"] is True for item in executions)
    )
    return {
        "condition": "sandbox",
        "source": "packages/governance/safety.py",
        "proposal_count": len(proposals),
        "allowed_count": allowed,
        "refused_count": refused,
        "blast_cap": 3,
        "allowed_action_count": len(ALLOWED_ACTIONS),
        "executor_real_action_count": real_actions,
        "crown_cut_attempts_rejected": crown_rejected,
        "admin_override": "impossible",
        "status": "ok" if ok else "fail",
    }


def vigil_section() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    active = manifest["active_deployment_model"]
    app = build_citizen_app(bus_url="", poster=lambda event: {"accepted": 1})
    client = TestClient(app)
    dashboard = client.get("/vigil/", follow_redirects=False)
    static_asset = client.get("/vigil/static/app.js")
    overview = client.get("/vigil/api/overview")
    model_status = overview.json()["model_status"] if overview.status_code == 200 else {}
    local_epochs = len(history["val_loss"])
    ok = (
        dashboard.status_code == 200
        and static_asset.status_code == 200
        and overview.status_code == 200
        and model_status.get("is_neural_active") is True
        and model_status.get("architecture") == "TorchScript_VigilPrivacyNet"
        and model_status.get("weights_file") == active["filename"]
        and DEFAULT_WEIGHTS_CANDIDATES[0].name == active["filename"]
        and manifest["claim_policy"]["real_world_privacy_efficacy"] == "UNMEASURED"
        and local_epochs > 0
    )
    return {
        "condition": "local training / fixture; real-world UNMEASURED",
        "sources": [
            "packages/vigil/model_manifest.json",
            "packages/vigil/privacynet_history.json",
            "packages/vigil/config.py",
            "apps/citizen/api.py",
        ],
        "dashboard_status_code": dashboard.status_code,
        "static_status_code": static_asset.status_code,
        "overview_status_code": overview.status_code,
        "active_model": active["filename"],
        "model_status": model_status,
        "model_input_size": HARDWARE_CONFIG.model_input_size,
        "semantic_class_count": len(SEMANTIC_CLASSES),
        "policy_count": len(PROTECTION_POLICIES),
        "local_epochs": local_epochs,
        "local_metrics": manifest["independent_test_metrics"],
        "training_history": history,
        "local_metrics_only": True,
        "privacy_efficacy": "UNMEASURED",
        "claims_not_made": list(manifest["claim_policy"]["claims_not_made"]),
        "status": "ok" if ok else "fail",
    }


__all__ = [
    "citizen_section", "infra_section", "messageguard_section", "organ_section",
    "governance_section", "vigil_section",
]
