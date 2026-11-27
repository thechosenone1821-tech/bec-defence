"""Active Infra feature and status constants.

Infra is the deterministic, read-only, dry-run app. It never imports Citizen or
VIGIL, never enables Commander inference and never performs a live containment
action. These constants are the one source for Infra's owned status paths,
boot-manifest keys, app-state flags, gates and generated eval section.
"""
from __future__ import annotations

from typing import Any

APP_NAME = "infra"
BOUNDARY = "apps/infra"
SHARED_SPINE = "packages/spine"

MODEL_BACKED = False
DETERMINISTIC = True
DRY_RUN = True
ACTIVE_MODEL = "none"
VIGIL_INTEGRATED = False
EXECUTOR_MODE = "dry-run"
EXECUTOR = "DryRunExecutor-v1"
COMMANDER_ENABLED = False
CONSOLE_READ_ONLY = True
INTEGRATION_READY = True

HEALTH_PATH = "/app/health"
CONSOLE_PATH = "/app/console"
CONSOLE_JS_PATH = "/app/console.js"
CONTRACT_PATH = "/app/contract"
STATE_PATH = "/v1/state"
STATUS_PATH = "/api/infra/status"
CAPABILITIES_PATH = "/api/infra/capabilities"
DETECTORS_PATH = "/api/infra/detectors"
HOSPITAL_DEMO_PATH = "/demo/hospital"
HOSPITAL_DEMO_JS_PATH = "/demo/hospital.js"
HOSPITAL_STATE_PATH = "/api/infra/demo/hospital/state"
HOSPITAL_START_PATH = "/api/infra/demo/hospital/start"
HOSPITAL_STEP_PATH = "/api/infra/demo/hospital/step"
HOSPITAL_RESET_PATH = "/api/infra/demo/hospital/reset"
HOSPITAL_DEMO_CONTRACT = "raksha-fake-hospital-demo-v1"
FAKE_ORGANIZATION = "Aster Memorial Hospital (synthetic)"

READ_AUTH_FALLBACKS = (
    "Authorization: Bearer <read token>",
    "X-API-Token: <read token>",
    "raksha_read_token read cookie",
    "access_token query on read-only GET routes",
)

FEATURE_FLAGS = (
    "deterministic_runtime",
    "dry_run_executor",
    "read_only_console",
    "same_origin_status",
    "capability_card",
    "detector_card",
    "read_token_fallbacks",
    "append_only_ledger",
    "fake_hospital_attack_exercise",
)

CLAIMS_NOT_MADE = (
    "real-world detection accuracy",
    "production SLA",
    "live containment action",
    "Commander inference",
    "network capture",
    "real patient data",
    "real attack traffic",
)


def detector_detail_card() -> dict[str, Any]:
    """Return the one detector card plus UI-safe per-organ rule details."""
    from apps.infra.detectors.registry import ORGAN_SPECS, detector_card

    card: dict[str, Any] = dict(detector_card())
    card["organ_details"] = [
        {
            "name": spec.name,
            "ring": spec.ring,
            "legacy_organ": spec.legacy_organ,
            "rule_ids": [rule.rule_id for rule in spec.rules],
            "fixtures": sorted(spec.firing_payload),
        }
        for spec in ORGAN_SPECS
    ]
    return card


def hospital_demo_card() -> dict[str, Any]:
    """Return the honest fake-hospital exercise capability card."""
    return {
        "contract": HOSPITAL_DEMO_CONTRACT,
        "status": "ok",
        "functional": True,
        "organization": FAKE_ORGANIZATION,
        "synthetic": True,
        "ui_path": HOSPITAL_DEMO_PATH,
        "ui_js_path": HOSPITAL_DEMO_JS_PATH,
        "state_path": HOSPITAL_STATE_PATH,
        "controls": {
            "start": HOSPITAL_START_PATH,
            "step": HOSPITAL_STEP_PATH,
            "reset": HOSPITAL_RESET_PATH,
            "play": "client-side step loop",
        },
        "pipeline": [
            "signed_or_invalid_event",
            "envelope_quarantine",
            "detector_contract",
            "campaign_fusion",
            "governor",
            "append_only_ledger",
            "dry_run_executor",
        ],
        "isolated_runtime": True,
        "mutates_live_runtime": False,
        "real_network_actions": False,
        "real_patient_data": False,
        "executor_mode": EXECUTOR_MODE,
        "model_backed": MODEL_BACKED,
        "commander_enabled": COMMANDER_ENABLED,
        "real_action_count": 0,
        "claims_not_made": list(CLAIMS_NOT_MADE),
    }


def infra_card() -> dict[str, Any]:
    """Return the honest Infra status/capability constants."""
    return {
        "app": APP_NAME,
        "boundary": BOUNDARY,
        "shared_spine": SHARED_SPINE,
        "ready": INTEGRATION_READY,
        "status_path": STATUS_PATH,
        "capabilities_path": CAPABILITIES_PATH,
        "detectors_path": DETECTORS_PATH,
        "hospital_demo_path": HOSPITAL_DEMO_PATH,
        "hospital_state_path": HOSPITAL_STATE_PATH,
        "hospital_start_path": HOSPITAL_START_PATH,
        "hospital_step_path": HOSPITAL_STEP_PATH,
        "hospital_reset_path": HOSPITAL_RESET_PATH,
        "fake_organization": FAKE_ORGANIZATION,
        "hospital_demo": hospital_demo_card(),
        "health_path": HEALTH_PATH,
        "console_path": CONSOLE_PATH,
        "console_js_path": CONSOLE_JS_PATH,
        "contract_path": CONTRACT_PATH,
        "state_path": STATE_PATH,
        "model_backed": MODEL_BACKED,
        "deterministic": DETERMINISTIC,
        "dry_run": DRY_RUN,
        "active_model": ACTIVE_MODEL,
        "vigil_integrated": VIGIL_INTEGRATED,
        "executor_mode": EXECUTOR_MODE,
        "executor": EXECUTOR,
        "commander_enabled": COMMANDER_ENABLED,
        "console_read_only": CONSOLE_READ_ONLY,
        "read_auth_fallbacks": list(READ_AUTH_FALLBACKS),
        "feature_flags": list(FEATURE_FLAGS),
        "claims_not_made": list(CLAIMS_NOT_MADE),
    }


__all__ = [
    "APP_NAME", "BOUNDARY", "SHARED_SPINE", "MODEL_BACKED", "DETERMINISTIC",
    "DRY_RUN", "ACTIVE_MODEL", "VIGIL_INTEGRATED", "EXECUTOR_MODE", "EXECUTOR",
    "COMMANDER_ENABLED", "CONSOLE_READ_ONLY", "INTEGRATION_READY", "HEALTH_PATH",
    "CONSOLE_PATH", "CONSOLE_JS_PATH", "CONTRACT_PATH", "STATE_PATH",
    "STATUS_PATH", "CAPABILITIES_PATH", "DETECTORS_PATH", "HOSPITAL_DEMO_PATH",
    "HOSPITAL_DEMO_JS_PATH", "HOSPITAL_STATE_PATH", "HOSPITAL_START_PATH",
    "HOSPITAL_STEP_PATH", "HOSPITAL_RESET_PATH", "HOSPITAL_DEMO_CONTRACT",
    "FAKE_ORGANIZATION", "READ_AUTH_FALLBACKS", "FEATURE_FLAGS",
    "CLAIMS_NOT_MADE", "detector_detail_card", "hospital_demo_card",
    "infra_card",
]
