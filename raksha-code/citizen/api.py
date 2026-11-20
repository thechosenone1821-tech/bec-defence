"""RAKSHA Citizen API — offline-first citizen defence service + PWA host.

    python -m citizen.api --port 8095

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

Honesty: message screening is heuristic (see messageguard); voice screening is
as heuristic fallback (see voiceguard); neither is an accusation — verdicts are
advisory and every screen links to the 1930 national cybercrime helpline.
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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from citizen.messageguard import score_message
from citizen.voiceguard import score_voice

_HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(_HERE, "app")

MAX_SAMPLES = 240_000
CATEGORIES = {"voice": "CITIZEN_REPORT_VOICE", "message": "CITIZEN_REPORT_MESSAGE",
              "financial": "CITIZEN_REPORT_FINANCIAL", "other": "CITIZEN_REPORT_OTHER"}


def _clamp_severity(value: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def build_app(bus_url: Optional[str] = None, poster: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> FastAPI:
    bus_url = (bus_url or os.environ.get("RAKSHA_BUS_URL", "")).rstrip("/")
    app = FastAPI(title="RAKSHA Citizen", version="0.3.0-m3")
    state = {"started_at": time.time(), "reports_today": 0}

    def _sign_and_forward(event: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from spine.telemetry_mac import sign_event
        except Exception:
            try:
                import sys
                sys.path.insert(0, os.path.dirname(_HERE))
                from spine.telemetry_mac import sign_event
            except Exception as exc:
                return {"forwarded": False, "error": f"signing unavailable: {exc}"}
        signed = sign_event(dict(event))
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
        return {"status": "ok", "engine": "messageguard-rules-v0 + spectral_fallback_v0",
                "bus_configured": bool(bus_url), "reports_today": state["reports_today"],
                "honesty": "heuristic detectors — not a security guarantee"}

    @app.post("/api/citizen/screen_message")
    async def screen_message(payload: Dict[str, Any] = Body(...)):
        text = str(payload.get("text") or "")[:4000]
        result = score_message(text)
        result["helpline"] = "1930"
        result["disclaimer"] = "Advisory only. If unsure, do not act — call 1930."
        return result

    @app.post("/api/citizen/screen_voice")
    async def screen_voice(payload: Dict[str, Any] = Body(...)):
        samples = payload.get("samples")
        if not isinstance(samples, list):
            raise HTTPException(422, "samples must be a list of floats")
        if len(samples) > MAX_SAMPLES:
            raise HTTPException(413, f"too many samples (>{MAX_SAMPLES})")
        result = score_voice(samples)
        result["helpline"] = "1930"
        return result

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
        return {"status": "REPORTED", "event_id": event["event_id"],
                "category": category, "severity": severity_band,
                "forwarded": forward, "helpline": "1930"}
        # note is accepted for future on-device features but is NEVER stored or sent

    app.mount("/app", StaticFiles(directory=APP_DIR, html=True), name="app")

    @app.get("/")
    async def root():
        return FileResponse(os.path.join(APP_DIR, "index.html"))

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
