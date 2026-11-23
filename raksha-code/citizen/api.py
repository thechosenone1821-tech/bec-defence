"""RAKSHA Citizen API — same-origin, privacy-conscious screening service.

Voice screening requires consent=true on every request. It accepts only mono
16 kHz samples up to two seconds, never writes audio to disk, never forwards
audio to the shared spine, and returns advisory output only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from typing import Any, Callable, Dict, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from citizen.messageguard import score_message
from citizen.voiceguard import score_voice
from citizen.voiceguard.model import get_model, get_model_status

_HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(_HERE, "app")
MAX_SAMPLES = 32_000
CATEGORIES = {
    "voice": "CITIZEN_REPORT_VOICE",
    "message": "CITIZEN_REPORT_MESSAGE",
    "financial": "CITIZEN_REPORT_FINANCIAL",
    "other": "CITIZEN_REPORT_OTHER",
}


def _clamp_severity(value: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def build_app(
    bus_url: Optional[str] = None,
    poster: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    voice_model_provider: Optional[Callable[[], Any]] = None,
    voice_model_status_provider: Optional[Callable[[], Dict[str, Any]]] = None,
) -> FastAPI:
    bus_url = (bus_url or os.environ.get("RAKSHA_BUS_URL", "")).rstrip("/")
    model_provider = voice_model_provider or get_model
    model_status_provider = voice_model_status_provider or get_model_status
    app = FastAPI(title="RAKSHA Citizen", version="0.4.0-voiceguard")
    state = {"started_at": time.time(), "reports_today": 0}

    def _sign_and_forward(event: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from spine.telemetry_mac import sign_event
        except Exception:
            try:
                sys.path.insert(0, os.path.dirname(_HERE))
                from spine.telemetry_mac import sign_event
            except Exception as exc:
                return {"forwarded": False, "error": f"signing unavailable: {type(exc).__name__}"}
        signed = sign_event(dict(event))
        if poster is not None:
            return {"forwarded": True, **poster(signed)}
        if not bus_url:
            return {
                "forwarded": False,
                "reason": "RAKSHA_BUS_URL not configured — demo mode",
                "event_id": signed.get("event_id"),
            }
        import urllib.request
        request = urllib.request.Request(
            bus_url + "/api/ingest",
            data=json.dumps([signed]).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return {"forwarded": True, "bus_reply": json.loads(response.read().decode())}
        except Exception as exc:
            return {"forwarded": False, "error": type(exc).__name__,
                    "event_id": signed.get("event_id")}

    @app.get("/api/citizen/health")
    async def health():
        model_status = model_status_provider()
        return {
            "status": "ok",
            "engine": "messageguard-rules-v0 + voiceguard",
            "voiceguard": model_status,
            "bus_configured": bool(bus_url),
            "reports_today": state["reports_today"],
            "honesty": "advisory heuristic or configured local model; not a security guarantee",
        }

    @app.post("/api/citizen/screen_message")
    async def screen_message(payload: Dict[str, Any] = Body(...)):
        message = str(payload.get("text") or "")[:4000]
        result = score_message(message)
        result["helpline"] = "1930"
        result["disclaimer"] = "Advisory only. If unsure, do not act — call 1930."
        return result

    @app.post("/api/citizen/screen_voice")
    async def screen_voice_endpoint(payload: Dict[str, Any] = Body(...)):
        if payload.get("consent") is not True:
            raise HTTPException(
                403,
                "explicit consent is required before audio is sent for VoiceGuard screening",
            )
        samples = payload.get("samples")
        if not isinstance(samples, list):
            raise HTTPException(422, "samples must be a list of mono float samples")
        if len(samples) > MAX_SAMPLES:
            raise HTTPException(413, f"audio window must be at most {MAX_SAMPLES} samples (2 seconds at 16 kHz)")
        sample_rate = payload.get("sample_rate", 16_000)
        if sample_rate != 16_000:
            raise HTTPException(422, "sample_rate must be 16000 Hz")
        model = model_provider()
        result = score_voice(samples, sample_rate=sample_rate, model=model)
        result["helpline"] = "1930"
        result["audio_retention"] = "not stored; request-memory processing only"
        result["model_status"] = "loaded" if model is not None else "fallback"
        # Do not attach samples or any waveform data to responses, reports or telemetry.
        return result

    @app.post("/api/citizen/report")
    async def report(payload: Dict[str, Any] = Body(...)):
        category = str(payload.get("category") or "").lower()
        if category not in CATEGORIES:
            raise HTTPException(422, f"category must be one of {sorted(CATEGORIES)}")
        severity = _clamp_severity(payload.get("severity"), 0.5)
        lang = str(payload.get("lang") or "en")[:8]
        case_id = str(payload.get("case_id") or "").strip()
        if case_id and not re.fullmatch(r"[A-Za-z0-9_]{3,40}", case_id):
            raise HTTPException(422, "case_id must match ^[A-Za-z0-9_]{3,40}$")
        severity_band = round(severity, 2)
        event = {
            "event_id": f"evt_cit_{uuid.uuid4().hex[:10]}",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ring": "RING_0_CITIZEN",
            "organ": "CITIZEN_APP",
            "signal_type": CATEGORIES[category],
            "severity": severity_band,
            "entities": {"case_id": case_id} if case_id else {},
            "metrics": {
                "severity_band": severity_band,
                "lang_digest": "sha256:" + hashlib.sha256(lang.encode()).hexdigest()[:8],
            },
        }
        state["reports_today"] += 1
        forward = _sign_and_forward(event)
        return {
            "status": "REPORTED",
            "event_id": event["event_id"],
            "category": category,
            "severity": severity_band,
            "forwarded": forward,
            "helpline": "1930",
        }

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
    uvicorn.run(build_app(bus_url=args.bus_url), host="0.0.0.0", port=args.port)


app = build_app()

if __name__ == "__main__":
    main()
