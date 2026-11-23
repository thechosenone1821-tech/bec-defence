import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.api import build_app
from fastapi.testclient import TestClient


@pytest.fixture()
def captured():
    return []


@pytest.fixture()
def client(captured):
    app = build_app(bus_url="http://unused.invalid",
                    poster=lambda evt: (captured.append(evt), {"accepted": 1})[1])
    return TestClient(app)


def test_health(client):
    r = client.get("/api/citizen/health").json()
    assert r["status"] == "ok"
    assert "heuristic" in r["honesty"]


def test_screen_message_endpoint(client):
    v = client.post("/api/citizen/screen_message",
                    json={"text": "URGENT: CBI digital arrest — transfer fine immediately"}).json()
    assert v["verdict"] in {"HIGH", "CRITICAL"}
    assert v["helpline"] == "1930"


def test_report_signs_and_forwards_tokenized_event(client, captured):
    v = client.post("/api/citizen/report",
                    json={"category": "voice", "severity": 0.9, "lang": "te",
                          "note": "raw scam message must NOT appear anywhere"}).json()
    assert v["status"] == "REPORTED"
    assert v["forwarded"]["forwarded"] is True
    assert len(captured) == 1
    evt = captured[0]
    from spine.telemetry_mac import verify_event
    assert verify_event(evt) is True
    assert evt["signal_type"] == "CITIZEN_REPORT_VOICE"
    assert evt["entities"] == {}                       # no PII, by construction
    assert "raw scam message" not in json.dumps(evt)   # note never leaves


def test_report_rejects_unknown_category(client):
    r = client.post("/api/citizen/report", json={"category": "everything"})
    assert r.status_code == 422


def test_screen_voice_endpoint(client):
    import math
    samples = [0.6 * math.sin(2 * math.pi * 440 * i / 16000) for i in range(16000)]
    v = client.post("/api/citizen/screen_voice", json={"samples": samples}).json()
    # Phase 3's model may escalate a pure tone to LIKELY_SYNTHETIC.
    assert v["verdict"] in {"SUSPICIOUS", "INCONCLUSIVE", "SILENT", "LIKELY_SYNTHETIC"}


def test_screen_voice_rejects_oversized(client):
    r = client.post("/api/citizen/screen_voice", json={"samples": [0.0] * 250_000})
    assert r.status_code == 413
