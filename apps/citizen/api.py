"""RAKSHA Citizen API — offline-first PWA, MessageGuard and VIGIL host.

    python -m apps.citizen.api --port 8095
    Compatibility: `python -m citizen.api` still resolves through the
    `raksha-code/citizen` package alias.

Endpoints (all same-origin; CORS disabled — the PWA ships with this service):
  GET  /api/citizen/health       -> service, contract and active-model status
  GET  /api/citizen/vigil/status -> mounted VIGIL model and honesty card
  POST /api/citizen/screen_message {text, lang}
  POST /api/citizen/report        {category, severity, lang, note, case_id}
  GET  /vigil/ and /vigil/api/*  -> VIGIL image-privacy engine (same process)
  GET  / and /app/*              -> the PWA (static)

Honesty: message screening uses the measured MessageGuard v1 rule scorer (see
messageguard and the generated root EVALS.md); its accuracy is in-distribution
on 538 hand-authored fixtures, with real-world recall and FPR UNMEASURED.
VIGIL is model-backed image privacy: it modifies pixels and reports local
evaluation metrics. It does not claim deepfake prevention, modern facial
recognition defeat or anonymity. Verdicts are advisory and every screen links
to the 1930 national cybercrime helpline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import uuid
from typing import Any, Callable, Dict, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from . import copy as citizen_copy
from . import features, retention
from .messageguard import score_message
from .phase4_shell import PHASE4_SHELL_JS, honest_manifest, inject_index_html
from .risk import assess as risk_assess
from packages.contracts.canonical import CANONICAL_JSON_RULE
from packages.contracts.envelope import (
    CONTRACT_VERSION as EVENT_CONTRACT_VERSION,
    sign_event as sign_shared_event,
    validate_envelope,
)
from packages.vigil.engines.vigil_core import VIGIL_CORE
from packages.vigil.main import mount_vigil


def _safe_int(value: Any) -> int:
    """int() that never raises. Malformed input becomes 0 (no signal)."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0
    if f != f or f in (float("inf"), float("-inf")):
        return 0
    try:
        return int(f)
    except (ValueError, OverflowError):
        return 0


_HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(_HERE, "app")
_i18n = citizen_copy
VIGIL_ENABLED = features.vigil_enabled()
VIGIL_CARD = features.vigil_card()
CATEGORIES = {"call": "CITIZEN_REPORT_CALL", "message": "CITIZEN_REPORT_MESSAGE",
              "financial": "CITIZEN_REPORT_FINANCIAL", "other": "CITIZEN_REPORT_OTHER"}


