"""Part 4 Phase 7 — organ fleet operations.

Three claims, each of which is easy to make and hard to earn:

* **Liveness.** The fleet can tell a live organ from a dead one, and does not
  call a never-observed organ healthy.
* **Silence is not safety.** An organ that emits nothing because it is blind and
  an organ that emits nothing because there is nothing to report are the *same
  observation*. Only a known-positive canary separates them.
* **The kill switch is an actuator, not a policy.** It cannot be pulled by the
  AI path, and a claimed approval is not an approval unless it is signed.
"""

from __future__ import annotations

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spine import approval_token
from spine.fleet import (DEGRADED, FAILING, HALTED, HEALTHY, SILENT, UNKNOWN,
                         OrganFleet)
from spine.organ_canary import CANARIES, run_all, run_canary


class _FakeOrgan:
    def __init__(self, name, ring="RING_TEST"):
        self.organ = name
        self.ring = ring


@pytest.fixture()
def fleet():
    return OrganFleet()


@pytest.fixture()
def now_box():
    """A clock the test controls, so 'silent' means silent rather than slow."""
    class Clock:
        t = 1000.0
        def __call__(self):
            return self.t
        def advance(self, sec):
            self.t += sec
    return Clock()


# --------------------------------------------------------------------------- #
# Liveness
# --------------------------------------------------------------------------- #
class TestLiveness:
    def test_a_fresh_fleet_claims_nothing(self, fleet):
        """The failure this prevents: a monitor that starts green."""
        fleet.register(_FakeOrgan("ORGAN_A"))
        assert fleet.snapshot()["all_healthy"] is False
        assert fleet.health("ORGAN_A")["state"] == UNKNOWN
        assert "not a health claim" in fleet.health("ORGAN_A")["reason"]

    def test_an_empty_fleet_is_not_healthy(self, fleet):
        assert fleet.snapshot()["all_healthy"] is False

    def test_an_observed_organ_becomes_healthy(self, fleet):
        fleet.register(_FakeOrgan("ORGAN_A"))
        fleet.note_call("ORGAN_A", ok=True)
        assert fleet.health("ORGAN_A")["state"] == HEALTHY
        assert fleet.snapshot()["all_healthy"] is True

    def test_an_organ_that_stops_being_seen_goes_silent(self, now_box):
        fleet = OrganFleet(silent_after_sec=60, clock=now_box)
        fleet.register(_FakeOrgan("ORGAN_A"))
        fleet.note_call("ORGAN_A", ok=True)
        now_box.advance(61)
        health = fleet.health("ORGAN_A")
        assert health["state"] == SILENT
        assert "Silence is not health" in health["reason"]

    def test_all_calls_failing_is_failing_not_degraded(self, fleet):
        fleet.register(_FakeOrgan("ORGAN_A"))
        fleet.note_call("ORGAN_A", ok=False, error="boom")
        fleet.note_call("ORGAN_A", ok=False, error="boom")
        assert fleet.health("ORGAN_A")["state"] == FAILING

    def test_some_calls_failing_is_degraded(self, fleet):
        fleet.register(_FakeOrgan("ORGAN_A"))
        fleet.note_call("ORGAN_A", ok=True)
        fleet.note_call("ORGAN_A", ok=False, error="boom")
        assert fleet.health("ORGAN_A")["state"] == DEGRADED

    def test_an_unregistered_organ_is_unknown_not_missing(self, fleet):
        h = fleet.health("ORGAN_NOWHERE")
        assert h["state"] == UNKNOWN
        assert "not registered" in h["reason"]

    def test_duplicate_registration_is_refused(self, fleet):
        fleet.register(_FakeOrgan("ORGAN_A"))
        with pytest.raises(ValueError, match="already registered"):
            fleet.register(_FakeOrgan("ORGAN_A"))

    def test_two_organs_cannot_own_the_same_tool(self, fleet):
        a, b = _FakeOrgan("ORGAN_A"), _FakeOrgan("ORGAN_B")
        fleet.register(a, tools=["the_tool"])
        fleet.register(b)
        with pytest.raises(ValueError, match="already owned"):
            fleet.register_fleet([], tool_owner={"the_tool": b})

    def test_being_fed_input_counts_as_activity(self, fleet):
        """Phase 6 showed an organ can process 600 rounds and emit nothing.
        That is activity, and the monitor must see it."""
        fleet.register(_FakeOrgan("ORGAN_A"))
        fleet.note_observation("ORGAN_A", emitted=0)
        assert fleet.health("ORGAN_A")["state"] == HEALTHY


