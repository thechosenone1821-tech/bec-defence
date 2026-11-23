import json
import os
import sys
import math

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.api import build_app
from fastapi.testclient import TestClient


@pytest.fixture()
def captured():
    return []


@pytest.fixture()
def client(captured):
    app = build_app(
        bus_url="http://unused.invalid",
        poster=lambda evt: (captured.append(evt), {"accepted": 1})[1],
        voice_model_provider=lambda: None,
        voice_model_status_provider=lambda: {
            "configured": False, "loaded": False, "error": None,
            "contract": "mono_float32_16khz_32000_samples_to_spoof_probability",
        },
    )
    return TestClient(app)


def _tone(seconds=2.0):
    return [0.6 * math.sin(2 * math.pi * 440 * i / 16000)
            for i in range(int(seconds * 16000))]


def test_health(client):
    result = client.get("/api/citizen/health").json()
    assert result["status"] == "ok"
    assert "advisory" in result["honesty"]
    assert result["voiceguard"]["loaded"] is False


def test_screen_message_endpoint(client):
    result = client.post(
        "/api/citizen/screen_message",
        json={"text": "URGENT: CBI digital arrest — transfer fine immediately"},
    ).json()
    assert result["verdict"] in {"HIGH", "CRITICAL"}
    assert result["helpline"] == "1930"


def test_report_signs_and_forwards_tokenized_event(client, captured):
    result = client.post(
        "/api/citizen/report",
        json={"category": "voice", "severity": 0.9, "lang": "te",
              "note": "raw scam message must NOT appear anywhere"},
    ).json()
    assert result["status"] == "REPORTED"
    assert result["forwarded"]["forwarded"] is True
    assert len(captured) == 1
    event = captured[0]
    from spine.telemetry_mac import verify_event
    assert verify_event(event) is True
    assert event["signal_type"] == "CITIZEN_REPORT_VOICE"
    assert event["entities"] == {}
    assert "raw scam message" not in json.dumps(event)


def test_report_rejects_unknown_category(client):
    response = client.post("/api/citizen/report", json={"category": "everything"})
    assert response.status_code == 422


def test_voice_requires_explicit_consent(client):
    response = client.post(
        "/api/citizen/screen_voice",
        json={"samples": _tone()},
    )
    assert response.status_code == 403


def test_voice_endpoint_screens_with_consent(client):
    response = client.post(
        "/api/citizen/screen_voice",
        json={"samples": _tone(), "sample_rate": 16000, "consent": True},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["verdict"] in {"SUSPICIOUS", "INCONCLUSIVE", "SILENT"}
    assert result["helpline"] == "1930"
    assert result["audio_retention"].startswith("not stored")
    assert "samples" not in result


def test_voice_endpoint_rejects_more_than_two_seconds(client):
    response = client.post(
        "/api/citizen/screen_voice",
        json={"samples": [0.0] * 32001, "consent": True},
    )
    assert response.status_code == 413


def test_voice_endpoint_rejects_non_16khz(client):
    response = client.post(
        "/api/citizen/screen_voice",
        json={"samples": _tone(), "sample_rate": 44100, "consent": True},
    )
    assert response.status_code == 422


def test_voice_endpoint_requires_sample_list(client):
    response = client.post(
        "/api/citizen/screen_voice",
        json={"samples": "not audio", "consent": True},
    )
    assert response.status_code == 422
