"""Static frontend serving and same-origin backend-for-frontend gateway."""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from packages.contracts.envelope import ingest_key, sign_event
from packages.governance.safety import EXECUTOR_ID, GOVERNOR_ID, PLANNER_ID

FRONTEND_CONTRACT_VERSION = "raksha-phosphor-frontend-v1"
FRONTEND_STATE_CONTRACT = "raksha-phosphor-state-compat-v1"
VIEW_LABEL = "gateway read-only compatibility view; not a second backend"
FRONTEND_BUILD_DIR = Path(__file__).resolve().parent / "static"
FRONTEND_INDEX = FRONTEND_BUILD_DIR / "index.html"

DEFAULT_CITIZEN_URL = "http://127.0.0.1:8095"
DEFAULT_INFRA_URL = "http://127.0.0.1:8090"
DEFAULT_READ_TOKEN = "demo-observer-token"
DEFAULT_SENSOR_TOKEN = "demo-sensor-token"
DEFAULT_TIMEOUT_SECONDS = 20.0

_FLEET_CONTROL = re.compile(r"^api/fleet/([^/]+)/(halt|resume)$")


def _env(name: str, default: str) -> str:
    return os.environ.get(name) or default


def citizen_url() -> str:
    return _env("RAKSHA_CITIZEN_INTERNAL_URL", DEFAULT_CITIZEN_URL).rstrip("/")


def infra_url() -> str:
    return _env("RAKSHA_INFRA_INTERNAL_URL", DEFAULT_INFRA_URL).rstrip("/")


def read_token() -> str:
    """The token the console reads with: frontend-specific, else the app's own.

    ``packages/spine.runtime`` registers its observer record from
    ``RAKSHA_OBSERVER_TOKEN``, so falling back to the same variable keeps a
    single-environment deployment working; the dedicated variable only exists
    to give the console a narrower token.
    """
    return (_env("RAKSHA_FRONTEND_READ_TOKEN", "") or _env("RAKSHA_OBSERVER_TOKEN", "")
            or DEFAULT_READ_TOKEN)


def sensor_token() -> str:
    """Ingest token, resolved the same way as the app's sensor record."""
    return (_env("RAKSHA_FRONTEND_SENSOR_TOKEN", "") or _env("RAKSHA_SENSOR_TOKEN", "")
            or DEFAULT_SENSOR_TOKEN)


def sensor_key() -> bytes:
    """The key the shared runtime verifies ingest with — resolved once, in the contract."""
    return ingest_key()


def infra_detectors_path() -> str:
    """The Infra detector-card route, kept in one place for the compat views."""
    return _env("RAKSHA_INFRA_DETECTORS_PATH", "/api/infra/detectors")


def _target_url(base: str, sub_path: str, query: str = "") -> str:
    path = "/" + sub_path.lstrip("/")
    return f"{base}{path}" + (f"?{query}" if query else "")


def _json(data: Any, *, status: int = 200, target: str) -> JSONResponse:
    return JSONResponse(
        data,
        status_code=status,
        headers={"Cache-Control": "no-store", "X-Gateway-Target": target},
    )


def _error(target: str, message: str, detail: str, *, status: int = 502) -> JSONResponse:
    return _json(
        {"ok": False, "status": status, "error": message, "detail": detail[:400]},
        status=status,
        target=target,
    )


def _passthrough(res: httpx.Response, target: str) -> Response:
    content_type = res.headers.get("content-type", "application/json")
    return Response(
        content=res.content,
        status_code=res.status_code,
        media_type=content_type,
        headers={"Cache-Control": "no-store", "X-Gateway-Target": target},
    )


def _request_headers(request: Request, *, token: str | None, content_type: str | None = None) -> dict[str, str]:
    headers = {"Accept": request.headers.get("accept", "application/json")}
    if token:
        headers["X-API-Token"] = token
    header_content_type = content_type or request.headers.get("content-type")
    if header_content_type:
        headers["Content-Type"] = header_content_type
    elif request.method in {"POST", "PUT", "PATCH"}:
        headers["Content-Type"] = "application/json"
    return headers


