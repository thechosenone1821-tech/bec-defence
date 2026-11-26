"""PART 4 / PHASE 2 — Organ 1, end to end.

Phase 2's deliverable from `specs/04_infra_detection_rings.md`:

    Organ 1 through the real bus -> sanitizer -> Commander, with a signed event
    and a Governor-gated RPC round trip.

Every test here drives the *real* components in the *real* order. Nothing is
stubbed except the SLM (which is unreachable by design and falls back to the
deterministic rule engine), because a seam test that stubs the seam proves
nothing.

The defect this phase was written to fix:

    executor("drop_bec_cluster", {...})  -> CLUSTER_DROPPED   (no signature)
    organ.handle_rpc(unsigned)           -> REJECTED bad_signature

The organ implemented a signature gate correctly, and the one code path that can
actually act skipped it. A gate is only a gate if the actuator goes through it.
"""

import os
import sys

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentinel.shields.base_organ import sign_rpc, verify_sealed
from sentinel.shields.ring1_perimeter_identity import BECSpectralFilter
from spine.bus import _build_dry_executor, _try_organ_executor, create_app
from spine.governor import PolicyEngine

POLICY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "spine", "config", "policy.yaml")


# --------------------------------------------------------------------------- #
# Fixtures: real traffic, real organs, real bus
# --------------------------------------------------------------------------- #
def botnet_matrix(n_human=300, n_bot=400, dims=16, seed=42):
    """A rank-1 botnet beside ordinary humans — Organ 1's reason for existing."""
    rng = np.random.default_rng(seed)
    humans = rng.normal(0, 1.5, size=(n_human, dims))
    direction = rng.normal(0, 1, size=dims)
    direction /= np.linalg.norm(direction)
    bots = 8.0 * direction + rng.normal(0, 0.1, size=(n_bot, dims))
    return np.vstack([humans, bots])


def benign_matrix(n=400, dims=16, seed=1234):
    return np.random.default_rng(seed).normal(0, 1.4, size=(n, dims))


@pytest.fixture()
def organ():
    return BECSpectralFilter()


@pytest.fixture()
def app():
    return create_app()


# --------------------------------------------------------------------------- #
# Leg 1: Organ 1 produces a signed, reasoned event from real traffic
# --------------------------------------------------------------------------- #
class TestLegOneTheOrgan:
    def test_real_botnet_traffic_is_flagged(self, organ):
        out = organ.analyze(botnet_matrix())
        assert out["is_rank1_botnet"] is True
        assert out["condensation_ratio"] > 0.72

    def test_benign_traffic_is_not_flagged(self, organ):
        out = organ.analyze(benign_matrix())
        assert out["is_rank1_botnet"] is False

    def test_a_flag_emits_exactly_one_sealed_event(self, organ):
        organ.analyze(botnet_matrix())
        events = organ.drain_events()
        assert len(events) == 1
        assert verify_sealed(events[0])
        assert events[0]["organ"] == "BEC_SPECTRAL_PROJECTOR"
        assert events[0]["ring"] == "RING_1_PERIMETER_IDENTITY"

    def test_benign_traffic_emits_nothing(self, organ):
        organ.analyze(benign_matrix())
        assert organ.drain_events() == []

    def test_the_organ_carries_its_own_reason(self, organ):
        """Phase 1 gave every event a reason; Phase 2 checks the organ's is useful.

        A generic "something happened" is technically a reason and practically
        useless. This asserts the numbers that drove the decision are in it.
        """
        verdict = organ.analyze(botnet_matrix())
        reason = organ.drain_events()[0]["reason"]
        # The generic fallback satisfied the first version of this test:
        # "reported RANK1_CONDENSATION_DETECTED at severity 0.773" contains the
        # word "condensation", so the assertion passed while the reason said
        # nothing an analyst could use. Require the measurement itself.
        assert f"{verdict['condensation_ratio']:.3f}" in reason, reason
        assert "threshold" in reason.lower(), reason
        assert str(len(verdict["excised_session_indices"])) in reason, reason

    def test_the_event_severity_reflects_the_measured_ratio(self, organ):
        verdict = organ.analyze(botnet_matrix())
        event = organ.drain_events()[0]
        assert event["severity"] == pytest.approx(min(1.0, verdict["condensation_ratio"]),
                                                  abs=1e-6)


