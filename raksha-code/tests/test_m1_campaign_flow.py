"""M1 spine acceptance test — the exit criterion from BUILD_GUIDE.md §M1:

    "one synthetic campaign flows bus → graph → Governor → ledger and back
     out via /api/state"

Everything runs on the dry-run executor (no host ever touched) and against a
temp policy copy so no repo files are written.
"""

import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from spine.bus import create_app
from spine.telemetry_mac import sign_event
from spine.ledger import AuditLedger

SPINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spine")
POLICY_SRC = os.path.join(SPINE, "config", "policy.yaml")
TOPOLOGY = os.path.join(SPINE, "config", "company_topology.json")

HOST = "HOST_AB12CD"
USER = "USER_77AA01"
SESS = "SESS_3F4A9C"

CAMPAIGN_EVENTS = [
    {"ring": "RING_3_ENDPOINT_SILICON", "organ": "ENDPOINT_PAGE_CURVE",
     "signal_type": "PARITY_ENTROPY_COLLAPSE", "severity": 0.96,
     "entities": {"host_id": HOST, "user_id": USER, "vlan_id": "VLAN_CORP_IT"},
     "metrics": {"bytes_written": 4096, "parity_delta": 0.99},
     "event_id": "evt_m1camp_0001", "timestamp_utc": "2026-11-20T09:00:00Z"},
    {"ring": "RING_3_ENDPOINT_SILICON", "organ": "LANDAUER_THERMAL_AUDIT",
     "signal_type": "UNACCOUNTED_POWER_RESIDUAL", "severity": 0.71,
     "entities": {"host_id": HOST, "user_id": USER, "vlan_id": "VLAN_CORP_IT"},
     "metrics": {"unaccounted_watts": 16.5},
     "event_id": "evt_m1camp_0002", "timestamp_utc": "2026-11-20T09:00:05Z"},
    {"ring": "RING_1_PERIMETER_IDENTITY", "organ": "COOKIE_FLUID_TURBULENCE",
     "signal_type": "TURBULENT_SESSION_REPLAY", "severity": 0.82,
     "entities": {"session_id": SESS, "user_id": USER, "host_id": HOST},
     "metrics": {"laminar_ratio": 0.12},
     "event_id": "evt_m1camp_0003", "timestamp_utc": "2026-11-20T09:00:10Z"},
]


@pytest.fixture()
def stack(tmp_path):
    cfg = tmp_path / "config"
    cfg.mkdir()
    shutil.copy(POLICY_SRC, cfg / "policy.yaml")
    app = create_app(policy_path=str(cfg / "policy.yaml"),
                     topology_path=TOPOLOGY, model="qwen3.5:4b")
    client = TestClient(app)
    return client, cfg


def test_forged_batch_cannot_reach_the_ai_path(stack):
    client, _ = stack
    r = client.post("/api/ingest", json=CAMPAIGN_EVENTS).json()
    assert r == {"accepted": 3, "received": 3, "unverified": 3}
    bundle = client.post("/api/orchestrate").json()
    assert bundle["status"] == "HELD_UNVERIFIED_EVIDENCE"


def test_synthetic_campaign_flows_end_to_end(stack):
    client, cfg = stack
    signed = [sign_event(dict(e)) for e in CAMPAIGN_EVENTS]
    r = client.post("/api/ingest", json=signed).json()
    assert r["accepted"] == 3 and r["unverified"] == 0

    bundle = client.post("/api/orchestrate").json()
    assert bundle["status"] == "OK"
    tools = [res["tool"] for res in bundle["results"]]
    statuses = [res["result"]["status"] for res in bundle["results"]]
    assert "arm_page_curve_traps" in tools        # parity collapse ⇒ trap pre-arm
    assert "escalate_human_stepup" in tools       # sev ≥ 0.9 ⇒ human asked
    organ_ok = {"CLUSTER_DROPPED", "SESSION_REVOKED", "DOCUMENT_QUARANTINED",
                "STEERING_CLAMPED", "TRAPS_ARMED", "TRAP_DENSITY_BOOSTED",
                "HOST_ISOLATED", "PERCOLATION_CUT_APPROVED", "SHIELD_DEPLOYED",
                "SERVICE_READONLY_SET", "HUMAN_STEPUP_REQUESTED", "SHIELD_SPLICED"}
    assert all(s.startswith("DRY_RUN_") or s in organ_ok or s in {"APPROVED", "BLOCKED", "ESCALATE"}
               for s in statuses)
    assert bundle["decisions"] and all(
        d["fortress_tcb"] in {"ok", "tcb_override", "frozen", "fortress_absent"} for d in bundle["decisions"])

    state = client.get("/api/state").json()
    campaigns = state["campaigns"]
    big = [c for c in campaigns if c["size"] >= 3]
    assert big, f"expected one fused campaign, got {campaigns}"
    camp = big[0]
    assert camp["campaign_id"].startswith("cmp_")
    assert camp["severity_max"] == pytest.approx(0.96)
    assert USER in camp["entities"] and HOST in camp["entities"]

    assert state["executor_mode"] == "organ"        # sentinel shields wired (M2)
    assert state["fortress"]["telemetry_mac"] is True
    assert state["fortress"]["unverified_held"] == 0
    assert state["governor"]["config_integrity"] == "ok"

    ledger = AuditLedger(str(cfg / "audit_ledger.jsonl"))
    verdict = ledger.verify()
    assert verdict["valid"] is True and verdict["entries"] >= 2
    record_types = [json.loads(line)["record_type"] for line in
                    open(cfg / "audit_ledger.jsonl")]
    assert "governor_decision" in record_types
    assert "orchestration" in record_types


def test_unsigned_cannot_seed_a_campaign_but_remains_visible(stack):
    client, _ = stack
    r = client.post("/api/ingest", json=CAMPAIGN_EVENTS).json()
    assert r["unverified"] == 3
    state = client.get("/api/state").json()
    assert state["campaigns"] == []                      # unverified ⇒ inert
    assert state["fortress"]["unverified_held"] == 3     # but visible
    assert len(state["recent_events"]) == 3
