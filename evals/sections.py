"""Phase 9 — deterministic capability sections for the one eval runner.

Citizen, organ, governance and MessageGuard measurements are computed here from
committed fixtures, the one detector registry and the one Governor. The
end-to-end replay lives in :mod:`evals.replay`. Nothing in this module imports a
model, Commander endpoint, legacy spine bus, frozen VoiceGuard/MAYA asset, live
executor or network service.
"""
from __future__ import annotations

import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from apps.citizen import features  # noqa: E402
from apps.citizen.api import build_app as build_citizen_app  # noqa: E402
from apps.infra.detectors.registry import (  # noqa: E402
    ORGAN_FIXTURES, ORGAN_SPECS, detect, detector_card,
)
from packages.contracts.config import DEFAULT_TOPOLOGY  # noqa: E402
from packages.contracts.envelope import sign_event  # noqa: E402
from packages.governance.safety import (  # noqa: E402
    ALLOWED_ACTIONS, PLANNER_ID, DryRunExecutor, ExhaustivePlanner, Governor,
    Proposal, Topology, UnsafeProposal,
)
from evals.messageguard import compute_results as messageguard_results  # noqa: E402

SENSOR_KEY = b"phase9-sections-sensor-key"


def _raw(event_id: str, organ: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "ts": "2026-11-26T09:00:00Z",
        "organ": organ,
        "campaign_id": "C-P9-SECTIONS",
        "case_id": "CASE-P9-SECTIONS",
        "leg": "infra",
        "severity": 4,
        "entity": "HOST_EVAL_SECTIONS",
        "summary": f"phase 9 section fixture {event_id}",
        "payload": dict(payload),
    }


def citizen_section() -> dict[str, Any]:
    app = build_citizen_app(bus_url="", poster=lambda event: {"accepted": 1})
    client = TestClient(app)
    health = client.get("/api/citizen/health")
    feature_response = client.get("/api/citizen/features")
    manifest = client.get("/app/manifest.json")
    root = client.get("/", follow_redirects=False)
    health_body = health.json() if health.status_code == 200 else {}
    ok = (
        health.status_code == 200
        and feature_response.status_code == 200
        and manifest.status_code == 200
        and root.status_code == 307
        and bool(health_body.get("no_ai_models")) is True
        and bool((health_body.get("voiceguard") or {}).get("enabled")) is False
    )
    return {
        "condition": "fixture / sandbox",
        "source": "apps/citizen/api.py",
        "health_status_code": health.status_code,
        "features_status_code": feature_response.status_code,
        "manifest_status_code": manifest.status_code,
        "root_redirect_status_code": root.status_code,
        "feature_flag_count": len(features.FEATURE_FLAGS),
        "app_route_count": len(app.routes),
        "no_ai_models": bool(health_body.get("no_ai_models")),
        "voiceguard_enabled": bool((health_body.get("voiceguard") or {}).get("enabled")),
        "voiceguard_integrated": False,
        "status": "ok" if ok else "fail",
    }


def messageguard_section() -> dict[str, Any]:
    return messageguard_results()


def organ_section() -> dict[str, Any]:
    firing = silent = missing = 0
    for index, spec in enumerate(ORGAN_SPECS, start=1):
        for bundle in ("firing", "silent", "missing"):
            raw = _raw(f"EV-P9-ORG-{index:02d}-{bundle}", spec.name,
                       ORGAN_FIXTURES[spec.name][bundle])
            result = detect(sign_event(raw, key=SENSOR_KEY), key=SENSOR_KEY).to_dict()
            status = result["status"]
            if bundle == "firing" and status == "finding":
                firing += 1
            elif bundle in ("silent", "missing") and status == "no_detection":
                if bundle == "silent":
                    silent += 1
                else:
                    missing += 1

    quarantine = 0
    unknown = 0
    for index, kind in enumerate(("unsigned", "tampered", "forged", "unknown_organ"), start=1):
        organ = "not_a_registered_organ" if kind == "unknown_organ" else "page_curve_trap"
        raw = _raw(f"EV-P9-Q-{index:02d}", organ,
                   ORGAN_FIXTURES["page_curve_trap"]["firing"])
        if kind == "unsigned":
            body = raw
        else:
            key = b"phase9-forged-key" if kind == "forged" else SENSOR_KEY
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
        and card["frozen_voiceguard_integrated"] is False
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
        "voiceguard_integrated": False,
        "status": "ok" if ok else "fail",
    }


def governance_section() -> dict[str, Any]:
    topology = Topology.from_path(DEFAULT_TOPOLOGY)
    planner = ExhaustivePlanner(topology)
    governor = Governor(blast_cap=3)
    executor = DryRunExecutor()
    campaign = {"campaign_id": "C-P9-GOVERNANCE", "case_id": "CASE-P9-GOVERNANCE"}
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
        "voiceguard_integrated": False,
        "status": "ok" if ok else "fail",
    }


__all__ = ["citizen_section", "messageguard_section", "organ_section", "governance_section"]