# --------------------------------------------------------------------------- #
# Leg 2: the bus accepts it, sanitises it, and keeps the reason
# --------------------------------------------------------------------------- #
class TestLegTwoTheBus:
    def test_a_trusted_organ_event_is_verified(self, app, organ):
        import asyncio
        organ.analyze(botnet_matrix())
        event = organ.drain_events()[0]
        out = asyncio.run(app.state_ingest_trusted(dict(event)))
        assert out["verified"] is True
        assert out["signal_type"] == "RANK1_CONDENSATION_DETECTED"

    def test_the_signal_type_survives_the_sanitiser(self, app, organ):
        """The sanitiser upper-cases and pattern-checks the signal name.

        If it rewrote this one, the Commander's rule table would never match and
        Organ 1 could shout all day without anything happening.
        """
        import asyncio
        organ.analyze(botnet_matrix())
        out = asyncio.run(app.state_ingest_trusted(dict(organ.drain_events()[0])))
        assert out["signal_type"] == "RANK1_CONDENSATION_DETECTED"

    def test_the_organ_identity_survives(self, app, organ):
        import asyncio
        organ.analyze(botnet_matrix())
        out = asyncio.run(app.state_ingest_trusted(dict(organ.drain_events()[0])))
        assert out["organ"] == "BEC_SPECTRAL_PROJECTOR"
        assert out["ring"] == "RING_1_PERIMETER_IDENTITY"

    def test_the_reason_survives_end_to_end(self, app, organ):
        """Phase 1 found the sanitiser deleting `reason`; this is the e2e proof."""
        import asyncio
        organ.analyze(botnet_matrix())
        out = asyncio.run(app.state_ingest_trusted(dict(organ.drain_events()[0])))
        assert out["reason"], "the reason did not reach the bus"
        assert out["severity_source"] == "supplied"


# --------------------------------------------------------------------------- #
# Leg 3: the Commander turns the event into a proposed action
# --------------------------------------------------------------------------- #
class TestLegThreeTheCommander:
    def test_organ_1_telemetry_produces_a_bec_action(self, app, organ):
        import asyncio
        organ.analyze(botnet_matrix())
        asyncio.run(app.state_ingest_trusted(dict(organ.drain_events()[0])))
        bundle = TestClient(app).post("/api/orchestrate").json()
        tools = [a["tool"] for a in bundle["actions"]]
        assert "drop_bec_cluster" in tools, tools

    def test_the_plan_is_deterministic(self, app, organ):
        """Same telemetry in, same action out. A demo that differs each run is
        not a demo — and §3 requires determinism from the whole chain, not just
        from the organ."""
        import asyncio

        def run_once():
            a = create_app()
            o = BECSpectralFilter()
            o.analyze(botnet_matrix())
            asyncio.run(a.state_ingest_trusted(dict(o.drain_events()[0])))
            b = TestClient(a).post("/api/orchestrate").json()
            return [(x["tool"], sorted(x["args"].items())) for x in b["actions"]]

        assert run_once() == run_once()

    def test_an_unverified_event_cannot_reach_the_commander(self, app):
        """The Fortress rule, exercised through the real HTTP door.

        A forged high-severity event is accepted (it is evidence in itself) but
        must not produce a plan.
        """
        client = TestClient(app)
        client.post("/api/ingest", json=[{
            "event_id": "evt_forged01", "ring": "RING_1_PERIMETER_IDENTITY",
            "organ": "FORGED", "signal_type": "RANK1_CONDENSATION_DETECTED",
            "severity": 0.99, "entities": {"cluster_id": "CLUS_EVIL"},
        }])
        bundle = client.post("/api/orchestrate").json()
        assert bundle["status"] == "HELD_UNVERIFIED_EVIDENCE"
        assert bundle.get("actions") in (None, []) or "actions" not in bundle


# --------------------------------------------------------------------------- #
# Leg 4: the Governor gates it, and the actuator obeys the gate
# --------------------------------------------------------------------------- #
class TestLegFourTheGovernor:
    def test_a_normal_bec_cut_is_approved(self):
        g = PolicyEngine(POLICY)
        d = g.evaluate({"tool": "drop_bec_cluster",
                        "args": {"cluster_id": "CLUS_X", "ttl_seconds": 3600}})
        assert d["decision"] == "APPROVED"

    def test_a_tier0_host_is_blocked(self):
        g = PolicyEngine(POLICY)
        d = g.evaluate({"tool": "isolate_thermal_anomaly_host",
                        "args": {"host_id": "HOST_ER_DB_PRIMARY",
                                 "dump_hardware_trace": True}})
        assert d["decision"] == "BLOCKED"

    def test_an_unlisted_tool_never_reaches_an_executor(self):
        g = PolicyEngine(POLICY)
        d = g.evaluate({"tool": "rm_rf_everything", "args": {}})
        assert d["decision"] != "APPROVED"


