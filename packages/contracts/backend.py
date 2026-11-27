"""Phase 3 — one backend contract mapping for legacy and enterprise surfaces."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable

BACKEND_CONTRACT_VERSION = "raksha-backend-v1"


@dataclass(frozen=True)
class BackendRoute:
    canonical: str
    spine_v2: str | None
    enterprise_i1: str | None
    methods: tuple[str, ...]
    auth_scope: str | None
    purpose: str


BACKEND_ROUTES: tuple[BackendRoute, ...] = (
    BackendRoute("health", "/api/health", "/healthz", ("GET",), None, "liveness"),
    BackendRoute("ingest", "/api/ingest", "/v1/telemetry", ("POST",), "telemetry:write", "signed telemetry ingest"),
    BackendRoute("state", "/api/state", "/v1/state", ("GET",), "read", "state and campaign snapshot"),
    BackendRoute("orchestrate", "/api/orchestrate", "/v1/campaigns", ("POST", "GET"), "read", "campaign/decision surface"),
    BackendRoute("ledger_verify", None, "/v1/ledger/verify", ("GET",), "read", "append-only chain verification"),
    BackendRoute("websocket", "/ws/telemetry", "/v1/telemetry/stream", ("WS",), "read", "verified event stream"),
    BackendRoute("decisions", None, "/v1/decisions", ("GET",), "read", "Governor decisions incl. refusals"),
)

PROFILE_PATHS = {
    "spine-v2": tuple(r.spine_v2 for r in BACKEND_ROUTES if r.spine_v2),
    "enterprise-i1": tuple(r.enterprise_i1 for r in BACKEND_ROUTES if r.enterprise_i1),
}


def contract_card() -> dict[str, Any]:
    return {
        "contract": BACKEND_CONTRACT_VERSION,
        "profiles": sorted(PROFILE_PATHS),
        "routes": [asdict(r) for r in BACKEND_ROUTES],
        "signature_required": True,
        "governor_required": True,
        "append_only_ledger": True,
    }


def validate_routes(app: Any, profile: str) -> dict[str, Any]:
    """Duck-typed FastAPI/Starlette route check; no framework import needed."""
    if profile not in PROFILE_PATHS:
        return {"ok": False, "profile": profile, "missing": [], "reason": "unknown backend profile"}
    actual = {getattr(route, "path", None) for route in getattr(app, "routes", [])}
    expected = set(PROFILE_PATHS[profile])
    missing = sorted(expected - actual)
    return {"ok": not missing, "profile": profile, "missing": missing, "checked": sorted(expected)}


__all__ = [
    "BACKEND_CONTRACT_VERSION", "BackendRoute", "BACKEND_ROUTES", "PROFILE_PATHS",
    "contract_card", "validate_routes",
]
