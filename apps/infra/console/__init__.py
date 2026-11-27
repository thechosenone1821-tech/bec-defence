"""Read-only SOC console assets for Phase 8.

The backend injects one read-scoped token into ``console.js``. The HTML and JS
contain no write route, override route, admin token, model endpoint or mutation
control.
"""
from __future__ import annotations

import json
from pathlib import Path

CONSOLE_DIR = Path(__file__).resolve().parent
CONSOLE_TOKEN_PLACEHOLDER = "__RAKSHA_READ_TOKEN__"


def console_html() -> str:
    return (CONSOLE_DIR / "index.html").read_text(encoding="utf-8")


def console_js(read_token: str) -> str:
    source = (CONSOLE_DIR / "console.js").read_text(encoding="utf-8")
    return source.replace(CONSOLE_TOKEN_PLACEHOLDER, json.dumps(str(read_token)))


def console_card() -> dict[str, object]:
    return {
        "contract": "raksha-readonly-console-v1",
        "read_only": True,
        "mutating_routes": [],
        "write_methods": [],
        "state_sources": ["/v1/state", "/v1/decisions", "/v1/ledger/verify",
                          "/v1/metrics", "/v1/quarantine"],
        "websocket": "/v1/telemetry/stream",
        "campaign_sequence": "detection -> proposal -> decision -> ledger",
        "refusals_visible": True,
    }


__all__ = ["CONSOLE_DIR", "CONSOLE_TOKEN_PLACEHOLDER", "console_html",
           "console_js", "console_card"]
