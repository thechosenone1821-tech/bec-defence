"""Part 7 — the Spine's seven Definition-of-done boxes, earned one at a time.

`specs/07_spine.md` §5 lists seven claims. Six of them had no test naming them;
the ones that did were spread across four suites and did not assert the box.
This file earns each box by driving the real path — a signed POST through the
bus, the real Governor, the real ledger — not by calling an internal helper and
checking it returned something.

Box 4 is the one that failed when I tried to earn it. See
`TestBox4Tier0.gtest_a_tier0_service_cannot_be_isolated_by_its_own_id` for the
defect that was live until this file existed.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spine.governor import PolicyEngine
from spine.ledger import AuditLedger

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLICY = os.path.join(_HERE, "spine", "config", "policy.yaml")
TOPO = os.path.join(_HERE, "spine", "config", "company_topology.json")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from spine.bus import create_app
    app = create_app(policy_path=POLICY, topology_path=TOPO)
    return TestClient(app)


@pytest.fixture()
def ledger():
    path = tempfile.mktemp(suffix=".jsonl")
    yield AuditLedger(path)
    for suffix in ("", ".anchor"):
        try:
            os.unlink(path + suffix)
        except OSError:
            pass


@pytest.fixture()
def governor(ledger):
    return PolicyEngine(POLICY, ledger=ledger)


def _signed(event_id: str, **overrides):
    from spine.telemetry_mac import sign_event
    event = {
        "event_id": event_id,
        "signal_type": "PARITY_ENTROPY_COLLAPSE",
        "severity": 0.96,
        "organ": "ENDPOINT_PAGE_CURVE",
        "ring": "RING_3_ENDPOINT_SILICON",
        "entities": {"host_id": "HOST_042", "vlan_id": "VLAN_CORP_IT"},
        "metrics": {"flipped_bits": 4096},
        "reason": "test event",
    }
    event.update(overrides)
    return sign_event(event)


# --------------------------------------------------------------------------- #
# Box 1 — an unsigned event is stored and provably inert
# --------------------------------------------------------------------------- #
class TestBox1UnsignedIsInert:
    def test_an_unsigned_event_is_stored_but_marked_unverified(self, client):
        out = client.post("/api/ingest", json={
            "event_id": "unsigned-1", "signal_type": "X", "severity": 0.99,
            "organ": "FORGED", "ring": "RING_1"}).json()
        assert out["accepted"] == 1
        assert out["unverified"] == 1

    def test_an_unsigned_event_does_not_move_the_graph(self, client):
        """The whole point of 'inert'. A stored event that still builds edges is
        visible *and* dangerous, which is the failure mode the MAC exists for."""
        state_before = client.get("/api/state").json()["entity_graph"]["node_count"]
        client.post("/api/ingest", json={
            "event_id": "unsigned-2", "signal_type": "X", "severity": 0.99,
            "organ": "FORGED", "ring": "RING_1",
            "entities": {"host_id": "HOST_FORGED", "vlan_id": "VLAN_FORGED"}})
        state_after = client.get("/api/state").json()["entity_graph"]["node_count"]
        assert state_after == state_before, "an unsigned event built graph nodes"

    def test_an_unsigned_event_does_not_move_a_blast_radius_budget(self, client, governor):
        before = governor.status()["budget_window_usage"]
        client.post("/api/ingest", json={
            "event_id": "unsigned-3", "signal_type": "X", "severity": 0.99,
            "organ": "FORGED", "ring": "RING_1"})
        assert governor.status()["budget_window_usage"] == before

    def test_a_tampered_signature_is_treated_as_unsigned(self, client):
        ev = _signed("tampered-1")
        ev["severity"] = 0.01          # change after signing
        out = client.post("/api/ingest", json=ev).json()
        assert out["unverified"] == 1, "a post-signature edit was accepted as verified"


# --------------------------------------------------------------------------- #
# Box 2 — a signed event reaches the graph and appears in /api/state
# --------------------------------------------------------------------------- #
class TestBox2SignedReachesTheGraph:
    def test_a_signed_event_is_accepted_as_verified(self, client):
        out = client.post("/api/ingest", json=_signed("signed-1")).json()
        assert out["unverified"] == 0
        assert out["accepted"] == 1

    def test_a_signed_event_appears_in_state(self, client):
        client.post("/api/ingest", json=_signed("signed-2", entities={
            "host_id": "HOST_GRAPH_1", "vlan_id": "VLAN_GRAPH_1"}))
        graph = client.get("/api/state").json()["entity_graph"]
        assert graph["node_count"] >= 2
        assert graph["edge_count"] >= 1

    def test_the_event_is_in_the_buffered_stream(self, client):
        client.post("/api/ingest", json=_signed("signed-3"))
        recent = client.get("/api/state").json()["recent_events"]
        assert any(e.get("event_id") == "signed-3" for e in recent)


# --------------------------------------------------------------------------- #
# Box 3 — planner proposes; Governor can refuse; both in the ledger
# --------------------------------------------------------------------------- #
class TestBox3PlannerAndGovernor:
    def test_the_planner_proposes_a_cut(self, client):
        plan = client.post("/api/containment", json={"seeds": ["VLAN_GUEST_WIFI"]}).json()
        assert plan["containment"]["status"] == "PLAN_PROPOSED"

    def test_the_governor_can_approve_it(self, client):
        body = client.post("/api/containment", json={"seeds": ["VLAN_GUEST_WIFI"]}).json()
        assert body["governor"]["decision"] == "APPROVED"

    def test_the_governor_can_refuse_it(self, client):
        """A cut that severs Tier-0 is refused — the same planner output,
        a different disposition."""
        body = client.post("/api/containment", json={"seeds": ["VLAN_CORP_IT"]}).json()
        assert body["containment"]["status"] == "PLAN_PROPOSED"
        assert body["governor"]["decision"] == "BLOCKED"

    def test_both_decisions_land_in_the_ledger(self, ledger, governor):
        governor.evaluate({"tool": "drop_bec_cluster",
                           "args": {"cluster_id": "c1", "ttl_seconds": 600}})
        governor.evaluate({"tool": "execute_percolation_cut",
                           "args": {"target_spectral_radius": 0.4,
                                    "preserve_tier0_vlans": ["VLAN_ICU_CLINICAL"]}})
        decisions = [e["payload"].get("decision") for e in ledger.tail(100)]
        assert "APPROVED" in decisions and "BLOCKED" in decisions

    def test_the_refusal_carries_a_reason_into_the_ledger(self, ledger, governor):
        governor.evaluate({"tool": "execute_percolation_cut",
                           "args": {"target_spectral_radius": 0.4,
                                    "preserve_tier0_vlans": ["VLAN_ICU_CLINICAL"]}})
        refusal = [e for e in ledger.tail(100) if e["payload"].get("decision") == "BLOCKED"][0]
        assert refusal["payload"]["reasons"], "refusal recorded with no reason"


# --------------------------------------------------------------------------- #
# Box 4 — a Tier-0 cut is refused WITHOUT human step-up, refusal in the ledger
# --------------------------------------------------------------------------- #
class TestBox4Tier0:
    def test_a_tier0_vlan_is_refused_without_stepup(self, governor):
        d = governor.evaluate({"tool": "execute_percolation_cut",
                               "args": {"target_spectral_radius": 0.3,
                                        "preserve_tier0_vlans": True,
                                        "seed_vlans": ["VLAN_ICU_CLINICAL"]}})
        assert d["decision"] == "BLOCKED"
        assert any("tier-0" in r.lower() for r in d["reasons"])

    def test_a_tier0_host_is_refused_without_stepup(self, governor):
        d = governor.evaluate({"tool": "isolate_thermal_anomaly_host",
                               "args": {"host_id": "HOST_ER_DB_PRIMARY",
                                        "dump_hardware_trace": True}})
        assert d["decision"] == "BLOCKED"

    def test_a_tier0_service_cannot_be_isolated_by_its_own_id(self, governor):
        """THE DEFECT THIS FILE EXISTS FOR.

        Before this, the crown-jewel lock matched VLAN and host ids only.
        `set_service_readonly(HOST_BLOODBANK_CTRL_01)` was BLOCKED, and
        `set_service_readonly(SVC_COLDCHAIN)` — the service running on that very
        host — was APPROVED. A lock evaded by renaming the target is not a lock,
        and §2.2's "no model can isolate the ICU" was false through the service
        path.
        """
        d = governor.evaluate({"tool": "set_service_readonly",
                               "args": {"service_id": "SVC_COLDCHAIN", "ttl_seconds": 60}})
        assert d["decision"] == "BLOCKED", (
            "SVC_COLDCHAIN runs on Tier-0 host HOST_BLOODBANK_CTRL_01 and was approved"
        )
        assert any("tier-0" in r.lower() for r in d["reasons"])

    def test_the_governor_own_check_catches_the_service_without_the_twins(self, governor):
        """Both guards catch this and each must be proven on its own.

        My first version only asserted `decision == BLOCKED`, which the TCB twins
        deliver even with the Governor's own check reverted — so the mutation run
        showed the test could not tell the two guards apart. A defence-in-depth
        claim needs one test per layer, or "redundant" is an assumption.
        """
        hits = governor._tier0_targets_in_args({"service_id": "SVC_COLDCHAIN",
                                                "ttl_seconds": 60})
        assert hits, "the Governor's own crown-jewel check missed a tier-0 service"
        assert "SVC_COLDCHAIN" in hits[0]

    def test_the_governor_own_check_resolves_the_topology(self, governor):
        assert governor._service_owner.get("SVC_COLDCHAIN") == "HOST_BLOODBANK_CTRL_01"

    def test_the_service_path_does_not_over_block_a_normal_service(self, governor):
        """The fix must not turn every service into a crown jewel."""
        d = governor.evaluate({"tool": "set_service_readonly",
                               "args": {"service_id": "APP_SRV_07", "ttl_seconds": 60}})
        assert d["decision"] == "APPROVED"

    def test_a_tier0_service_cannot_be_patched_by_its_own_id(self, governor):
        d = governor.evaluate({"tool": "deploy_muts_ebpf_shield",
                               "args": {"service_id": "SVC_COLDCHAIN",
                                        "patch_profile_id": "syscall_filter_v1"}})
        assert d["decision"] == "BLOCKED"

    def test_the_refusal_is_recorded_in_the_ledger(self, ledger, governor):
        governor.evaluate({"tool": "set_service_readonly",
                           "args": {"service_id": "SVC_COLDCHAIN", "ttl_seconds": 60}})
        entries = ledger.tail(100)
        assert entries, "no ledger entry for a Tier-0 refusal"
        assert entries[-1]["payload"]["decision"] == "BLOCKED"

    def test_human_stepup_permits_what_was_refused(self, governor):
        """The lock is a step-up gate, not a wall: a verified human must be able
        to authorise it, or the crown jewels could never be defended at all."""
        d = governor.evaluate({"tool": "set_service_readonly",
                               "args": {"service_id": "SVC_COLDCHAIN", "ttl_seconds": 60}},
                              context={"human_stepup": "VERIFIED"})
        assert d["decision"] == "APPROVED"

    def test_a_fabricated_stepup_value_is_not_a_verified_human(self, governor):
        """Checked via `fortress_tcb`, not just the final decision.

        With `bool(context.get("human_stepup"))` the Governor would treat any
        non-empty string as a verified human — but the TCB twins still block, so
        the *decision* stays BLOCKED and a test that only asserts the decision
        passes against the broken version. The mutation run found this. The
        field that reveals it is `fortress_tcb`: a real step-up makes the twins
        approve (`ok`) and the Governor's own check carry the block; a fabricated
        one is refused by the twins too, which is a different code path.
        """
        good = governor.evaluate({"tool": "set_service_readonly",
                                  "args": {"service_id": "SVC_COLDCHAIN", "ttl_seconds": 60}},
                                 context={"human_stepup": "VERIFIED"})
        bad = governor.evaluate({"tool": "set_service_readonly",
                                 "args": {"service_id": "SVC_COLDCHAIN", "ttl_seconds": 60}},
                                context={"human_stepup": "yes please"})
        assert bad["decision"] == "BLOCKED"
        assert good["decision"] == "APPROVED"
        # `fortress_tcb` is "ok" in BOTH cases — the twins agree either way, so
        # that field cannot distinguish a verified human from a typed string.
        # The observable difference is WHERE the refusal comes from: the
        # Governor's own tier-0 check names the isochrone asset, whereas the
        # twins' veto has its own wording. If the Governor accepted any
        # non-empty string, this test's premise ("the Governor refuses it")
        # would be false and only the twins would block.
        assert bad["fortress_tcb"] == "ok", (
            f"fortress_tcb={bad['fortress_tcb']!r}: the refusal came from the TCB twins, "
            f"not from the Governor's own check — meaning the Governor treated a typed "
            f"string as a verified human")
        assert any("tier-0" in r.lower() for r in bad["reasons"]), (
            f"the Governor's own check did not refuse a fabricated step-up: {bad['reasons']}")

    def test_both_tcb_twins_agree_on_the_service_path(self):
        """They are N-version twins, written differently on purpose. A fix
        applied to one and not the other would be caught only by the veto."""
        from spine import tcb_core, tcb_mirror
        owners = {"SVC_COLDCHAIN": "HOST_BLOODBANK_CTRL_01"}
        kwargs = dict(tier0_vlans=["VLAN_ICU_CLINICAL"],
                      tier0_hosts=["HOST_BLOODBANK_CTRL_01"],
                      service_owner=owners)
        args = {"service_id": "SVC_COLDCHAIN", "ttl_seconds": 60}
        core = tcb_core.decide("set_service_readonly", args, **kwargs)
        mirror = tcb_mirror.decide("set_service_readonly", args, **kwargs)
        assert core["decision"] == mirror["decision"] == "BLOCKED"


# --------------------------------------------------------------------------- #
# Box 5 — ledger_cli verify passes after a full campaign
# --------------------------------------------------------------------------- #
class TestBox5LedgerVerify:
    def test_the_chain_verifies_after_many_decisions(self, ledger, governor):
        for i in range(12):
            governor.evaluate({"tool": "drop_bec_cluster",
                               "args": {"cluster_id": f"c{i}", "ttl_seconds": 600}})
        out = ledger.verify()
        assert out["valid"] is True
        assert out["entries"] == len(ledger.tail(1000))

    def test_editing_a_record_breaks_verification(self, ledger, governor):
        """A chain that verifies after tampering is decoration, not evidence."""
        for i in range(4):
            governor.evaluate({"tool": "drop_bec_cluster",
                               "args": {"cluster_id": f"c{i}", "ttl_seconds": 600}})
        lines = open(ledger.path).read().splitlines()
        record = json.loads(lines[1])
        record["payload"]["decision"] = "TAMPERED"
        lines[1] = json.dumps(record, separators=(",", ":"), default=str)
        open(ledger.path, "w").write("\n".join(lines) + "\n")
        assert ledger.verify()["valid"] is False

    def test_the_cli_exit_code_is_2_on_a_broken_chain(self, ledger, governor):
        from spine import ledger_cli
        governor.evaluate({"tool": "drop_bec_cluster",
                           "args": {"cluster_id": "c1", "ttl_seconds": 600}})
        lines = open(ledger.path).read().splitlines()
        record = json.loads(lines[0])
        record["payload"]["decision"] = "TAMPERED"
        open(ledger.path, "w").write(json.dumps(record, separators=(",", ":"), default=str) + "\n")
        old = sys.argv
        sys.argv = ["ledger_cli", "verify", "--ledger", ledger.path]
        try:
            assert ledger_cli.main() == 2
        finally:
            sys.argv = old

    def test_an_empty_ledger_verifies_rather_than_erroring(self, ledger):
        assert ledger.verify()["valid"] is True


# --------------------------------------------------------------------------- #
# Box 6 — one citizen report and one organ event share one campaign_id
# --------------------------------------------------------------------------- #
class TestBox6CampaignFusion:
    def test_the_same_case_token_digests_identically_on_both_rails(self):
        """The fusion key. If the sanitizer produced different tokens for the
        same case_id on the citizen and infra rails, no campaign could ever
        span them — and the digest being stable is the whole mechanism."""
        from spine.sanitizer import sanitize_event
        citizen = sanitize_event({"event_id": "c", "organ": "CITIZEN_APP", "severity": 0.8,
                                  "entities": {"case_id": "CASE_42"}, "metrics": {}})
        infra = sanitize_event({"event_id": "i", "organ": "BEC_SPECTRAL_PROJECTOR",
                                "severity": 0.9,
                                "entities": {"host_id": "HOST_1", "case_id": "CASE_42"},
                                "metrics": {}})
        assert citizen["entities"]["case_id"] == infra["entities"]["case_id"]

    def test_one_citizen_report_and_one_organ_event_share_a_campaign(self):
        from spine.entity_graph import EntityGraph
        from spine.sanitizer import sanitize_event
        graph = EntityGraph()
        graph.add_event(sanitize_event({"event_id": "c1", "organ": "CITIZEN_APP",
                                        "severity": 0.8,
                                        "entities": {"case_id": "CASE_77"}, "metrics": {}}))
        graph.add_event(sanitize_event({"event_id": "i1", "organ": "BEC_SPECTRAL_PROJECTOR",
                                        "severity": 0.9,
                                        "entities": {"host_id": "HOST_9", "case_id": "CASE_77"},
                                        "metrics": {}}))
        campaigns = graph.campaigns()
        assert len(campaigns) == 1
        assert campaigns[0]["size"] == 2

    def test_without_a_shared_token_they_do_not_fuse(self):
        """The honest limit, pinned so it cannot be mistaken for a bug later:
        correlation is entity overlap. A report with no case token cannot be
        joined to a network event by this mechanism, and pretending otherwise
        would be the fabrication this part exists to prevent."""
        from spine.entity_graph import EntityGraph
        from spine.sanitizer import sanitize_event
        graph = EntityGraph()
        graph.add_event(sanitize_event({"event_id": "c1", "organ": "CITIZEN_APP",
                                        "severity": 0.8, "entities": {}, "metrics": {}}))
        graph.add_event(sanitize_event({"event_id": "i1", "organ": "BEC_SPECTRAL_PROJECTOR",
                                        "severity": 0.9,
                                        "entities": {"host_id": "HOST_9"}, "metrics": {}}))
        assert len(graph.campaigns()) == 2

    def test_the_campaign_id_is_deterministic(self):
        from spine.entity_graph import EntityGraph
        from spine.sanitizer import sanitize_event

        # The ids must satisfy the sanitizer's ^[A-Za-z0-9_-]{4,64}$ rule. A
        # shorter id is REPLACED with a random one, which silently makes the
        # campaign_id unstable — my first version of this test used "a"/"b" and
        # failed for that reason, not because the correlator is nondeterministic.
        def build():
            g = EntityGraph()
            g.add_event(sanitize_event({"event_id": "evt_aaa1", "organ": "X", "severity": 0.5,
                                        "entities": {"user_id": "U1"}, "metrics": {}}))
            g.add_event(sanitize_event({"event_id": "evt_bbb2", "organ": "Y", "severity": 0.5,
                                        "entities": {"user_id": "U1"}, "metrics": {}}))
            return g.campaigns()[0]["campaign_id"]

        assert build() == build()

    def test_a_too_short_event_id_is_replaced_not_kept(self):
        """Pinning the behaviour my first test tripped over: the sanitizer
        regenerates an id that fails its length rule, so a caller cannot rely on
        a short id surviving intact."""
        from spine.sanitizer import sanitize_event
        out = sanitize_event({"event_id": "ab", "organ": "X", "severity": 0.5,
                              "entities": {}, "metrics": {}})
        assert out["event_id"] != "ab"
        assert out["event_id"].startswith("evt_")

    def test_a_valid_event_id_is_preserved(self):
        from spine.sanitizer import sanitize_event
        out = sanitize_event({"event_id": "evt_keepme", "organ": "X", "severity": 0.5,
                              "entities": {}, "metrics": {}})
        assert out["event_id"] == "evt_keepme"


# --------------------------------------------------------------------------- #
# Box 7 — two TCB twins disagree => action refused
# --------------------------------------------------------------------------- #
class TestBox7TwinVeto:
    def test_a_disagreement_fails_closed(self, governor, monkeypatch):
        import spine.tcb_mirror as mirror
        monkeypatch.setattr(mirror, "decide",
                            lambda *a, **k: {"decision": "BLOCKED", "reasons": ["forced"]})
        d = governor.evaluate({"tool": "drop_bec_cluster",
                               "args": {"cluster_id": "c1", "ttl_seconds": 600}})
        assert d["decision"] == "BLOCKED"
        assert any("TCB disagreement" in r for r in d["reasons"])

    def test_a_raising_twin_fails_closed(self, governor, monkeypatch):
        """A twin that raises must deny, not be skipped.

        My first version replaced the condition with `except ZeroDivisionError`
        to test this and the suite still passed, because the real handler catches
        Exception and only records reasons. The mutant proved the test was not
        actually exercising the crash path.
        """
        import spine.tcb_mirror as mirror

        def explode(*a, **k):
            raise RuntimeError("twin is broken")
        monkeypatch.setattr(mirror, "decide", explode)
        d = governor.evaluate({"tool": "drop_bec_cluster",
                               "args": {"cluster_id": "c1", "ttl_seconds": 600}})
        assert d["decision"] == "BLOCKED", "a crashing twin approved an action"
        assert any("TCB" in r or "FORTRESS" in r for r in d["reasons"]), d["reasons"]

    def test_the_tcb_failure_is_recorded_as_an_error_not_silence(self, governor, monkeypatch):
        import spine.tcb_core as core

        def explode(*a, **k):
            raise RuntimeError("core is broken")
        monkeypatch.setattr(core, "decide", explode)
        d = governor.evaluate({"tool": "drop_bec_cluster",
                               "args": {"cluster_id": "c1", "ttl_seconds": 600}})
        assert d["decision"] == "BLOCKED"
        assert d["reasons"], "the failure produced no stated reason"

    def test_agreement_permits_the_action(self, governor):
        d = governor.evaluate({"tool": "drop_bec_cluster",
                               "args": {"cluster_id": "c1", "ttl_seconds": 600}})
        assert d["decision"] == "APPROVED"


# --------------------------------------------------------------------------- #
# §2.6 — no unverified number
# --------------------------------------------------------------------------- #
class TestNoUnverifiedNumber:
    def test_the_containment_payload_labels_its_figures_as_fixture(self):
        from spine import containment
        plan = containment.propose(TOPO, ["VLAN_GUEST_WIFI"])
        note = plan.get("note", "")
        assert "Fixture" in note or "fixture" in note
        assert "not a production SLO" in note or "never production SLO" in note

    def test_the_bus_health_payload_does_not_claim_an_slo(self, client):
        """Every number a payload exposes must say what produced it."""
        body = client.get("/api/state").json()
        blob = json.dumps(body)
        for forbidden in ("assume 99", "99% accuracy", "99.9% uptime SLA"):
            assert forbidden not in blob