# --------------------------------------------------------------------------- #
# Canaries — the only way to tell a quiet organ from a blind one
# --------------------------------------------------------------------------- #
class TestCanaries:
    def test_every_registered_organ_has_a_canary(self):
        from sentinel.shields.ring1_perimeter_identity import BECSpectralFilter, CookieFluidTurbulence
        from sentinel.shields.ring2_ai_defense import BraggFFTFirewall, HessianLyapunovGuard
        from sentinel.shields.ring3_endpoint_silicon import LandauerThermalAudit, PageCurveTrap
        from sentinel.shields.ring4_network_healing import HashimotoPercolation, MutsEbpfRepair
        organs = [BECSpectralFilter(), CookieFluidTurbulence(), BraggFFTFirewall(),
                  HessianLyapunovGuard(), PageCurveTrap(), LandauerThermalAudit(),
                  HashimotoPercolation(), MutsEbpfRepair()]
        missing = [o.organ for o in organs if o.organ not in CANARIES]
        assert not missing, f"no canary for {missing}"

    def test_every_canary_fires_on_a_healthy_fleet(self):
        from sentinel.shields.ring1_perimeter_identity import BECSpectralFilter, CookieFluidTurbulence
        from sentinel.shields.ring2_ai_defense import BraggFFTFirewall, HessianLyapunovGuard
        from sentinel.shields.ring3_endpoint_silicon import LandauerThermalAudit, PageCurveTrap
        from sentinel.shields.ring4_network_healing import HashimotoPercolation, MutsEbpfRepair
        organs = {o.organ: o for o in [
            BECSpectralFilter(), CookieFluidTurbulence(), BraggFFTFirewall(),
            HessianLyapunovGuard(), PageCurveTrap(), LandauerThermalAudit(),
            HashimotoPercolation(), MutsEbpfRepair()]}
        report = run_all(organs)
        assert report["blind"] == [], report["results"]
        assert report["all_detecting"] is True

    def test_a_sabotaged_organ_is_caught_and_no_counter_would_notice(self):
        """Set a threshold out of reach. Counters stay clean; the canary does not."""
        from sentinel.shields.ring1_perimeter_identity import BECSpectralFilter
        organ = BECSpectralFilter()
        organ.rank1_threshold = 99.0          # cannot ever fire
        organ.analyze([[1.0] * 5] * 40)       # looks like normal work
        assert organ.drain_events() == []      # nothing to see
        result = run_canary(organ)
        assert result.fired is False
        assert "cannot detect" in result.reason

    def test_a_canary_that_raises_is_a_failure_not_an_excuse(self):
        """A raising canary must count as BLIND, never as "inconclusive, assume ok".

        Landauer genuinely raises "calibrate() first" when uncalibrated — that is
        how I found this. The first version of this test asserted on an organ
        with no canary defined, which never reaches the exception path at all, so
        a mutant that turned a raise into a pass survived. This drives the real
        exception: `audit()` on an organ that was never calibrated.
        """
        from sentinel.shields.ring3_endpoint_silicon import LandauerThermalAudit
        organ = LandauerThermalAudit()
        # Force the raise the canary's own calibrate() step would otherwise prevent.
        def explode(_samples):
            raise RuntimeError("calibration unavailable")
        organ.calibrate = explode
        result = run_canary(organ, name="LANDAUER_THERMAL_AUDITOR")
        assert result.fired is False, "a raising canary must not report success"
        assert "raised" in result.reason
        assert "RuntimeError" in result.reason

    def test_an_organ_with_no_canary_is_blind_not_healthy(self):
        result = run_canary(_FakeOrgan("NO_SUCH_ORGAN"))
        assert result.fired is False
        assert "no canary defined" in result.reason

    def test_the_real_landauer_canary_passes_when_calibrated(self):
        from sentinel.shields.ring3_endpoint_silicon import LandauerThermalAudit
        assert run_canary(LandauerThermalAudit(), name="LANDAUER_THERMAL_AUDITOR").fired is True

    def test_halted_organs_are_excused_but_still_reported(self):
        from sentinel.shields.ring2_ai_defense import BraggFFTFirewall
        organs = {"BRAGG_FFT_FIREWALL": BraggFFTFirewall()}
        report = run_all(organs, halted={"BRAGG_FFT_FIREWALL"})
        assert report["excused"] == ["BRAGG_FFT_FIREWALL"]
        assert "halted by operator" in report["results"]["BRAGG_FFT_FIREWALL"]["reason"]
        # A halted organ that still fires means the halt did not reach this path.
        assert report["halted_but_active"] == ["BRAGG_FFT_FIREWALL"]

    def test_the_canary_does_not_leave_events_behind(self):
        """Canary alerts must not reach the telemetry stream, or operators learn
        to ignore both canaries and real alerts."""
        from sentinel.shields.ring2_ai_defense import BraggFFTFirewall
        organ = BraggFFTFirewall()
        run_canary(organ)
        assert organ.drain_events() == [], "canary left events in the organ buffer"


