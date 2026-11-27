"""Bus API: auth, ingest, state, decisions, no-override, ledger, metrics, WS."""

from __future__ import annotations

import threading

from conftest import ADMIN_TOKEN, OBSERVER_TOKEN, SENSOR_KEY, SENSOR_TOKEN, make_event, signed_event


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_healthz_no_auth(client) -> None:
    body = client.get("/healthz").json()
    assert body["status"] == "ok" and body["version"]


def test_missing_token_is_401(client) -> None:
    assert client.get("/v1/state").status_code == 401


def test_bad_token_is_401(client) -> None:
    assert client.get("/v1/state", headers=_headers("nope")).status_code == 401


def test_scope_enforced(client) -> None:
    # observer has `read` only -> cannot write telemetry
    event = signed_event()
    assert client.post("/v1/telemetry", json=event.to_dict(),
                       headers=_headers(OBSERVER_TOKEN)).status_code == 403
    # sensor has `telemetry:write` only -> cannot read state
    assert client.get("/v1/state", headers=_headers(SENSOR_TOKEN)).status_code == 403


def test_verified_event_flows_through(client) -> None:
    event = signed_event(event_id="EV-OK-1")
    result = client.post("/v1/telemetry", json=event.to_dict(), headers=_headers(SENSOR_TOKEN)).json()
    assert result["verified"] == "valid"
    assert result["detections"][0]["organ"] == "voiceguard"
    assert result["detections"][0]["rule_id"].startswith("VG-")


def test_tampered_event_is_quarantined_not_actionable(client) -> None:
    event = signed_event(event_id="EV-TAM-1", organ="fileguard", leg="infra",
                         entity="N-BUILD-SRV", payload={"encrypt_events_per_min": 900})
    event.severity = 1  # flip after signing
    result = client.post("/v1/telemetry", json=event.to_dict(), headers=_headers(SENSOR_TOKEN)).json()
    assert result["verified"] == "tampered"
    assert result["detections"] == []
    quarantine = client.get("/v1/quarantine", headers=_headers(OBSERVER_TOKEN)).json()
    assert any(item["event_id"] == "EV-TAM-1" and not item["verified"] for item in quarantine["items"])


def test_unsigned_event_is_quarantined(client) -> None:
    event = make_event("EV-UNS-1")
    result = client.post("/v1/telemetry", json=event.to_dict(), headers=_headers(SENSOR_TOKEN)).json()
    assert result["verified"] == "unsigned"


def test_malformed_envelope_is_422(client) -> None:
    raw = signed_event().to_dict()
    raw.pop("organ")
    assert client.post("/v1/telemetry", json=raw, headers=_headers(SENSOR_TOKEN)).status_code == 422


def test_duplicate_event_id_rejected_at_api(client) -> None:
    event = signed_event(event_id="EV-DUP-API")
    headers = _headers(SENSOR_TOKEN)
    assert client.post("/v1/telemetry", json=event.to_dict(), headers=headers).json()["accepted"]
    second = client.post("/v1/telemetry", json=event.to_dict(), headers=headers).json()
    assert second["accepted"] is False


def test_state_and_campaigns_after_full_scenario(client) -> None:
    from raksha.raavan.player import RaavanPlayer
    from raksha.raavan import load_scenario
    # feed the corpus through the API (fresh sensor client-side key is the fixture key)
    from raksha.events import sign_event
    player = RaavanPlayer(
        transport=lambda e: client.post("/v1/telemetry", json=e.to_dict(),
                                        headers=_headers(SENSOR_TOKEN)).json(),
        sensor_key=SENSOR_KEY, scenario=load_scenario())
    report = player.run()
    assert report["ok"], report["failures"]

    state = client.get("/v1/state", headers=_headers(OBSERVER_TOKEN)).json()
    assert state["ledger_height"] >= 10
    campaigns = state["campaigns"]
    c2247 = [c for c in campaigns if c["campaign_id"] == "C-2247"]
    assert c2247 and sorted(c2247[0]["legs"]) == ["citizen", "infra"]
    crowns = [n for n in state["topology"]["nodes"] if n.get("crown")]
    assert {n["id"] for n in crowns} == {"N-TIER0-CORE", "N-IDENTITY-VAULT"}
    assert any(n["detected"] for n in state["topology"]["nodes"])


def test_decisions_including_refusal_exposed(client) -> None:
    test_state_and_campaigns_after_full_scenario(client)
    decisions = client.get("/v1/decisions", headers=_headers(OBSERVER_TOKEN)).json()["decisions"]
    refusals = [d for d in decisions if d["verdict"] == "REFUSED"]
    assert len(refusals) == 1 and refusals[0]["ref"] == "PROP-C-2247-ICU-CUT"
    assert refusals[0]["fallback"] == "PROP-C-2247-N-BUILD-SRV-EGRESS"
    assert len([d for d in decisions if d["verdict"] == "ALLOWED"]) == 3


def test_override_is_impossible_even_for_admin(client) -> None:
    response = client.post("/v1/decisions/PROP-C-2247-ICU-CUT/override",
                           headers=_headers(ADMIN_TOKEN))
    assert response.status_code == 403
    assert "append-only" in response.json()["detail"]


def test_ledger_endpoints(client) -> None:
    head = client.get("/v1/ledger/head", headers=_headers(OBSERVER_TOKEN)).json()
    assert head["height"] == 1  # genesis only
    assert client.get("/v1/ledger/verify", headers=_headers(OBSERVER_TOKEN)).json()["ok"] is True
    block = client.post("/v1/ledger/entries", headers=_headers(ADMIN_TOKEN),
                        json={"kind": "ops-note", "ref": "OPS-1", "text": "rotate sensor",
                              "payload": {"by": "ops"}}).json()
    assert block["seq"] == 1
    assert client.post("/v1/ledger/entries", headers=_headers(OBSERVER_TOKEN),
                       json={"kind": "ops-note", "ref": "X", "text": "nope"}).status_code == 403


def test_metrics_endpoint(client) -> None:
    client.post("/v1/telemetry", json=signed_event(event_id="EV-M-1").to_dict(),
                headers=_headers(SENSOR_TOKEN))
    snap = client.get("/v1/metrics", headers=_headers(OBSERVER_TOKEN)).json()
    assert snap["counters"]["ingest.verified"] == 1
    assert "ingest" in snap["latency_ms"]
    assert snap["store"]["events"] == 1


def test_websocket_stream_broadcasts(client) -> None:
    app = client.app
    from fastapi.testclient import TestClient
    poster_client = TestClient(app)

    def post() -> None:
        poster_client.post("/v1/telemetry", json=signed_event(event_id="EV-WS-1").to_dict(),
                           headers=_headers(SENSOR_TOKEN))

    with client.websocket_connect(f"/v1/telemetry/stream?token={OBSERVER_TOKEN}") as ws:
        hello = ws.receive_json()
        assert hello["kind"] == "hello"
        thread = threading.Thread(target=post)
        thread.start()
        message = ws.receive_json()
        thread.join(5)
        assert message["kind"] == "detection"
        assert message["data"]["organ"] == "voiceguard"


def test_websocket_rejects_bad_token(client) -> None:
    try:
        with client.websocket_connect("/v1/telemetry/stream?token=wrong"):
            raised = False
    except Exception:
        raised = True
    assert raised