async def _infra_json(client: httpx.AsyncClient, path: str, *, token: str) -> dict[str, Any]:
    res = await client.get(
        _target_url(infra_url(), path),
        headers={"Accept": "application/json", "X-API-Token": token},
    )
    if not 200 <= res.status_code < 300:
        raise RuntimeError(f"Infra endpoint {path} returned {res.status_code}: {res.text[:200]}")
    payload = res.json()
    return payload if isinstance(payload, dict) else {"items": payload}


def _timeline_events(
    timeline: list[dict[str, Any]],
    detections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Project the runtime timeline into the rows the console feed renders.

    The runtime timeline carries no wall-clock stamp (it is a deterministic
    step counter) and it does not repeat the organ, so the organ and severity
    are joined in from the sealed detection records rather than guessed from
    the free-text detail.
    """
    by_ref = {str(item.get("event_id") or ""): item for item in detections}
    events: list[dict[str, Any]] = []
    for entry in timeline[-60:]:
        stage = str(entry.get("stage") or "event")
        ref = str(entry.get("ref") or "")
        sealed = by_ref.get(ref) or {}
        events.append({
            "event_id": ref,
            "organ": str(sealed.get("organ") or ""),
            "signal_type": str(entry.get("kind") or stage),
            "severity": sealed.get("severity"),
            "verified": stage != "quarantine",
            "step": entry.get("step"),
            "ledger_seq": entry.get("ledger_seq"),
            "stage": stage,
            "detail": str(entry.get("detail") or ""),
        })
    return events


def _state_view(
    raw: dict[str, Any],
    decisions: list[dict[str, Any]] | None = None,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    timeline = [dict(item) for item in (raw.get("timeline") or []) if isinstance(item, dict)]
    detections = [dict(item) for item in (raw.get("detections") or []) if isinstance(item, dict)]
    campaigns = []
    for item in raw.get("campaigns") or []:
        if not isinstance(item, dict):
            continue
        campaigns.append({
            "campaign_id": item.get("campaign_id") or "",
            "case_id": item.get("case_id") or "",
            # the runtime scores a campaign as 10 points per sealed detection
            "size": item.get("detections") or 0,
            "risk_score": item.get("risk_score") or 0,
            "severity_max": round(float(item.get("risk_score") or 0) / 10.0, 2),
            "entities": item.get("entities") or [],
            "fused": bool(item.get("fused")),
        })
    recent_events = _timeline_events(timeline, detections)
    for detection in detections[-60:]:
        recent_events.append({
            "event_id": str(detection.get("event_id") or ""),
            "organ": str(detection.get("organ") or ""),
            "signal_type": str(detection.get("rule_id") or "detection"),
            "severity": detection.get("severity") or 0,
            "verified": True,
            "timestamp_utc": str(detection.get("ts") or ""),
            "kind": "detection",
        })
    topology = raw.get("topology") if isinstance(raw.get("topology"), dict) else {}
    nodes = topology.get("nodes") or topology.get("hosts") or []
    edges = topology.get("edges") or []
    counters = (metrics or {}).get("counters") if isinstance(metrics, dict) else {}
    counters = counters if isinstance(counters, dict) else {}
    quarantine_count = int(raw.get("quarantine_count") or 0)
    organs_observed = sorted({
        str(item.get("organ")) for item in detections if item.get("organ")
    })
    return {
        "app": "infra",
        "status": raw.get("status") or "ok",
        "contract": FRONTEND_STATE_CONTRACT,
        "view": VIEW_LABEL,
        "sources": ["/v1/state", "/v1/decisions", "/v1/metrics"],
        "dry_run": bool(raw.get("dry_run", True)),
        "deterministic": bool(raw.get("deterministic", True)),
        "model_backed": bool(raw.get("model_backed", False)),
        "commander": raw.get("commander") or {"enabled": False, "mode": "disabled"},
        "executor_mode": "dry-run",
        "buffered_events": len(timeline),
        "decision_count": len(decisions or []),
        "campaigns": campaigns,
        "recent_events": recent_events[-60:],
        "timeline": timeline,
        "detections": detections,
        "organs_observed": organs_observed,
        "quarantine_count": quarantine_count,
        "ledger_height": raw.get("ledger_height") or 0,
        "fortress": {
            "telemetry_mac": True,
            "unverified_held": quarantine_count,
            "replay_dropped": int(counters.get("ingest.duplicate") or 0),
            "rate_limited": int(counters.get("ingest.rate_limited") or 0),
            "quarantine_states": {
                key.split(".", 2)[-1]: int(value)
                for key, value in counters.items()
                if key.startswith("ingest.quarantine.")
            },
        },
        "entity_graph": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "window_sec": 600,
            "window_note": "topology snapshot; 600s is the console label, not a sliding window",
        },
        "governor": {
            "planner": PLANNER_ID,
            "governor_id": GOVERNOR_ID,
            "executor_id": EXECUTOR_ID,
            "decisions_allowed": int(counters.get("decide.allowed") or 0),
            "decisions_refused": int(counters.get("decide.refused") or 0),
            "executor_simulated": int(counters.get("executor.simulated") or 0),
            "executor_skipped_refusal": int(counters.get("executor.skipped_refusal") or 0),
            "live_action_paths": 0,
            "admin_override": "refused with 403 by the runtime",
            "commander_model_invoked": False,
        },
        "last_containment": (decisions or [])[-1] if decisions else None,
        "last_plan": next(
            (item for item in reversed(timeline) if item.get("stage") == "proposal"),
            None,
        ),
    }


def _health_view(raw: dict[str, Any]) -> dict[str, Any]:
    """Project the runtime health card without adding claims it does not make."""
    commander = raw.get("commander") if isinstance(raw.get("commander"), dict) else {}
    return {
        "status": raw.get("status") or "ok",
        "version": raw.get("version"),
        "contract": raw.get("contract"),
        "view": VIEW_LABEL,
        "dry_run": bool(raw.get("dry_run", True)),
        "deterministic": bool(raw.get("deterministic", True)),
        "model_backed": bool(raw.get("model_backed", False)),
        "executor_mode": "dry-run",
        "commander_enabled": bool(commander.get("enabled", False)),
        "commander_mode": str(commander.get("mode") or "disabled"),
        "rings_3_4": "deterministic detector organs cover rings 3 and 4; no live fabric control exists",
    }


async def _state_compat(client: httpx.AsyncClient) -> dict[str, Any]:
    token = read_token()
    raw = await _infra_json(client, "/v1/state", token=token)
    decisions: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    try:
        result = await _infra_json(client, "/v1/decisions", token=token)
        decisions = [dict(item) for item in (result.get("decisions") or []) if isinstance(item, dict)]
    except Exception:
        decisions = []
    try:
        metrics = await _infra_json(client, "/v1/metrics", token=token)
    except Exception:
        metrics = {}
    return _state_view(raw, decisions, metrics)


async def _orchestrate_compat(client: httpx.AsyncClient) -> dict[str, Any]:
    """Read-only orchestration view over the deterministic runtime.

    The runtime's own ``/api/orchestrate`` route answers with the campaign
    snapshot. The console also has to explain *why* nothing was executed, so
    this view reads the same sealed state (timeline, quarantine, decisions) and
    reports it. It never runs a model and never performs a containment action.
    """
    token = read_token()
    raw = await _infra_json(client, "/v1/state", token=token)
    timeline = [dict(item) for item in (raw.get("timeline") or []) if isinstance(item, dict)]
    quarantine_count = int(raw.get("quarantine_count") or 0)
    last = timeline[-1] if timeline else {}
    last_is_held = str(last.get("stage") or "") == "quarantine"
    if not timeline and quarantine_count == 0:
        status = "NO_EVENTS"
        reason = "no signed telemetry has been ingested in this runtime"
    elif last_is_held:
        status = "HELD_UNVERIFIED_EVIDENCE"
        reason = (
            f"the last event was quarantined ({last.get('kind')}) before detection, "
            "so it cannot steer a decision"
        )
    elif quarantine_count:
        status = "PARTIAL_HOLD"
        reason = (
            f"{quarantine_count} event(s) are quarantined and excluded from fusion; "
            "the remaining signed evidence was decided normally"
        )
    else:
        status = "DETERMINISTIC_SNAPSHOT"
        reason = "sealed proposals and Governor decisions are exposed without a Commander call"
    decisions: list[dict[str, Any]] = []
    campaigns: list[dict[str, Any]] = []
    try:
        result = await _infra_json(client, "/v1/decisions", token=token)
        decisions = [dict(item) for item in (result.get("decisions") or []) if isinstance(item, dict)]
    except Exception:
        decisions = []
    try:
        result = await _infra_json(client, "/v1/campaigns", token=token)
        campaigns = [dict(item) for item in (result.get("campaigns") or []) if isinstance(item, dict)]
    except Exception:
        campaigns = []
    return {
        "status": status,
        "reason": reason,
        "view": VIEW_LABEL,
        "sources": ["/v1/state", "/v1/decisions", "/v1/campaigns"],
        "commander_mode": str((raw.get("commander") or {}).get("mode")
                              if isinstance(raw.get("commander"), dict) else "" ) or "disabled",
        "brief": (
            f"{PLANNER_ID} proposals ruled by {GOVERNOR_ID}; {EXECUTOR_ID} simulates only. "
            "No model inference and no live containment action is wired."
        ),
        "unverified_events": quarantine_count,
        "ledger_height": raw.get("ledger_height") or 0,
        "campaigns": campaigns,
        "actions": [
            {
                "tool": str(item.get("kind") or "proposal"),
                "proposal_id": str(item.get("ref") or ""),
                "rationale": str(item.get("detail") or ""),
                "ledger_seq": item.get("ledger_seq"),
            }
            for item in timeline
            if item.get("stage") == "proposal"
        ][-20:],
        "decisions": [
            {
                "tool": str(item.get("ref") or "governor"),
                "decision": str(item.get("verdict") or item.get("kind") or ""),
                "reason": str(item.get("text") or ""),
                "dry_run": bool(item.get("dry_run", True)),
            }
            for item in decisions
        ][-20:],
        "results": [
            {
                "tool": str(item.get("kind") or "dry-run-executor"),
                "result": {"status": "dry_run_only", "detail": item.get("detail") or ""},
            }
            for item in timeline
            if item.get("stage") == "execution"
        ][-20:],
    }


def _containment_compat_view(
    state: dict[str, Any],
    decisions: list[dict[str, Any]],
    detectors: dict[str, Any],
) -> dict[str, Any]:
    """Describe the sealed containment plan the runtime already produced."""
    timeline = [dict(item) for item in (state.get("timeline") or []) if isinstance(item, dict)]
    detections = [dict(item) for item in (state.get("detections") or []) if isinstance(item, dict)]
    plan = next((item for item in reversed(timeline) if item.get("stage") == "proposal"), {})
    last = decisions[-1] if decisions else {}
    verdict = str(last.get("verdict") or "NO_DECISION")
    return {
        "status": "DRY_RUN_SNAPSHOT",
        "view": VIEW_LABEL,
        "sources": ["/v1/state", "/v1/decisions", "/api/infra/detectors"],
        "brief": (
            "The planner, Governor and dry-run executor are the wired active path; this view "
            "reports their sealed output and does not propose a new live action."
        ),
        "plan_source": PLANNER_ID,
        "governor_id": GOVERNOR_ID,
        "executor_id": EXECUTOR_ID,
        "containment": {
            "plan_id": str(plan.get("ref") or last.get("ref") or "none"),
            "status": "PLAN_SEALED" if plan else "NO_PLAN_YET",
            "action": str(plan.get("kind") or ""),
            "reason": str(plan.get("detail") or last.get("text") or ""),
            "ledger_seq": plan.get("ledger_seq"),
            "detections_in_window": len(detections),
            "organs_observed": state.get("organs_observed") or [],
        },
        "governor": {
            "decision": verdict,
            "reason": str(last.get("text") or "no sealed decision in this runtime window"),
            "allowed": int((state.get("governor") or {}).get("decisions_allowed") or 0),
            "refused": int((state.get("governor") or {}).get("decisions_refused") or 0),
        },
        "registry": {
            "organ_count": detectors.get("organ_count"),
            "rules": sum(len(item.get("rule_ids") or [])
                         for item in detectors.get("organ_details") or [] if isinstance(item, dict)),
        },
        "executor_result": {
            "status": "dry_run_only",
            "simulated": int((state.get("governor") or {}).get("executor_simulated") or 0),
            "real_action_count": 0,
            "commander_model_invoked": False,
        },
    }


async def _containment_compat(client: httpx.AsyncClient) -> dict[str, Any]:
    token = read_token()
    state = await _state_compat(client)
    decisions: list[dict[str, Any]] = []
    detectors: dict[str, Any] = {}
    try:
        result = await _infra_json(client, "/v1/decisions", token=token)
        decisions = [dict(item) for item in (result.get("decisions") or []) if isinstance(item, dict)]
    except Exception:
        decisions = []
    try:
        detectors = await _infra_json(client, infra_detectors_path(), token=token)
    except Exception:
        detectors = {}
    return _containment_compat_view(state, decisions, detectors)


async def _fleet_compat(client: httpx.AsyncClient, *, canary: bool = False) -> dict[str, Any]:
    """Per-organ view built only from the registry and the live runtime state.

    Infra runs one deterministic detector registry — there is no supervisor, so
    there is no process health, call count or error count to report. Each organ
    is therefore labelled by what the runtime actually saw: findings, held
    events, or nothing in this window.
    """
    token = read_token()
    detectors = await _infra_json(client, infra_detectors_path(), token=token)
    state = await _state_compat(client)
    details = [dict(item) for item in (detectors.get("organ_details") or []) if isinstance(item, dict)]
    detections = [dict(item) for item in (state.get("detections") or []) if isinstance(item, dict)]
    try:
        held = await _infra_json(client, "/v1/quarantine", token=token)
        held_items = [dict(item) for item in (held.get("items") or []) if isinstance(item, dict)]
    except Exception:
        held_items = []
    organs: dict[str, Any] = {}
    canary_results: dict[str, Any] = {}
    counts = {"OBSERVED": 0, "QUIET": 0, "HELD_ONLY": 0}
    unobserved: list[str] = []
    for item in details:
        name = str(item.get("name") or "unknown-organ")
        fired = [d for d in detections if str(d.get("organ") or "") == name]
        held_for_organ = [h for h in held_items if str(h.get("organ") or "").lower() == name]
        if fired:
            state_label = "OBSERVED"
        elif held_for_organ:
            state_label = "HELD_ONLY"
        else:
            state_label = "QUIET"
            unobserved.append(name)
        counts[state_label] += 1
        rule_ids = [str(r) for r in (item.get("rule_ids") or [])]
        organs[name] = {
            "state": state_label,
            "ring": str(item.get("ring") or "RING_UNSET"),
            "rules": len(rule_ids),
            "rule_ids": rule_ids,
            "detections": len(fired),
            "held": len(held_for_organ),
            "last_event": (fired[-1].get("ts") if fired else None) or None,
            "note": (
                f"last rule hit: {fired[-1].get('rule_id')}" if fired
                else "no signed event for this organ in the runtime window"
            ),
        }
        canary_results[name] = {
            "verdict": "RULES_REGISTERED" if rule_ids else "NO_RULES",
            "detail": (
                f"{len(rule_ids)} deterministic rule(s); fixtures "
                f"{', '.join(item.get('fixtures') or []) or 'none'} — no canary runner exists "
                "in this build, so no synthetic probe is claimed"
            ),
        }
    return {
        "available": True,
        "contract": "raksha-phosphor-fleet-compat-v1",
        "view": VIEW_LABEL,
        "sources": ["/api/infra/detectors", "/v1/state", "/v1/quarantine"],
        "executor_mode": "dry-run",
        "live_control": False,
        "organs": organs,
        "counts": counts,
        "total": len(organs),
        "halted": [],
        "silent": unobserved,
        "unobserved": unobserved,
        "canary": {
            "available": True,
            "ran": False,
            "reason": (
                "no canary runner is wired in this build; the registry and its fixtures are "
                "exercised by the repository test gates"
                if canary else "not requested"
            ),
            "results": canary_results if canary else {},
        },
    }


async def _ingest_batch(
    client: httpx.AsyncClient,
    events: list[dict[str, Any]],
    *,
    should_sign: bool,
    target: str,
) -> JSONResponse:
    results: list[dict[str, Any]] = []
    for event in events:
        try:
            payload = sign_event(dict(event), key=sensor_key()) if should_sign else dict(event)
        except Exception as exc:
            return _error(target, "event signing failed", f"{type(exc).__name__}: {exc}", status=400)
        try:
            res = await client.post(
                _target_url(infra_url(), "/api/ingest"),
                content=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-API-Token": sensor_token(),
                },
            )
            body = res.json() if res.content else {}
            if not isinstance(body, dict):
                body = {"raw": body}
            results.append({"status": res.status_code, "body": body})
        except Exception as exc:
            return _error(target, "spine ingest unreachable", f"{type(exc).__name__}: {exc}")
    accepted = sum(
        1 for item in results
        if 200 <= item["status"] < 300 and bool(item["body"].get("accepted"))
    )
    unverified = sum(
        1 for item in results
        if 200 <= item["status"] < 300 and bool(item["body"].get("quarantined"))
    )
    return _json(
        {
            "accepted": accepted,
            "received": len(events),
            "unverified": unverified,
            "results": results,
        },
        target=target,
    )


async def _screen_transcript(request: Request, client: httpx.AsyncClient) -> JSONResponse:
    try:
        payload = await request.json()
    except Exception:
        return _error("citizen-transcript", "invalid JSON body", "body must be a JSON object", status=400)
    if not isinstance(payload, dict):
        return _error("citizen-transcript", "invalid JSON body", "body must be a JSON object", status=400)
    text = str(payload.get("text") or "")[:4000]
    lang = str(payload.get("lang") or "en")[:8]
    try:
        res = await client.post(
            _target_url(citizen_url(), "/api/citizen/screen_message"),
            content=json.dumps({"text": text, "lang": lang}, separators=(",", ":")).encode("utf-8"),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        data = res.json() if res.content else {}
        if not isinstance(data, dict):
            data = {}
    except Exception as exc:
        return _error("citizen-transcript", "Citizen service unreachable", f"{type(exc).__name__}: {exc}")
    if not 200 <= res.status_code < 300:
        return _json(data if data else {"detail": res.text[:400]}, status=res.status_code, target="citizen-transcript")
    explanation = data.get("explanation") if isinstance(data.get("explanation"), dict) else {}
    return _json(
        {
            "verdict": str(data.get("verdict") or "LOW"),
            "score": data.get("score"),
            "legacy_band": data.get("legacy_band"),
            "engine": data.get("engine") or "messageguard",
            "view": "transcript alias of POST /api/citizen/screen_message",
            "reasons": data.get("reasons") or [],
            "reason_codes": data.get("reason_codes") or [],
            "families_hit": data.get("families_hit") or [],
            "features": {"transcript_characters": len(text),
                         "families_hit": len(data.get("families_hit") or [])},
            "explanation": {
                "title": explanation.get("title") or "Transcript screen result",
                "action": explanation.get("action") or "If in doubt, hang up and call 1930.",
                "reasons": explanation.get("reasons") or data.get("reasons") or [],
                "disclaimer": explanation.get("disclaimer") or data.get("disclaimer") or "",
            },
            "helpline": data.get("helpline") or "1930",
            "lang": data.get("lang") or lang,
            "disclaimer": "Transcript-only Citizen rule screen. No recording is made and no synthetic-speech claim is made.",
        },
        target="citizen-transcript",
    )


async def _proxy(
    request: Request,
    client: httpx.AsyncClient,
    *,
    base: str,
    sub_path: str,
    target: str,
    token: str | None,
) -> Response:
    body = await request.body() if request.method in {"POST", "PUT", "PATCH", "DELETE"} else None
    headers = _request_headers(request, token=token)
    try:
        res = await client.request(
            request.method,
            _target_url(base, sub_path, request.url.query),
            content=body,
            headers=headers,
        )
        return _passthrough(res, target)
    except httpx.RequestError as exc:
        return _error(target, f"{target} service unreachable", f"{type(exc).__name__}: {exc}")
    except Exception as exc:
        return _error(target, f"{target} gateway failure", f"{type(exc).__name__}: {exc}")


async def _probe(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    try:
        res = await client.get(url, headers={"Accept": "application/json"})
        try:
            info = res.json() if res.content else None
        except Exception:
            info = {"raw": res.text[:200]}
        return {"ok": 200 <= res.status_code < 300, "info": info}
    except Exception as exc:
        return {"ok": False, "detail": f"{type(exc).__name__}: {exc}", "info": None}


async def _gateway_handler(request: Request, gateway_path: str) -> Response:
    gateway_path = gateway_path.strip("/")
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS, follow_redirects=False) as client:
        try:
            if gateway_path == "status" and request.method == "GET":
                citizen, spine = await asyncio.gather(
                    _probe(client, _target_url(citizen_url(), "/api/citizen/health")),
                    _probe(client, _target_url(infra_url(), "/api/health")),
                )
                return _json({"citizen": citizen, "spine": spine}, target="status")

            if gateway_path == "spine-signed" and request.method == "POST":
                try:
                    parsed = await request.json()
                except Exception:
                    return _error("spine-signed", "invalid JSON body", "body must be a JSON event or array", status=400)
                events = parsed if isinstance(parsed, list) else [parsed]
                if not all(isinstance(item, dict) for item in events):
                    return _error("spine-signed", "invalid event batch", "every item must be a JSON object", status=400)
                return await _ingest_batch(client, events, should_sign=True, target="spine-signed")

            if gateway_path.startswith("citizen/"):
                sub_path = gateway_path[len("citizen/"):]
                if sub_path == "api/citizen/screen_transcript" and request.method == "POST":
                    return await _screen_transcript(request, client)
                return await _proxy(
                    request, client, base=citizen_url(), sub_path=sub_path,
                    target="citizen", token=None,
                )

            if gateway_path.startswith("spine/"):
                sub_path = gateway_path[len("spine/"):]
                if sub_path == "api/health" and request.method == "GET":
                    raw = await _infra_json(client, "/api/health", token=read_token())
                    return _json(_health_view(raw), target="spine-health")
                if sub_path == "api/state" and request.method == "GET":
                    return _json(await _state_compat(client), target="spine-state")
                if sub_path == "api/orchestrate":
                    return _json(await _orchestrate_compat(client), target="spine-orchestrate")
                if sub_path == "api/containment":
                    return _json(await _containment_compat(client), target="spine-containment")
                if sub_path == "api/fleet" and request.method == "GET":
                    return _json(await _fleet_compat(client), target="spine-fleet")
                if sub_path == "api/fleet/canary" and request.method == "GET":
                    return _json(await _fleet_compat(client, canary=True), target="spine-fleet-canary")
                control = _FLEET_CONTROL.match(sub_path)
                if control and request.method == "POST":
                    organ, action = control.group(1), control.group(2)
                    return _json(
                        {
                            "status": "DRY_RUN_ONLY",
                            "reason": "Live organ control is disabled; use signed telemetry and the deterministic Governor path.",
                            "organ": organ,
                            "requested_action": action,
                            "real_action_count": 0,
                        },
                        target="spine-fleet-control",
                    )
                if sub_path == "api/ingest" and request.method == "POST":
                    try:
                        parsed = await request.json()
                    except Exception:
                        return _error("spine-ingest", "invalid JSON body", "body must be a JSON event or array", status=400)
                    events = parsed if isinstance(parsed, list) else [parsed]
                    if not all(isinstance(item, dict) for item in events):
                        return _error("spine-ingest", "invalid event batch", "every item must be a JSON object", status=400)
                    return await _ingest_batch(client, events, should_sign=False, target="spine-ingest")
                token = sensor_token() if sub_path == "api/ingest" and request.method == "POST" else read_token()
                return await _proxy(
                    request, client, base=infra_url(), sub_path=sub_path,
                    target="spine", token=token,
                )

            return _json(
                {"error": "unknown gateway path", "path": gateway_path},
                status=404,
                target="unknown",
            )
        except RuntimeError as exc:
            return _error("gateway", "backend compatibility view failed", str(exc))
        except Exception as exc:
            return _error("gateway", "gateway failure", f"{type(exc).__name__}: {exc}")


def register_frontend(app: FastAPI, *, service: str, root_redirect: str) -> None:
    """Attach the static frontend and gateway to one of the two active apps."""
    if getattr(app.state, "frontend_registered", False):
        return
    app.state.frontend_registered = True
    app.state.frontend_contract = FRONTEND_CONTRACT_VERSION
    app.state.frontend_service = service
    app.state.frontend_root_redirect = root_redirect

    @app.get("/api/frontend/health")
    async def frontend_health() -> dict[str, Any]:
        return {
            "contract": FRONTEND_CONTRACT_VERSION,
            "service": service,
            "static_build": FRONTEND_INDEX.is_file(),
            "gateway": True,
            "root_redirect": root_redirect,
            "citizen_configured": bool(citizen_url()),
            "infra_configured": bool(infra_url()),
        }

    @app.api_route(
        "/api/gateway/{gateway_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    )
    async def frontend_gateway(request: Request, gateway_path: str) -> Response:
        return await _gateway_handler(request, gateway_path)

    @app.get("/{asset_path:path}")
    async def frontend_asset(asset_path: str) -> Response:
        if asset_path.startswith("api/"):
            return _json({"detail": "Not Found"}, status=404, target="frontend")
        if not FRONTEND_INDEX.is_file():
            return _json(
                {"error": "static frontend build missing", "detail": str(FRONTEND_INDEX)},
                status=503,
                target="frontend",
            )
        build_root = FRONTEND_BUILD_DIR.resolve()
        candidate = (build_root / asset_path).resolve()
        if candidate.is_dir():
            # trailingSlash: true means /console/rings/ is a directory whose
            # prerendered document is index.html — resolve it so a deep link
            # serves that route's HTML instead of the shell fallback
            candidate = candidate / "index.html"
        if candidate.is_relative_to(build_root) and candidate.is_file():
            return FileResponse(candidate, headers={"Cache-Control": "no-store"})
        return FileResponse(FRONTEND_INDEX, headers={"Cache-Control": "no-store"})


__all__ = [
    "FRONTEND_BUILD_DIR",
    "FRONTEND_CONTRACT_VERSION",
    "citizen_url",
    "infra_url",
    "register_frontend",
]
