"""M4 acceptance — RAAVAN kill chain + citizen↔sentinel campaign fusion."""

import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from fastapi.testclient import TestClient

from spine.bus import create_app
from spine.telemetry_mac import sign_event
from raavan.killchain import build_campaign, run, STEPS, _CASE_ID

SPINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spine")
POLICY_SRC = os.path.join(SPINE, "config", "policy.yaml")
TOPOLOGY = os.path.join(SPINE, "config", "company_topology.json")
PLAYBOOK = os.path.join(os.path.dirname(SPINE), "raavan", "playbook.yaml")


@pytest.fixture()
def spine_client(tmp_path):
    cfg = tmp_path / "config"
    cfg.mkdir()
    shutil.copy(POLICY_SRC, cfg / "policy.yaml")
    app = create_app(policy_path=str(cfg / "policy.yaml"),
                     topology_path=TOPOLOGY, model="qwen3.5:4b")
    return TestClient(app)


def ingest_f(client):
    return lambda batch: client.post("/api/ingest", json=batch).json()


def orchestrate_f(client):
    return lambda: client.post("/api/orchestrate").json()


def state_f(client):
    return lambda: client.get("/api/state").json()


def test_playbook_shape_and_coverage():
    data = yaml.safe_load(open(PLAYBOOK, encoding="utf-8"))
    assert data["version"] == 1
    ids = [t["id"] for t in data["techniques"]]
    assert len(ids) == 10
    for t in data["techniques"]:
        for key in ("id", "name", "kill_chain_stage", "layers", "fixture", "expected_defense"):
            assert t.get(key), (t.get("id"), key)
    # layers span citizen + infrastructure
    layers = {l for t in data["techniques"] for l in t["layers"]}
    assert {"citizen", "endpoint", "identity", "agent", "governor"} <= layers


def test_forged_raavan_cannot_steer_the_ai_path(spine_client):
    events = build_campaign()
    r = spine_client.post("/api/ingest", json=events).json()
    assert r["unverified"] == len(events)
    bundle = spine_client.post("/api/orchestrate").json()
    assert bundle["status"] == "HELD_UNVERIFIED_EVIDENCE"
    # forged evidence remains visible for the SOC
    assert spine_client.get("/api/state").json()["fortress"]["unverified_held"] == len(events)


def test_full_kill_chain_fuses_into_one_campaign(spine_client):
    summary = run(ingest_f(spine_client), orchestrate_f(spine_client),
                  state_f(spine_client), sign_event, log=lambda *_: None)
    bundle = summary["bundle"]
    assert bundle["status"] == "OK"
    tools = [r["tool"] for r in bundle["results"]]
    # impact-stage parity collapse ⇒ human step-up is unavoidable
    assert "escalate_human_stepup" in tools
    assert "arm_page_curve_traps" in tools

    campaigns = summary["campaigns"]
    assert campaigns, "no campaign fused"
    biggest = campaigns[0]
    assert biggest["size"] >= 5
    layers = set(summary["layers"])
    # the fused campaign spans the citizen organ and the infrastructure organs
    assert "CITIZEN_APP" in layers
    assert {"COOKIE_FLUID_TURBULENCE", "ENDPOINT_PAGE_CURVE", "BRAGG_FFT_FIREWALL"} & layers


def test_case_token_digest_is_stable_across_ingests(spine_client):
    events = [sign_event(dict(e)) for e in build_campaign()[:2]]
    spine_client.post("/api/ingest", json=events)
    first = spine_client.get("/api/state").json()["recent_events"][-1]["entities"]["case_id"]
    assert first.startswith("sha256:")
    # sanitizer digests are salt-free sha256 prefixes — same input, same token
    spine_client.post("/api/ingest", json=[sign_event(dict(build_campaign()[0],
                                                          event_id="evt_raavan_recheck_1"))])
    second = spine_client.get("/api/state").json()["recent_events"][-1]["entities"]["case_id"]
    assert first == second


def test_governor_blocks_raavan_icu_cut_attempt(spine_client):
    """The knockout blow: RAAVAN tries to make RAKSHA cut the ICU VLAN —
    the deterministic Governor hard-blocks it, ledger or not."""
    from spine.governor import PolicyEngine
    from spine.ledger import AuditLedger
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        gov = PolicyEngine(POLICY_SRC, ledger=AuditLedger(os.path.join(tmp, "l.jsonl")))
        d = gov.evaluate({"tool": "execute_percolation_cut",
                          "args": {"target_spectral_radius": 0.9,
                                   "preserve_tier0_vlans": False,
                                   "vlan_hint": "VLAN_ICU_CLINICAL"}})
        assert d["decision"] == "BLOCKED"
        d2 = gov.evaluate({"tool": "execute_percolation_cut",
                           "args": {"target_spectral_radius": 0.9,
                                    "preserve_tier0_vlans": True,
                                    "note": "VLAN_ICU_CLINICAL"}})
        assert d2["decision"] == "BLOCKED"   # crown jewel in args ⇒ hard block


def test_campaign_shape_is_deterministic():
    a = build_campaign()
    b = build_campaign()
    assert [e["event_id"] for e in a] == [e["event_id"] for e in b]
    assert [e["signal_type"] for e in a] == [s["event"]["signal_type"] for s in STEPS]