def _clamp_severity(value: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def build_app(bus_url: Optional[str] = None,
              poster: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> FastAPI:
    bus_url = (bus_url or os.environ.get("RAKSHA_BUS_URL", "")).rstrip("/")
    app = FastAPI(title="RAKSHA Citizen", version="vigil-integrated")
    state = {"started_at": time.time(), "reports_today": 0}
    app.state.model_backed = features.MODEL_BACKED
    app.state.active_model = features.ACTIVE_MODEL
    app.state.vigil_integrated = VIGIL_ENABLED
    app.state.vigil_route = VIGIL_CARD["route"]
    app.state.vigil_status_path = features.VIGIL_STATUS_PATH

    def _sign_and_forward(event: Dict[str, Any]) -> Dict[str, Any]:
        try:
            signed = sign_shared_event(dict(event))
            validation = validate_envelope(signed, require_signature=True)
            if not validation.actionable:
                return {"forwarded": False,
                        "error": f"signed report is not actionable: {validation.state.value}"}
        except Exception as exc:
            return {"forwarded": False, "error": f"signing unavailable: {exc}"}
        if poster is not None:
            return {"forwarded": True, **poster(signed)}
        if not bus_url:
            return {"forwarded": False, "reason": "RAKSHA_BUS_URL not configured — report stored locally (demo mode)",
                    "event_id": signed.get("event_id")}
        import urllib.request
        req = urllib.request.Request(bus_url + "/api/ingest", data=json.dumps([signed]).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return {"forwarded": True, "bus_reply": json.loads(resp.read().decode())}
        except Exception as exc:
            return {"forwarded": False, "error": str(exc), "event_id": signed.get("event_id")}

    @app.get("/api/citizen/health")
    async def health():
        return {"status": "ok", "engine": "messageguard-rules-v1",
                "bus_configured": bool(bus_url), "reports_today": state["reports_today"],
                "honesty": "advisory, not a security guarantee",
                "phase": features.PHASE,
                "features": dict(features.FEATURE_FLAGS),
                "model_backed": features.MODEL_BACKED,
                "active_model": features.ACTIVE_MODEL,
                "vigil": dict(VIGIL_CARD),
                "vigil_status_path": features.VIGIL_STATUS_PATH,
                "contract": {
                    "event": EVENT_CONTRACT_VERSION,
                    "canonical_json": CANONICAL_JSON_RULE,
                    "citizen_copy": _i18n.CONTRACT_VERSION,
                    "signature_required": True,
                    "governor_required": True,
                }}

    @app.get("/api/citizen/features")
    async def feature_flags():
        return {
            "app": "citizen",
            "phase": features.PHASE,
            "features": dict(features.FEATURE_FLAGS),
            "model_backed": features.MODEL_BACKED,
            "active_model": features.ACTIVE_MODEL,
            "vigil": dict(VIGIL_CARD),
            "vigil_status_path": features.VIGIL_STATUS_PATH,
        }

    @app.get("/api/citizen/capabilities")
    async def capabilities():
        card = features.capability_card()
        card["privacy_tab"] = _i18n.privacy_tab_copy(_i18n.DEFAULT_LANGUAGE)
        return card

    @app.get("/api/citizen/retention")
    async def retention_policy_route():
        return retention.retention_policy()

    @app.get(features.VIGIL_STATUS_PATH)
    async def vigil_status():
        """Citizen-owned backend view of the mounted VIGIL runtime."""
        overview = VIGIL_CORE.get_system_overview()
        return {
            "app": "citizen",
            "model_backed": features.MODEL_BACKED,
            "active_model": features.ACTIVE_MODEL,
            "vigil": dict(VIGIL_CARD),
            "model_status": overview["model_status"],
            "privacy_efficacy": "UNMEASURED",
            "claims_not_made": list(VIGIL_CARD["claims_not_made"]),
        }

    @app.post("/api/citizen/screen_message")
    async def screen_message(payload: Dict[str, Any] = Body(...)):
        text = str(payload.get("text") or "")[:4000]
        lang = _i18n.normalise_language(payload.get("lang"))
        result = score_message(text)
        result["explanation"] = _i18n.explain_message(result, lang)
        result["helpline"] = "1930"
        result["lang"] = lang
        result["disclaimer"] = _i18n.CITIZEN_COPY["disclaimer"][lang]
        return result

    @app.post("/api/citizen/assess")
    async def assess(payload: Dict[str, Any] = Body(default={})):
        lang = _i18n.normalise_language(payload.get("lang"))
        return risk_assess(
            message=payload.get("message"),
            campaign_linked=bool(payload.get("campaign_linked", False)),
            repeat_contacts=_safe_int(payload.get("repeat_contacts")),
            user_doubt=bool(payload.get("user_doubt", False)),
            lang=lang,
        )

    @app.get("/api/citizen/languages")
    async def languages():
        return {"languages": list(_i18n.LANGUAGES),
                "default": _i18n.DEFAULT_LANGUAGE,
                "copy_contract": _i18n.CONTRACT_VERSION}

    @app.post("/api/citizen/report")
    async def report(payload: Dict[str, Any] = Body(...)):
        category = str(payload.get("category") or "").lower()
        if category not in CATEGORIES:
            raise HTTPException(422, f"category must be one of {sorted(CATEGORIES)}")
        severity = _clamp_severity(payload.get("severity"), 0.5)
        lang = str(payload.get("lang") or "en")[:8]
        note = str(payload.get("note") or "")[:200]
        case_id = str(payload.get("case_id") or "").strip()
        if case_id and not re.fullmatch(r"[A-Za-z0-9_]{3,40}", case_id):
            raise HTTPException(422, "case_id must match ^[A-Za-z0-9_]{3,40}$")
        entities = {"case_id": case_id} if case_id else {}
        severity_band = round(severity, 2)
        event = {
            "event_id": f"evt_cit_{uuid.uuid4().hex[:10]}",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ring": "RING_0_CITIZEN",
            "organ": "CITIZEN_APP",
            "signal_type": CATEGORIES[category],
            "severity": severity_band,
            "entities": entities,
            "metrics": {"severity_band": severity_band,
                        "lang_digest": "sha256:" + hashlib.sha256(lang.encode()).hexdigest()[:8]},
        }
        state["reports_today"] += 1
        forward = _sign_and_forward(event)
        payload_out = {"status": "REPORTED", "event_id": event["event_id"],
                       "category": category, "severity": severity_band,
                       "forwarded": forward, "helpline": "1930",
                       "lang": lang}
        payload_out["explanation"] = _i18n.explain_report(
            payload_out, lang, "sent" if forward else "offline")
        payload_out["delivered"] = payload_out["explanation"]["delivered"]
        return payload_out
        # note is accepted for compatibility but is NEVER stored or sent.

    @app.get("/_citizen/phase4.js")
    @app.get("/app/phase4.js")
    async def phase4_shell_js():
        return Response(PHASE4_SHELL_JS, media_type="application/javascript")

    @app.get("/app/")
    @app.get("/app/index.html")
    async def citizen_index():
        return HTMLResponse(inject_index_html(APP_DIR))

    @app.get("/app/manifest.json")
    async def citizen_manifest():
        return JSONResponse(honest_manifest(APP_DIR))

    app.mount("/app", StaticFiles(directory=APP_DIR, html=True), name="app")

    @app.get("/")
    async def root():
        return RedirectResponse(url="/app/", status_code=307)

    mount_vigil(app)
    return app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="RAKSHA Citizen service with VIGIL")
    parser.add_argument(
        "--port", type=int,
        default=int(os.environ.get("RAKSHA_CITIZEN_PORT", "8095")),
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--bus-url", default=os.environ.get("RAKSHA_BUS_URL", ""))
    args = parser.parse_args(argv)
    import uvicorn
    app = build_app(bus_url=args.bus_url)
    uvicorn.run(app, host=args.host, port=args.port)


app = build_app()

if __name__ == "__main__":
    main()
