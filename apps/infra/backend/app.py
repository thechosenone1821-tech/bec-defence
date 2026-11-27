"""RAKSHA Infra / Sentinel completed deterministic app facade.

Phase 6–8 delegates the one app factory to ``packages.spine.runtime`` and
injects the one detector registry from ``apps.infra.detectors``. The legacy
``spine.bus``/Commander live-action path is not imported or run. This facade
adds Infra-owned status, capability and detector cards, a read-token cookie
for preview proxies, and the read-only SOC console.
"""
from __future__ import annotations

import argparse
import os
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from apps.infra import features as infra_features
from apps.infra.console import (
    READ_COOKIE, console_card, console_html, console_js, hospital_html,
    hospital_js,
)
from apps.infra.demo.hospital import HospitalScenario
from apps.infra.detectors import detect as detect_event
from packages.spine.config import DEFAULT_POLICY, DEFAULT_TOPOLOGY
from packages.spine.contract import (
    BACKEND_CONTRACT_VERSION, BACKEND_ROUTES, EVENT_CONTRACT_VERSION,
    CANONICAL_JSON_RULE, SPINE_CONTRACT, validate_routes,
)
from packages.spine.runtime import AuthError, create_app as create_runtime_app


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
    """Create the one completed Infra app with the canonical detector/runtime."""
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

    app.state.infra_ready = infra_features.INTEGRATION_READY
    app.state.app_name = infra_features.APP_NAME
    app.state.boundary = infra_features.BOUNDARY
    app.state.shared_spine = infra_features.SHARED_SPINE
    app.state.model_backed = infra_features.MODEL_BACKED
    app.state.deterministic = infra_features.DETERMINISTIC
    app.state.dry_run = infra_features.DRY_RUN
    app.state.active_model = infra_features.ACTIVE_MODEL
    app.state.vigil_integrated = infra_features.VIGIL_INTEGRATED
    app.state.executor_mode = infra_features.EXECUTOR_MODE
    app.state.executor = infra_features.EXECUTOR
    app.state.commander_enabled = infra_features.COMMANDER_ENABLED
    app.state.console_read_only = infra_features.CONSOLE_READ_ONLY
    app.state.health_path = infra_features.HEALTH_PATH
    app.state.console_path = infra_features.CONSOLE_PATH
    app.state.console_js_path = infra_features.CONSOLE_JS_PATH
    app.state.contract_path = infra_features.CONTRACT_PATH
    app.state.state_path = infra_features.STATE_PATH
    app.state.infra_status_path = infra_features.STATUS_PATH
    app.state.capabilities_path = infra_features.CAPABILITIES_PATH
    app.state.detectors_path = infra_features.DETECTORS_PATH
    app.state.detector_card = infra_features.detector_detail_card()
    app.state.hospital_demo = HospitalScenario(
        policy_path=policy_path or str(DEFAULT_POLICY),
    )
    app.state.hospital_demo_ready = True
    app.state.hospital_demo_contract = infra_features.HOSPITAL_DEMO_CONTRACT
    app.state.hospital_demo_path = infra_features.HOSPITAL_DEMO_PATH
    app.state.hospital_demo_js_path = infra_features.HOSPITAL_DEMO_JS_PATH
    app.state.hospital_state_path = infra_features.HOSPITAL_STATE_PATH
    app.state.hospital_start_path = infra_features.HOSPITAL_START_PATH
    app.state.hospital_step_path = infra_features.HOSPITAL_STEP_PATH
    app.state.hospital_reset_path = infra_features.HOSPITAL_RESET_PATH
    app.state.fake_organization = infra_features.FAKE_ORGANIZATION
    app.state.hospital_demo_card = infra_features.hospital_demo_card()

    def _app_state_card() -> dict[str, Any]:
        return {
            "infra_ready": bool(getattr(app.state, "infra_ready", False)),
            "model_backed": bool(getattr(app.state, "model_backed", True)),
            "deterministic": bool(getattr(app.state, "deterministic", False)),
            "dry_run": bool(getattr(app.state, "dry_run", False)),
            "vigil_integrated": bool(getattr(app.state, "vigil_integrated", True)),
            "executor_mode": str(getattr(app.state, "executor_mode", "unknown")),
            "commander_enabled": bool(getattr(app.state, "commander_enabled", True)),
            "console_read_only": bool(getattr(app.state, "console_read_only", False)),
            "status_path": str(getattr(app.state, "infra_status_path", "")),
            "capabilities_path": str(getattr(app.state, "capabilities_path", "")),
            "detectors_path": str(getattr(app.state, "detectors_path", "")),
            "fake_hospital_demo": bool(getattr(app.state, "hospital_demo_ready", False)),
            "hospital_demo_path": str(getattr(app.state, "hospital_demo_path", "")),
            "hospital_state_path": str(getattr(app.state, "hospital_state_path", "")),
            "fake_organization": str(getattr(app.state, "fake_organization", "")),
        }

    def _set_read_cookie(response: Response, request: Request) -> Response:
        response.set_cookie(
            READ_COOKIE,
            str(app.state.console_token),
            max_age=3600,
            path="/",
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
        )
        return response

    def _demo_auth(request: Request, *, allow_query: bool) -> None:
        """Authorize isolated demo controls with a read-scoped console token.

        The demo state is separate from the live runtime; POST here mutates
        neither real telemetry nor the app's canonical campaign. Query tokens
        remain read-only GET fallbacks and never authorize demo controls.
        """
        candidates: list[tuple[str, str]] = []
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            candidates.append((header[7:].strip(), "header"))
        header = request.headers.get("x-api-token", "").strip()
        if header:
            candidates.append((header, "header"))
        cookie = request.cookies.get(READ_COOKIE, "").strip()
        if cookie:
            candidates.append((cookie, "cookie"))
        query = request.query_params.get("access_token", "").strip()
        if query and allow_query:
            candidates.append((query, "query"))
        for token, source in candidates:
            if not token:
                continue
            try:
                record = app.state.token_store.authenticate(token)
            except AuthError:
                continue
            if source == "query" and (
                "admin" in record.scopes or "telemetry:write" in record.scopes
            ):
                raise HTTPException(
                    403,
                    "query token is read-only; use a scoped header or cookie",
                )
            if "read" not in record.scopes and "admin" not in record.scopes:
                raise HTTPException(403, "token lacks read scope")
            return
        raise HTTPException(401, "missing API token")

    def _demo_json(payload: dict[str, Any], request: Request) -> JSONResponse:
        return _set_read_cookie(JSONResponse(payload), request)

    @app.get("/", include_in_schema=False)
    async def root_console():
        return RedirectResponse(url=infra_features.CONSOLE_PATH, status_code=307)

    @app.get(infra_features.HEALTH_PATH)
    async def app_health():
        return {
            "app": infra_features.APP_NAME,
            "status": "ok",
            "ready": infra_features.INTEGRATION_READY,
            "infra_ready": infra_features.INTEGRATION_READY,
            "boundary": infra_features.BOUNDARY,
            "shared_spine": infra_features.SHARED_SPINE,
            "dry_run": infra_features.DRY_RUN,
            "model_backed": infra_features.MODEL_BACKED,
            "deterministic": infra_features.DETERMINISTIC,
            "active_model": infra_features.ACTIVE_MODEL,
            "vigil_integrated": infra_features.VIGIL_INTEGRATED,
            "executor_mode": infra_features.EXECUTOR_MODE,
            "executor": infra_features.EXECUTOR,
            "commander_enabled": infra_features.COMMANDER_ENABLED,
            "console_read_only": infra_features.CONSOLE_READ_ONLY,
            "contract": SPINE_CONTRACT,
            "commander": app.state.runtime.commander,
            "status_path": infra_features.STATUS_PATH,
            "capabilities_path": infra_features.CAPABILITIES_PATH,
            "detectors_path": infra_features.DETECTORS_PATH,
            "hospital_demo": infra_features.hospital_demo_card(),
            "fake_organization": infra_features.FAKE_ORGANIZATION,
            "app_state": _app_state_card(),
        }

    @app.get(infra_features.CONTRACT_PATH)
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
            "infra": infra_features.infra_card(),
            "console": console_card(),
            "hospital_demo": infra_features.hospital_demo_card(),
            "detectors": infra_features.detector_detail_card(),
            "app_state": _app_state_card(),
            "ledger_cli": "python -m packages.ledger.cli verify",
        }

    @app.get(infra_features.STATUS_PATH)
    async def infra_status():
        card = infra_features.infra_card()
        card.update({
            "status": "ok",
            "runtime_contract": "raksha-infra-runtime-v1",
            "console": console_card(),
            "detectors": infra_features.detector_detail_card(),
            "hospital_demo": infra_features.hospital_demo_card(),
            "hospital_state": app.state.hospital_demo.state_snapshot()["scenario"],
            "commander": dict(app.state.runtime.commander),
            "route_count": len(app.routes),
            "app_state": _app_state_card(),
        })
        return card

    @app.get(infra_features.CAPABILITIES_PATH)
    async def infra_capabilities():
        return {
            "contract": "raksha-infra-capabilities-v1",
            "status_path": infra_features.STATUS_PATH,
            "health_path": infra_features.HEALTH_PATH,
            "console_path": infra_features.CONSOLE_PATH,
            "state_path": infra_features.STATE_PATH,
            "infra": infra_features.infra_card(),
            "console": console_card(),
            "hospital_demo": infra_features.hospital_demo_card(),
            "detectors": infra_features.detector_detail_card(),
            "backend_contract": {
                "contract": BACKEND_CONTRACT_VERSION,
                "event_contract": EVENT_CONTRACT_VERSION,
                "canonical_json": CANONICAL_JSON_RULE,
                "spine_route_check": validate_routes(app, "spine-v2"),
                "enterprise_route_check": validate_routes(app, "enterprise-i1"),
            },
            "read_paths": [
                infra_features.STATE_PATH, "/v1/decisions", "/v1/ledger/head",
                "/v1/ledger/verify", "/v1/quarantine", "/v1/metrics",
                "/v1/campaigns", infra_features.STATUS_PATH,
                infra_features.CAPABILITIES_PATH, infra_features.DETECTORS_PATH,
                infra_features.HOSPITAL_STATE_PATH,
            ],
            "backend_write_paths": [
                {"path": "/v1/telemetry", "scope": "telemetry:write"},
                {"path": "/v1/ledger/entries", "scope": "admin"},
            ],
            "append_only_override_path": "/v1/decisions/{proposal_id}/override",
            "demo_control_paths": [
                {"path": infra_features.HOSPITAL_START_PATH, "scope": "read", "isolated": True},
                {"path": infra_features.HOSPITAL_STEP_PATH, "scope": "read", "isolated": True},
                {"path": infra_features.HOSPITAL_RESET_PATH, "scope": "read", "isolated": True},
            ],
            "console_write_methods": [],
            "console_mutating_routes": [],
            "auth": {
                "read_header": "Authorization: Bearer <read token>",
                "read_alt_header": "X-API-Token: <read token>",
                "read_cookie": READ_COOKIE,
                "read_query": "access_token on read-only GET routes",
                "write": "scoped header or cookie; query tokens are read-only",
            },
            "claims_not_made": list(infra_features.CLAIMS_NOT_MADE),
        }

    @app.get(infra_features.DETECTORS_PATH)
    async def infra_detectors():
        return infra_features.detector_detail_card()

    @app.get(infra_features.CONSOLE_PATH, response_class=HTMLResponse)
    async def app_console(request: Request):
        return _set_read_cookie(HTMLResponse(console_html()), request)

    @app.get(infra_features.CONSOLE_JS_PATH)
    async def app_console_js(request: Request):
        response = Response(console_js(app.state.console_token),
                            media_type="application/javascript")
        return _set_read_cookie(response, request)

    @app.get(infra_features.HOSPITAL_DEMO_PATH, response_class=HTMLResponse)
    async def app_hospital_demo(request: Request):
        return _set_read_cookie(HTMLResponse(hospital_html()), request)

    @app.get(infra_features.HOSPITAL_DEMO_JS_PATH)
    async def app_hospital_demo_js(request: Request):
        response = Response(hospital_js(app.state.console_token),
                            media_type="application/javascript")
        return _set_read_cookie(response, request)

    @app.get(infra_features.HOSPITAL_STATE_PATH)
    async def app_hospital_state(request: Request):
        _demo_auth(request, allow_query=True)
        return _demo_json(app.state.hospital_demo.state_snapshot(), request)

    @app.post(infra_features.HOSPITAL_START_PATH)
    async def app_hospital_start(request: Request):
        _demo_auth(request, allow_query=False)
        payload = app.state.hospital_demo.start()
        return _demo_json({"contract": infra_features.HOSPITAL_DEMO_CONTRACT,
                          "step": payload["step"], "state": payload["state"]},
                         request)

    @app.post(infra_features.HOSPITAL_STEP_PATH)
    async def app_hospital_step(request: Request):
        _demo_auth(request, allow_query=False)
        entry = app.state.hospital_demo.step()
        return _demo_json({"contract": infra_features.HOSPITAL_DEMO_CONTRACT,
                          "step": entry,
                          "state": app.state.hospital_demo.state_snapshot()},
                         request)

    @app.post(infra_features.HOSPITAL_RESET_PATH)
    async def app_hospital_reset(request: Request):
        _demo_auth(request, allow_query=False)
        state = app.state.hospital_demo.reset()
        return _demo_json({"contract": infra_features.HOSPITAL_DEMO_CONTRACT,
                          "state": state}, request)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="RAKSHA Infra / Sentinel completed service")
    parser.add_argument(
        "--port", type=int,
        default=int(os.environ.get("RAKSHA_INFRA_PORT", "8090")),
    )
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
