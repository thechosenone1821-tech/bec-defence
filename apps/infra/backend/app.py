"""RAKSHA Infra / Sentinel unified app facade.

Phase 6–8 delegates the one app factory to ``packages.spine.runtime`` and
injects the one detector registry from ``apps.infra.detectors``. The legacy
``spine.bus`` model/Commander path is not imported or run.
"""
from __future__ import annotations

import argparse
import os
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from apps.infra.console import console_card, console_html, console_js
from apps.infra.detectors import detect as detect_event
from packages.spine.config import DEFAULT_POLICY, DEFAULT_TOPOLOGY
from packages.spine.contract import (
    BACKEND_CONTRACT_VERSION, BACKEND_ROUTES, EVENT_CONTRACT_VERSION,
    CANONICAL_JSON_RULE, SPINE_CONTRACT, validate_routes,
)
from packages.spine.runtime import create_app as create_runtime_app


def create_app(policy_path: Optional[str] = None,
               topology_path: Optional[str] = None,
               model: Optional[str] = None,
               *,
               sensor_key: Any = None,
               token_records: Any = None,
               console_token: str | None = None,
               seed_demo: bool = True,
               rate_limit_epm: int = 600,
               blast_cap: int = 3) -> FastAPI:
    """Create the one Infra app with the canonical detector and runtime."""
    app = create_runtime_app(
        detector=detect_event,
        sensor_key=sensor_key,
        token_records=token_records,
        console_token=console_token,
        policy_path=policy_path or str(DEFAULT_POLICY),
        topology_path=topology_path or str(DEFAULT_TOPOLOGY),
        model=model,
        seed_demo=seed_demo,
        rate_limit_epm=rate_limit_epm,
        blast_cap=blast_cap,
    )
    app.title = "RAKSHA Infra / Sentinel"

    @app.get("/", include_in_schema=False)
    async def root_console():
        return RedirectResponse(url="/app/console", status_code=307)

    @app.get("/app/health")
    async def app_health():
        return {
            "app": "infra",
            "status": "ok",
            "boundary": "apps/infra",
            "shared_spine": "packages/spine",
            "dry_run": True,
            "no_ai_models": True,
            "contract": SPINE_CONTRACT,
            "phase": "6-8 unified integration",
            "commander": app.state.runtime.commander,
        }

    @app.get("/app/contract")
    async def app_contract():
        return {
            "contract": BACKEND_CONTRACT_VERSION,
            "event_contract": EVENT_CONTRACT_VERSION,
            "canonical_json": CANONICAL_JSON_RULE,
            "signature_required": True,
            "governor_required": True,
            "append_only_ledger": True,
            "routes": [route.canonical for route in BACKEND_ROUTES],
            "route_check": validate_routes(app, "spine-v2"),
            "enterprise_route_check": validate_routes(app, "enterprise-i1"),
            "detector": "apps.infra.detectors.detect",
            "console": console_card(),
            "ledger_cli": "python -m packages.ledger.cli verify",
        }

    @app.get("/app/console", response_class=HTMLResponse)
    async def app_console():
        return HTMLResponse(console_html())

    @app.get("/app/console.js")
    async def app_console_js():
        return Response(console_js(app.state.console_token),
                        media_type="application/javascript")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="RAKSHA Infra / Sentinel unified service")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--topology", default=str(DEFAULT_TOPOLOGY))
    parser.add_argument("--model", default=os.environ.get("EIGENSHIELD_MODEL", "disabled"))
    parser.add_argument("--no-seed-demo", action="store_true",
                        help="start with an empty deterministic runtime")
    args = parser.parse_args()
    import uvicorn
    app = create_app(policy_path=args.policy, topology_path=args.topology,
                     model=args.model, seed_demo=not args.no_seed_demo)
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