# --------------------------------------------------------------------------- #
# Approval tokens
# --------------------------------------------------------------------------- #
class TestApprovalTokens:
    def test_a_token_verifies_for_its_own_action_and_organ(self):
        tok = approval_token.mint("halt", "ORGAN_A", "why")
        assert approval_token.verify(tok, "halt", "ORGAN_A")["ok"] is True

    def test_a_token_cannot_be_replayed_on_another_organ(self):
        tok = approval_token.mint("halt", "ORGAN_A", "why")
        v = approval_token.verify(tok, "halt", "ORGAN_B")
        assert v["ok"] is False and "not 'ORGAN_B'" in v["reason"]

    def test_a_token_cannot_be_replayed_as_another_action(self):
        tok = approval_token.mint("halt", "ORGAN_A", "why")
        v = approval_token.verify(tok, "resume", "ORGAN_A")
        assert v["ok"] is False and "for 'halt'" in v["reason"]

    def test_a_tampered_token_fails_the_signature(self):
        tok = approval_token.mint("halt", "ORGAN_A", "why")
        forged = dict(tok, organ="ORGAN_B")
        v = approval_token.verify(forged, "halt", "ORGAN_B")
        assert v["ok"] is False and "signature" in v["reason"]

    def test_an_unsigned_token_is_refused(self):
        tok = approval_token.mint("halt", "ORGAN_A", "why")
        tok.pop("signature")
        assert approval_token.verify(tok, "halt", "ORGAN_A")["ok"] is False

    def test_an_expired_token_is_refused_with_the_age_stated(self):
        tok = approval_token.mint("halt", "ORGAN_A", "why", ttl_sec=10)
        v = approval_token.verify(tok, "halt", "ORGAN_A", now=time.time() + 3600)
        assert v["ok"] is False and "expired" in v["reason"]

    def test_a_blocked_governor_decision_cannot_mint(self):
        with pytest.raises(ValueError, match="BLOCKED"):
            approval_token.mint("halt", "ORGAN_A", "why", decision={"decision": "BLOCKED"})

    def test_an_approved_decision_can_mint(self):
        tok = approval_token.mint("halt", "ORGAN_A", "why", decision={"decision": "APPROVED"})
        assert approval_token.verify(tok, "halt", "ORGAN_A")["ok"] is True


# --------------------------------------------------------------------------- #
# Kill switch
# --------------------------------------------------------------------------- #
class TestKillSwitch:
    def test_a_halt_without_an_approval_is_refused(self, fleet):
        fleet.register(_FakeOrgan("ORGAN_A"))
        out = fleet.halt("ORGAN_A", "because", approval=None)
        assert out["status"] == "HALT_REFUSED"
        assert "no approval token" in out["reason"]
        assert fleet.is_halted("ORGAN_A") is False

    def test_a_halt_with_a_forged_approval_is_refused(self, fleet):
        fleet.register(_FakeOrgan("ORGAN_A"))
        forged = {"action": "halt", "organ": "ORGAN_A", "signature": "deadbeef"}
        out = fleet.halt("ORGAN_A", "because", approval=forged)
        assert out["status"] == "HALT_REFUSED"
        assert fleet.is_halted("ORGAN_A") is False

    def test_a_valid_approval_halts_and_reports_halted(self, fleet):
        fleet.register(_FakeOrgan("ORGAN_A"))
        tok = approval_token.mint("halt", "ORGAN_A", "why")
        out = fleet.halt("ORGAN_A", "why", approval=tok)
        assert out["status"] == "HALTED"
        assert fleet.health("ORGAN_A")["state"] == HALTED
        assert fleet.snapshot()["halted"] == ["ORGAN_A"]

    def test_a_token_is_single_use(self, fleet):
        fleet.register(_FakeOrgan("ORGAN_A"))
        fleet.register(_FakeOrgan("ORGAN_B"))
        tok = approval_token.mint("halt", "ORGAN_A", "why")
        assert fleet.halt("ORGAN_A", "why", approval=tok)["status"] == "HALTED"
        fleet.resume("ORGAN_A", "reset", approval=approval_token.mint("resume", "ORGAN_A", "reset"))
        out = fleet.halt("ORGAN_A", "again", approval=tok)
        assert out["status"] == "HALT_REFUSED"
        assert "already been used" in out["reason"]

    def test_resuming_requires_its_own_token(self, fleet):
        fleet.register(_FakeOrgan("ORGAN_A"))
        fleet.halt("ORGAN_A", "why", approval=approval_token.mint("halt", "ORGAN_A", "why"))
        out = fleet.resume("ORGAN_A", "back", approval=None)
        assert out["status"] == "RESUME_REFUSED"
        assert fleet.is_halted("ORGAN_A") is True

    def test_a_resumed_organ_returns_to_unknown_not_healthy(self, fleet):
        """Resuming does not prove the organ works — only a canary does."""
        fleet.register(_FakeOrgan("ORGAN_A"))
        fleet.halt("ORGAN_A", "why", approval=approval_token.mint("halt", "ORGAN_A", "why"))
        fleet.resume("ORGAN_A", "back", approval=approval_token.mint("resume", "ORGAN_A", "back"))
        assert fleet.health("ORGAN_A")["state"] == UNKNOWN

    def test_a_halt_must_state_a_reason(self, fleet):
        fleet.register(_FakeOrgan("ORGAN_A"))
        out = fleet.halt("ORGAN_A", "  ", approval=approval_token.mint("halt", "ORGAN_A", "x"))
        assert out["status"] == "HALT_REFUSED"
        assert "state why" in out["reason"]

    def test_halt_and_resume_are_recorded(self, fleet):
        fleet.register(_FakeOrgan("ORGAN_A"))
        fleet.halt("ORGAN_A", "why", approval=approval_token.mint("halt", "ORGAN_A", "why"))
        fleet.resume("ORGAN_A", "back", approval=approval_token.mint("resume", "ORGAN_A", "back"))
        actions = [h["action"] for h in fleet.history()]
        assert actions == ["HALT", "RESUME"]
        assert all("approval_id" in h for h in fleet.history())

    def test_halting_an_unknown_organ_is_refused(self, fleet):
        out = fleet.halt("ORGAN_NOPE", "why", approval=approval_token.mint("halt", "ORGAN_NOPE", "w"))
        assert out["status"] == "HALT_REFUSED"
        assert "unknown organ" in out["reason"]


