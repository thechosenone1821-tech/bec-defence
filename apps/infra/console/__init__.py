"""Read-only SOC console and fake-hospital demo assets.

The backend injects one read-scoped token into console/demo JS and also sets a
same-origin read cookie. The HTML and JS contain no write route to the live
runtime, override route, admin token, model endpoint or mutation control. GET
requests can fall back to a read-only query token when a preview proxy strips
authorization headers. The hospital demo controls only an isolated synthetic
scenario; they do not mutate the live deterministic campaign.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.infra import features as infra_features

CONSOLE_DIR = Path(__file__).resolve().parent
CONSOLE_TOKEN_PLACEHOLDER = "__RAKSHA_READ_TOKEN__"
HOSPITAL_TOKEN_PLACEHOLDER = "__RAKSHA_DEMO_TOKEN__"
READ_COOKIE = "raksha_read_token"


def console_html() -> str:
    return (CONSOLE_DIR / "index.html").read_text(encoding="utf-8")


def console_js(read_token: str) -> str:
    source = (CONSOLE_DIR / "console.js").read_text(encoding="utf-8")
    return source.replace(CONSOLE_TOKEN_PLACEHOLDER, json.dumps(str(read_token)))


def hospital_html() -> str:
    return (CONSOLE_DIR / "hospital.html").read_text(encoding="utf-8")


def hospital_js(read_token: str) -> str:
    source = (CONSOLE_DIR / "hospital.js").read_text(encoding="utf-8")
    return source.replace(HOSPITAL_TOKEN_PLACEHOLDER, json.dumps(str(read_token)))


def console_card() -> dict[str, Any]:
    return {
        "contract": "raksha-readonly-console-v2",
        "read_only": True,
        "mutating_routes": [],
        "write_methods": [],
        "status_path": infra_features.STATUS_PATH,
        "capabilities_path": infra_features.CAPABILITIES_PATH,
        "detectors_path": infra_features.DETECTORS_PATH,
        "hospital_demo_path": infra_features.HOSPITAL_DEMO_PATH,
        "hospital_state_path": infra_features.HOSPITAL_STATE_PATH,
        "hospital_start_path": infra_features.HOSPITAL_START_PATH,
        "hospital_step_path": infra_features.HOSPITAL_STEP_PATH,
        "hospital_reset_path": infra_features.HOSPITAL_RESET_PATH,
        "hospital_demo": infra_features.hospital_demo_card(),
        "fake_organization": infra_features.FAKE_ORGANIZATION,
        "health_path": infra_features.HEALTH_PATH,
        "contract_path": infra_features.CONTRACT_PATH,
        "console_path": infra_features.CONSOLE_PATH,
        "console_js_path": infra_features.CONSOLE_JS_PATH,
        "state_sources": [
            infra_features.STATE_PATH,
            "/v1/decisions",
            "/v1/ledger/head",
            "/v1/ledger/verify",
            "/v1/metrics",
            "/v1/quarantine",
            "/v1/campaigns",
            infra_features.STATUS_PATH,
            infra_features.CAPABILITIES_PATH,
            infra_features.DETECTORS_PATH,
            infra_features.HOSPITAL_STATE_PATH,
        ],
        "websocket": "/v1/telemetry/stream",
        "read_auth_fallbacks": list(infra_features.READ_AUTH_FALLBACKS),
        "read_cookie": READ_COOKIE,
        "download_snapshot": True,
        "campaign_sequence": "detection -> proposal -> decision -> ledger",
        "refusals_visible": True,
        "executor_mode": infra_features.EXECUTOR_MODE,
        "commander_enabled": infra_features.COMMANDER_ENABLED,
        "claims_not_made": list(infra_features.CLAIMS_NOT_MADE),
    }


__all__ = [
    "CONSOLE_DIR", "CONSOLE_TOKEN_PLACEHOLDER", "HOSPITAL_TOKEN_PLACEHOLDER",
    "READ_COOKIE", "console_html", "console_js", "hospital_html", "hospital_js",
    "console_card",
]