# --------------------------------------------------------------------------- #
# Leg 5: the executor round trip — THE defect this phase fixes
# --------------------------------------------------------------------------- #
class TestLegFiveTheRpcRoundTrip:
    def test_the_executor_dispatches_through_a_signed_rpc(self):
        """Before Phase 2 the executor called `organ._rpc_drop_cluster(args)`.

        It reached into a private handler, so the signature gate the organ
        implements was never consulted: the organ rejected an unsigned call via
        `handle_rpc()` while the reachable actuator performed it anyway.

        **This test does not trust `dispatch == "signed_rpc"`.** An earlier
        version did, and a mutant that restored the exact bypass *while still
        setting the label* passed all 25 tests. Asserting a self-reported field
        verifies the label, not the mechanism. So this drives a real organ and
        observes whether `handle_rpc` was actually entered.
        """
        from spine import bus as bus_mod
        from sentinel.shields import base_organ

        seen = []
        original_handle = base_organ.BaseOrgan.handle_rpc

        def recording_handle(self, envelope):
            seen.append(envelope)
            return original_handle(self, envelope)

        # Patch the BASE class, never a subclass. Patching BECSpectralFilter
        # directly leaves a shadowing attribute on the subclass, which then hides
        # a later BaseOrgan patch — a test-ordering failure this test had on its
        # first version, and exactly the kind of cross-test coupling that makes a
        # suite pass alone and fail together.
        base_organ.BaseOrgan.handle_rpc = recording_handle
        try:
            execute, mode = bus_mod._try_organ_executor()
            assert mode == "organ"
            out = execute("drop_bec_cluster", {"cluster_id": "CLUS_X", "ttl_seconds": 10})
        finally:
            base_organ.BaseOrgan.handle_rpc = original_handle

        assert out["status"] == "CLUSTER_DROPPED"
        assert seen, "the executor never called handle_rpc: it bypassed the gate"
        assert seen[-1]["tool"] == "drop_bec_cluster"
        assert "signature" in seen[-1], "the envelope reached the organ unsigned"
        assert out["dispatch"] == "signed_rpc"
        assert out["organ"] == "BEC_SPECTRAL_PROJECTOR"

    def test_an_organ_refusal_is_surfaced_not_swallowed(self, monkeypatch):
        """If the organ rejects the call, the executor must pass the refusal on.

        A refusal reported as success is how a signature gate becomes decorative:
        the Governor approves, the organ refuses, and the SOC log says it worked.
        """
        from spine import bus as bus_mod
        from sentinel.shields.ring1_perimeter_identity import BECSpectralFilter

        from sentinel.shields import base_organ
        # Base class again: monkeypatch restores attributes it set, but an
        # attribute set on the *subclass* would shadow the base for any test that
        # runs afterwards and patches the base.
        monkeypatch.setattr(base_organ.BaseOrgan, "handle_rpc",
                            lambda self, env: {"status": "REJECTED",
                                               "reason": "bad_signature",
                                               "rpc_id": "rpc_test"})
        execute, _ = bus_mod._try_organ_executor()
        out = execute("drop_bec_cluster", {"cluster_id": "CLUS_X", "ttl_seconds": 10})
        assert out["status"] == "RPC_REJECTED"
        assert out["reason"] == "bad_signature"
        assert "CLUSTER_DROPPED" not in str(out)

    def test_the_organ_still_rejects_an_unsigned_call(self):
        """The gate is unchanged — the point is that it is now on the path."""
        organ = BECSpectralFilter()
        out = organ.handle_rpc({"rpc_id": "r1", "tool": "drop_bec_cluster", "args": {}})
        assert out["status"] == "REJECTED"
        assert out["reason"] == "bad_signature"

    def test_a_tampered_envelope_is_refused(self):
        organ = BECSpectralFilter()
        envelope = sign_rpc("drop_bec_cluster", {"cluster_id": "CLUS_A"})
        envelope["args"] = {"cluster_id": "CLUS_B"}
        assert organ.handle_rpc(envelope)["status"] == "REJECTED"

    def test_every_organ_owned_tool_goes_through_the_gate(self):
        """All eight organ tools, not just Organ 1's.

        A fix applied to one entry in a dispatch table is a fix that rots.
        """
        execute, mode = _try_organ_executor()
        organ_tools = {
            "drop_bec_cluster": {"cluster_id": "CLUS_X", "ttl_seconds": 60},
            "revoke_turbulent_session": {"session_id": "SESS_X", "user_id": "USER_X"},
            "quarantine_ai_document": {"doc_hash": "sha256:x", "agent_id": "AGENT_X"},
            "clamp_lyapunov_steering": {"model_id": "MODEL_X", "stiffness_gain": 0.5},
            "arm_page_curve_traps": {"host_id": "HOST_X", "density_level": "high"},
            "isolate_thermal_anomaly_host": {"host_id": "HOST_X", "dump_hardware_trace": True},
            "execute_percolation_cut": {"target_spectral_radius": 0.9, "preserve_tier0_vlans": True},
            "deploy_muts_ebpf_shield": {"service_id": "SVC_X", "patch_profile_id": "bounds_check_v1"},
        }
        from sentinel.shields import base_organ

        entered = []
        original = base_organ.BaseOrgan.handle_rpc

        def recording(self, envelope):
            entered.append((self.organ, envelope.get("tool"),
                            "signature" in envelope))
            return original(self, envelope)

        base_organ.BaseOrgan.handle_rpc = recording
        try:
            for tool, args in organ_tools.items():
                out = execute(tool, args)
                assert out.get("status") not in ("REJECTED", "RPC_REJECTED"), \
                    f"{tool} was refused by its own organ: {out}"
        finally:
            base_organ.BaseOrgan.handle_rpc = original

        # Every one of the eight must have gone through the gate, signed.
        assert {t for _, t, _ in entered} == set(organ_tools), \
            f"tools that bypassed the gate: {set(organ_tools) - {t for _, t, _ in entered}}"
        assert all(sig for _, _, sig in entered), \
            f"unsigned envelopes reached: {[x for x in entered if not x[2]]}"

    def test_platform_tools_do_not_claim_an_organ(self):
        """`escalate_human_stepup` has no organ behind it. It must say so rather
        than pretending to be an organ RPC."""
        execute, _ = _try_organ_executor()
        out = execute("escalate_human_stepup",
                      {"incident_id": "INC_1", "severity": 0.9, "summary": "x"})
        assert out["dispatch"] == "platform_local"
        assert "organ" not in out

    def test_the_dry_run_executor_never_impersonates_a_real_dispatch(self):
        execute, mode = _build_dry_executor()
        out = execute("drop_bec_cluster", {"cluster_id": "CLUS_X"})
        assert mode == "dry-run"
        assert out["dispatch"] == "dry_run"
        assert out["dry_run"] is True
        assert out["status"].startswith("DRY_RUN_")

    def test_an_unknown_tool_is_an_error_not_a_crash(self):
        execute, _ = _try_organ_executor()
        out = execute("totally_made_up", {})
        assert out["status"] == "ERROR"


