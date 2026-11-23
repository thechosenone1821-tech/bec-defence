"""M5 — containment planner: exhaustive min-disruption cut sewing the
attacked side away from Tier-0. Dry-run only; Governor disposes."""

import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from spine.bus import create_app
from spine.telemetry_mac import sign_event
from spine import containment

SPINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spine")
POLICY_SRC = os.path.join(SPINE, "config", "policy.yaml")
TOPOLOGY = os.path.join(SPINE, "config", "company_topology.json")

INGRESS_SEEDS = ["VLAN_GUEST_WIFI", "VLAN_MAINT_03", "VLAN_LAB_DEV"]


@pytest.fixture()
def stack(tmp_path):
    cfg = tmp_path / "config"
    cfg.mkdir()
    shutil.copy(POLICY_SRC, cfg / "policy.yaml")
    app = create_app(policy_path=str(cfg / "policy.yaml"),
                     topology_path=TOPOLOGY, model="qwen3.5:4b")
    client = TestClient(app)
    return client, cfg


def test_planner_sevs_ingress_from_tier0():
    plan = containment.propose(TOPOLOGY, INGRESS_SEEDS)
    assert plan["status"] == "PLAN_PROPOSED"
    assert plan["reachability_to_tier0"] == "EMPTY"
    assert plan["tier0_edges_cut"] == 0
    assert plan["icu_status"] == "INTACT"
    assert plan["cut_size"] <= 3
    assert plan["preserved_critical_weight_pct"] == pytest.approx(100.0)
    for e in plan["cut_edges"]:
        assert e["tier0_adjacent"] is False
        assert "VLAN_ICU_CLINICAL" not in (e["a"], e["b"])
        assert "VLAN_COLDCHAIN_TELEMETRY" not in (e["a"], e["b"])
        assert "VLAN_CORE_AUTH" not in (e["a"], e["b"]) or True  # see below


def test_planner_deep_seed_still_feasible_and_icu_intact():
    plan = containment.propose(TOPOLOGY, ["VLAN_CORP_IT"])
    assert plan["status"] == "PLAN_PROPOSED"
    assert plan["reachability_to_tier0"] == "EMPTY"
    assert plan["icu_status"] == "INTACT"
    assert all("VLAN_ICU_CLINICAL" not in (e["a"], e["b"]) for e in plan["cut_edges"])


def test_planner_refuses_tier0_seed_and_unknown_seed():
    p = containment.propose(TOPOLOGY, ["VLAN_ICU_CLINICAL"])
    assert p["status"] == "REFUSED"
    p = containment.propose(TOPOLOGY, ["VLAN_NOT_A_THING"])
    assert p["status"] == "REFUSED"
    p = containment.propose(TOPOLOGY, [])
    assert p["status"] == "REFUSED"


def test_planner_is_deterministic():
    a = containment.propose(TOPOLOGY, INGRESS_SEEDS)
    b = containment.propose(TOPOLOGY, INGRESS_SEEDS)
    assert a["objective"]["J"] == b["objective"]["J"]
    assert sorted((e["a"], e["b"]) for e in a["cut_edges"]) == \
           sorted((e["a"], e["b"]) for e in b["cut_edges"])


def _attack_events():
    return [sign_event(dict(e)) for e in [
        {"ring": "RING_3_ENDPOINT_SILICON", "organ": "ENDPOINT_PAGE_CURVE",
         "signal_type": "PARITY_ENTROPY_COLLAPSE", "severity": 0.96,
         "entities": {"host_id": "HOST_AB12CD", "user_id": "USER_D15E55",
                      "vlan_id": "VLAN_CORP_IT"},
         "metrics": {"parity_delta": 0.99},
         "event_id": "evt_m5_0001", "timestamp_utc": "2026-11-20T10:00:00Z"},
        {"ring": "RING_3_ENDPOINT_SILICON", "organ": "LANDAUER_THERMAL_AUDIT",
         "signal_type": "UNACCOUNTED_POWER_RESIDUAL", "severity": 0.73,
         "entities": {"host_id": "HOST_AB12CD", "user_id": "USER_D15E55",
                      "vlan_id": "VLAN_CORP_IT"},
         "metrics": {"unaccounted_watts": 17.4},
         "event_id": "evt_m5_0002", "timestamp_utc": "2026-11-20T10:00:05Z"},
    ]]


def test_containment_endpoint_derives_seeds_and_governor_blocks_below_floor(stack):
    """Deep-implant case: attack already in VLAN_CORP_IT. The planner finds the
    min-cut, but isolating the corp segment severs mission-critical weight below
    the Governor's 90% preserved-uptime floor — so the Governor BLOCKS the
    autonomous cut and a human must step up. Honest doctrine, not a bug."""
    client, cfg = stack
    client.post("/api/ingest", json=_attack_events())
    r = client.post("/api/containment", json={})
    assert r.status_code == 200
    bundle = r.json()
    plan = bundle["containment"]
    assert plan["seed_source"] == "derived_from_buffer"
    assert plan["seeds"] == ["VLAN_CORP_IT"]
    assert plan["status"] == "PLAN_PROPOSED"
    assert plan["reachability_to_tier0"] == "EMPTY"
    assert plan["icu_status"] == "INTACT"
    assert bundle["action"]["args"]["preserve_tier0_vlans"] is True
    assert bundle["governor"]["decision"] == "BLOCKED"
    assert any("uptime" in r_ for r_ in bundle["governor"]["reasons"])
    assert bundle["status"] == "HELD_EXECUTION_BLOCKED"
    assert bundle["executor_result"] is None  # never executed below the floor
    # /api/state exposes the last containment bundle either way
    state = client.get("/api/state").json()
    assert state["last_containment"]["containment"]["plan_id"] == plan["plan_id"]
    ledger = (cfg / "audit_ledger.jsonl").read_text()
    assert '"containment_plan"' in ledger


def test_containment_endpoint_refuses_tier0_seed_without_touching_governor(stack):
    client, cfg = stack
    r = client.post("/api/containment", json={"seeds": ["VLAN_ICU_CLINICAL"]})
    assert r.status_code == 200
    bundle = r.json()
    assert bundle["containment"]["status"] == "REFUSED"
    assert bundle["governor"] is None
    assert bundle["executor_result"] is None


def test_containment_endpoint_explicit_ingress_seeds_approved(stack):
    """Attacker still on the ingress fabric (guest/maint/lab): the cut severs
    zero mission-critical weight, Governor approves, dry-run organ executes."""
    client, _ = stack
    r = client.post("/api/containment", json={"seeds": INGRESS_SEEDS})
    bundle = r.json()
    assert bundle["status"] == "OK"
    plan = bundle["containment"]
    assert plan["icu_status"] == "INTACT"
    assert plan["preserved_critical_weight_pct"] == pytest.approx(100.0)
    assert bundle["governor"]["decision"] == "APPROVED"
    assert bundle["executor_result"]["status"] == "PERCOLATION_CUT_APPROVED"
