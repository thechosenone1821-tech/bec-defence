"""RAKSHA Citizen API — offline-first citizen defence service + PWA host.

    python -m apps.citizen.api --port 8095
    Compatibility: `python -m citizen.api` still resolves through the
    `raksha-code/citizen` package alias. VoiceGuard/MAYA files are untouched.

Endpoints (all same-origin; CORS disabled — the PWA ships with this service):
  GET  /api/citizen/health      -> {"status":"ok", "engine": ...}
  POST /api/citizen/screen_message {"text": "...", "lang": "en|hi|te|auto"}
  POST /api/citizen/screen_voice   {"samples": [float, ...]}  (<= 240k samples)
  POST /api/citizen/report         {"category":"voice|message|financial|other",
                                    "severity":0..1, "lang":"en|hi|te", "note":"<=200 chars"}
                                  forwards a SIGNED, tokenized event to the spine bus.
                                  Raw content is NEVER forwarded — only category,
                                  severity band, language and opaque tokens.
  GET  / and /app/*              -> the PWA (static)

Honesty: message screening uses the measured MessageGuard v1 rule scorer (see
messageguard and the generated root EVALS.md); its accuracy is in-distribution
on 538 hand-authored fixtures, with real-world recall and FPR UNMEASURED.
VoiceGuard /
MAYA is **not integrated yet**: the voice tab says so, no audio is scored, no
AI model is run, and no clone-detection claim is made. Verdicts are advisory and
every screen links to the 1930 national cybercrime helpline.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
import uuid
from typing import Any, Callable, Dict, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from . import copy as citizen_copy
from . import features
from .retention import (MAX_SCREEN_SAMPLES, retention_policy,
                        screen_with_consent)
from .messageguard import score_message
from .phase4_shell import (PHASE4_SHELL_JS, honest_manifest,
                           inject_index_html)
from .risk import assess as risk_assess
from .voiceguard_interface import VOICEGUARD, VOICEGUARD_INTERFACE_CARD
from packages.contracts.canonical import CANONICAL_JSON_RULE
from packages.contracts.envelope import (
    CONTRACT_VERSION as EVENT_CONTRACT_VERSION,
    sign_event as sign_shared_event,
    validate_envelope,
)

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

# Phase 4: the frozen capture contract still owns the retention ceiling, but no
# sample is scored because VoiceGuard is behind a hard-disabled feature flag.
MAX_SAMPLES = MAX_SCREEN_SAMPLES
_i18n = citizen_copy
VOICEGUARD_ENABLED = features.voiceguard_enabled()


def score_voice(samples):
    """Compatibility attribute only; Phase 4 must never invoke a model.

    Legacy tests monkeypatch this name to prove no consent means no scoring.
    The real active path returns a disabled response before reaching here.
    """
    raise RuntimeError("VoiceGuard is disabled in Phase 4; no AI model may run")
CATEGORIES = {"voice": "CITIZEN_REPORT_VOICE", "message": "CITIZEN_REPORT_MESSAGE",
              "financial": "CITIZEN_REPORT_FINANCIAL", "other": "CITIZEN_REPORT_OTHER"}


def _clamp_severity(value: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def build_app(bus_url: Optional[str] = None, poster: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> FastAPI:
    bus_url = (bus_url or os.environ.get("RAKSHA_BUS_URL", "")).rstrip("/")
    app = FastAPI(title="RAKSHA Citizen", version="0.4.0-phase4")
    state = {"started_at": time.time(), "reports_today": 0}

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
                "honesty": "heuristic detectors — not a security guarantee",
                "phase": features.PHASE,
                "features": dict(features.FEATURE_FLAGS),
                "no_ai_models": features.NO_AI_MODELS,
                "voiceguard": VOICEGUARD.status(),
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
            "voiceguard": VOICEGUARD.status(),
            "voiceguard_interface": VOICEGUARD_INTERFACE_CARD,
            "no_ai_models": features.NO_AI_MODELS,
        }

    @app.get("/api/citizen/capabilities")
    async def capabilities():
        card = features.capability_card()
        card["voice_tab"] = _i18n.voice_tab_copy(_i18n.DEFAULT_LANGUAGE)
        return card

    @app.get("/api/citizen/retention")
    async def retention():
        """The retention contract this build actually enforces."""
        return retention_policy()

    @app.post("/api/citizen/screen_message")
    async def screen_message(payload: Dict[str, Any] = Body(...)):
        text = str(payload.get("text") or "")[:4000]
        # BUG-2 (fixed in Phase 4): `lang` used to be accepted and ignored.
        # It now selects the explanation language, and is echoed back so a
        # caller can tell whether a fallback occurred.
        lang = _i18n.normalise_language(payload.get("lang"))
        # Detection stays language-agnostic: `lang` selects citizen copy, not
        # the script a scam message may be written in. The v1 scorer applies
        # en/hi/te token sets and language-agnostic link tokens together.
        result = score_message(text)
        # Part 1 Phase 1: the tab used to print "Score 0.65 · credential,
        # urgency", which violates the spine's own rule that a citizen never
        # sees a raw score. `explanation` is what the UI renders; `score` and
        # `hits` stay in the payload for diagnostics only.
        result["explanation"] = _i18n.explain_message(result, lang)
        result["helpline"] = "1930"
        result["lang"] = lang
        result["disclaimer"] = _i18n.CITIZEN_COPY["disclaimer"][lang]
        return result

    @app.post("/api/citizen/screen_voice")
    async def screen_voice(payload: Dict[str, Any] = Body(...)):
        # Part Three, task 3.1. /retention has always advertised
        # "consent_required": true while this endpoint never checked it, so the
        # guarantee lived only in a class that nothing outside the tests
        # constructed. Consent is now required here, where the audio actually
        # arrives, and the refusal is a 403 carrying citizen copy rather than a
        # bare error string — a client should be able to *show* the refusal.
        gate = screen_with_consent(payload.get("samples"), payload.get("consent"),
                                   lang=payload.get("lang"))
        if not gate["accepted"]:
            # Keep the HTTP meaning of each refusal: no consent is a 403, a
            # missing body is a 422, an oversized window is a 413. Collapsing
            # every refusal to one code would make the client guess *why*, which
            # is the thing task 3.3 exists to prevent.
            code = {"consent": 403, "no_audio": 422, "too_long": 413}.get(
                gate["reason"], 422)
            raise HTTPException(code, detail=gate["explanation"])
        samples = payload.get("samples")
        if not isinstance(samples, list):
            raise HTTPException(422, "samples must be a list of floats")
        if len(samples) > MAX_SAMPLES:
            raise HTTPException(413, f"too many samples (>{MAX_SAMPLES})")
        # Phase 4: VoiceGuard/MAYA is frozen behind a disabled feature flag.
        # No sample is processed, stored, echoed or scored; no model is imported
        # or invoked. The frozen capture contract still enforces consent/size.
        lang = _i18n.normalise_language(payload.get("lang"))
        return VOICEGUARD.screen(samples, consent=True, lang=lang)

    @app.post("/api/citizen/assess")
    async def assess(payload: Dict[str, Any] = Body(default={})):
        """Fuse whatever signals the client has into one citizen verdict.

        Every input is optional; an empty body returns LOW_CONFIDENCE, never a
        reassuring LOW. See citizen/risk/engine.py for the weighting rules.
        """
        lang = _i18n.normalise_language(payload.get("lang"))
        return risk_assess(
            voice=payload.get("voice"),
            message=payload.get("message"),
            campaign_linked=bool(payload.get("campaign_linked", False)),
            # Phase 3 fuzz finding: `int("abc")` here raised ValueError and the
            # endpoint returned 500. Coerce defensively at the boundary as well
            # as inside the engine — the boundary is what sees untrusted phones.
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
        note = str(payload.get("note") or "")[:200]  # may be empty; raw content NOT required
        case_id = str(payload.get("case_id") or "").strip()
        if case_id and not __import__("re").fullmatch(r"[A-Za-z0-9_]{3,40}", case_id):
            raise HTTPException(422, "case_id must match ^[A-Za-z0-9_]{3,40}$")
        # Optional opaque linkage token (the campaign-fusion key). Never
        # contains PII; the sanitizer digests it into a stable opaque token.
        entities = {"case_id": case_id} if case_id else {}
        severity_band = round(severity, 2)
        event = {
            "event_id": f"evt_cit_{uuid.uuid4().hex[:10]}",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ring": "RING_0_CITIZEN",
            "organ": "CITIZEN_APP",
            "signal_type": CATEGORIES[category],
            "severity": severity_band,
            "entities": entities,   # no PII, ever — reports carry category + band (+ optional opaque case token)
            "metrics": {"severity_band": severity_band,
                        "lang_digest": "sha256:" + __import__("hashlib").sha256(lang.encode()).hexdigest()[:8]},
        }
        state["reports_today"] += 1
        forward = _sign_and_forward(event)
        payload_out = {"status": "REPORTED", "event_id": event["event_id"],
                       "category": category, "severity": severity_band,
                       "forwarded": forward, "helpline": "1930",
                       "lang": lang}
        # Part Four: a 200 from *this* server is not delivery. `explain_report`
        # re-derives what actually happened from `forwarded` and will say
        # "received, but not passed on" rather than "Report sent". The state
        # passed here is only the fallback for the failure case.
        payload_out["explanation"] = _i18n.explain_report(
            payload_out, lang, "sent" if forward else "offline")
        payload_out["delivered"] = payload_out["explanation"]["delivered"]
        return payload_out
        # note is accepted for future on-device features but is NEVER stored or sent

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
        # Phase 5 bug found by running the app rather than the tests: this used
        # to return index.html *at /* while every asset in it is referenced
        # relatively (styles.css, app.js, maya-capture.js, sw.js). Those
        # requests resolved to /styles.css, /app.js ... which 404, so the page
        # rendered unstyled and every script failed to load — including the
        # microphone path, which then reported "microphone not available" on a
        # device that has one. Redirect to the mount instead.
        return RedirectResponse(url="/app/", status_code=307)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="RAKSHA Citizen service")
    parser.add_argument("--port", type=int, default=8095)
    parser.add_argument("--bus-url", default=os.environ.get("RAKSHA_BUS_URL", ""))
    args = parser.parse_args()
    import uvicorn
    app = build_app(bus_url=args.bus_url)
    uvicorn.run(app, host="0.0.0.0", port=args.port)


app = build_app()

if __name__ == "__main__":
    main()