# --------------------------------------------------------------------------- #
# The whole chain, in one test
# --------------------------------------------------------------------------- #
class TestTheWholeChain:
    def test_organ1_through_bus_commander_governor_and_back(self, app):
        """The Phase 2 deliverable, asserted end to end.

        real traffic -> Organ 1 verdict -> sealed event -> bus sanitise/verify
        -> Commander proposes -> Governor approves -> signed RPC -> organ acts.
        """
        import asyncio
        organ = BECSpectralFilter()
        verdict = organ.analyze(botnet_matrix())
        assert verdict["is_rank1_botnet"] is True

        event = organ.drain_events()[0]
        accepted = asyncio.run(app.state_ingest_trusted(dict(event)))
        assert accepted["verified"] is True
        assert accepted["reason"]

        bundle = TestClient(app).post("/api/orchestrate").json()
        assert bundle["status"] == "OK"
        tool_names = [a["tool"] for a in bundle["actions"]]
        assert "drop_bec_cluster" in tool_names
        assert all(d["decision"] == "APPROVED" for d in bundle["decisions"])

        bec_result = [r for r in bundle["results"] if r["tool"] == "drop_bec_cluster"][0]
        assert bec_result["result"]["status"] == "CLUSTER_DROPPED"
        assert bec_result["result"]["dispatch"] == "signed_rpc"
        assert bec_result["result"]["organ"] == "BEC_SPECTRAL_PROJECTOR"

    def test_the_chain_stops_at_a_blocked_governor_decision(self, app):
        """The Governor's refusal must actually prevent the action.

        Asserting the decision string is not enough: a BLOCKED decision that is
        nonetheless executed is the worst of both worlds.
        """
        import asyncio
        from spine import orchestrator as orch_mod

        organ = BECSpectralFilter()
        organ.analyze(botnet_matrix())
        asyncio.run(app.state_ingest_trusted(dict(organ.drain_events()[0])))

        original = orch_mod.Orchestrator.plan_actions

        def tier0_plan(self, events, graph_payload=None):
            plan = original(self, events, graph_payload)
            plan["actions"] = [{"tool": "isolate_thermal_anomaly_host",
                                "args": {"host_id": "HOST_ER_DB_PRIMARY",
                                         "dump_hardware_trace": True},
                                "rationale": "test: aimed at a Tier-0 host"}]
            return plan

        orch_mod.Orchestrator.plan_actions = tier0_plan
        try:
            bundle = TestClient(app).post("/api/orchestrate").json()
        finally:
            orch_mod.Orchestrator.plan_actions = original

        assert bundle["decisions"][0]["decision"] == "BLOCKED"
        # No executor result for a blocked action; the result is the refusal.
        assert bundle["results"][0]["result"]["status"] == "BLOCKED"
        assert "CLUSTER_DROPPED" not in str(bundle["results"])
        assert "HOST_ISOLATED" not in str(bundle["results"])