# --------------------------------------------------------------------------- #
# The bus wiring
# --------------------------------------------------------------------------- #
class TestBusWiring:
    def test_the_executor_exposes_a_fleet_with_all_eight_organs(self):
        from spine.bus import _try_organ_executor
        executor, mode = _try_organ_executor()
        assert mode == "organ"
        fleet = executor.fleet
        assert len(fleet.names()) == 8

    def test_a_halted_organ_refuses_work_over_the_rpc_path(self):
        from spine.bus import _try_organ_executor
        executor, _ = _try_organ_executor()
        executor.fleet.halt("BRAGG_FFT_FIREWALL", "test",
                            approval=approval_token.mint("halt", "BRAGG_FFT_FIREWALL", "t"))
        out = executor("quarantine_ai_document", {"doc_hash": "abc", "agent_id": "a"})
        assert out["status"] == "ORGAN_HALTED"
        assert "kill switch pulled" in out["reason"]

    def test_an_organ_call_is_recorded_as_activity(self):
        from spine.bus import _try_organ_executor
        executor, _ = _try_organ_executor()
        before = executor.fleet.health("BRAGG_FFT_FIREWALL")["calls"]
        executor("quarantine_ai_document", {"doc_hash": "abc", "agent_id": "a"})
        after = executor.fleet.health("BRAGG_FFT_FIREWALL")["calls"]
        assert after == before + 1

    def test_the_governor_blocks_the_ai_path_from_disabling_an_organ(self):
        """A kill switch the AI can pull is a kill switch an attacker can pull.
        The 10-tool schema lock must refuse `disable_organ`."""
        from spine.governor import PolicyEngine
        gov = PolicyEngine(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "spine", "config", "policy.yaml"))
        decision = gov.evaluate({"tool": "disable_organ", "args": {"organ": "BRAGG_FFT_FIREWALL"}})
        assert decision["decision"] == "BLOCKED"
        assert any("allowlist" in r for r in decision["reasons"])

    def test_the_fleet_endpoints_exist(self):
        from spine.bus import create_app
        policy = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "spine", "config", "policy.yaml")
        topology = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "spine", "config", "company_topology.json")
        app = create_app(policy_path=policy, topology_path=topology)
        paths = {r.path for r in app.routes if hasattr(r, "path")}
        for expected in ("/api/fleet", "/api/fleet/canary",
                         "/api/fleet/{organ}/halt", "/api/fleet/{organ}/resume",
                         "/api/fleet/history"):
            assert expected in paths, f"{expected} missing"

    def test_fleet_organs_is_keyed_by_organ_name_not_tool(self):
        """The bug this pins: `owned` is keyed by tool, and passing it directly
        made every organ lookup miss and the canary endpoint report 'unavailable'
        instead of failing."""
        from spine.bus import _try_organ_executor
        executor, _ = _try_organ_executor()
        keys = set(executor.fleet_organs)
        assert keys == set(executor.fleet.names())
        assert "quarantine_ai_document" not in keys
