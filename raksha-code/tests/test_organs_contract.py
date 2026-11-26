"""PART 4 / PHASE 1 — the BaseOrgan contract, as executable truth.

`specs/04_infra_detection_rings.md` §3 lists six rules every organ must honour.
Until Phase 1, not one of them was tested. This file makes each rule a test and
runs it against **all eight organs**, so a ninth organ cannot be added without
being held to the same contract.

What was measured before Phase 1, on `f701bfe`:

    BaseOrgan.emit(...) -> 8 keys, no signature, no reason
    emit(severity=nan)  -> accepted, severity becomes 1.0     <- NaN as MAX alarm
    emit(severity=None) -> TypeError                          <- organ crashes
    CookieFluidTurbulence / LandauerThermalAudit / MutsEbpfRepair -> no test at all

The rules are quoted from the spec so a failing test points at the promise, not
just at the code.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentinel.shields.base_organ import (BaseOrgan, coerce_severity, seal_event,
                                         sign_rpc, verify_sealed, verify_rpc)
from sentinel.shields.ring1_perimeter_identity import (BECSpectralFilter,
                                                       CookieFluidTurbulence)
from sentinel.shields.ring2_ai_defense import BraggFFTFirewall, HessianLyapunovGuard
from sentinel.shields.ring3_endpoint_silicon import LandauerThermalAudit, PageCurveTrap
from sentinel.shields.ring4_network_healing import HashimotoPercolation, MutsEbpfRepair

# The fleet. Add an organ here or it is not held to the contract.
ORGANS = [
    BECSpectralFilter,
    CookieFluidTurbulence,
    BraggFFTFirewall,
    HessianLyapunovGuard,
    PageCurveTrap,
    LandauerThermalAudit,
    HashimotoPercolation,
    MutsEbpfRepair,
]

ALL_IDS = [C.__name__ for C in ORGANS]


@pytest.fixture(params=ORGANS, ids=ALL_IDS)
def organ(request):
    return request.param()


# --------------------------------------------------------------------------- #
# Rule 1: "Inherit BaseOrgan, emit signed telemetry — unsigned events are inert"
# --------------------------------------------------------------------------- #
class TestSignedTelemetry:
    def test_every_organ_inherits_the_contract(self, organ):
        assert isinstance(organ, BaseOrgan)

    def test_a_fresh_event_is_sealed(self, organ):
        event = organ.emit("CONTRACT_PROBE", 0.5)
        assert verify_sealed(event), f"{organ.organ} emitted an unsigned event"
        assert len(event["mac"]) == 64

    def test_tampering_invalidates_the_seal(self, organ):
        event = organ.emit("CONTRACT_PROBE", 0.5)
        event["severity"] = 0.99
        assert not verify_sealed(event), "a modified event still verified"

    def test_stripping_the_seal_is_detected(self, organ):
        event = organ.emit("CONTRACT_PROBE", 0.5)
        del event["mac"]
        del event["signature"]
        assert not verify_sealed(event)

    def test_two_events_do_not_share_a_seal(self, organ):
        a = organ.emit("CONTRACT_PROBE", 0.5)
        b = organ.emit("CONTRACT_PROBE", 0.6)
        assert a["mac"] != b["mac"]


# --------------------------------------------------------------------------- #
# Rule 2: "Never perform the disruptive action itself — register an RPC"
# --------------------------------------------------------------------------- #
class TestRpcOnly:
    def test_every_organ_registers_at_least_one_governor_gated_rpc(self, organ):
        assert organ._rpc_handlers, f"{organ.organ} has no Governor-gated RPC"

    def test_an_unsigned_rpc_is_rejected(self, organ):
        tool = next(iter(organ._rpc_handlers))
        out = organ.handle_rpc({"rpc_id": "x", "tool": tool, "args": {}})
        assert out["status"] == "REJECTED"
        assert out["reason"] == "bad_signature"

    def test_a_tampered_rpc_is_rejected(self, organ):
        tool = next(iter(organ._rpc_handlers))
        env = sign_rpc(tool, {})
        env["args"] = {"host_id": "EVIL"}
        assert organ.handle_rpc(env)["status"] == "REJECTED"

    def test_a_valid_rpc_is_answered(self, organ):
        tool = next(iter(organ._rpc_handlers))
        out = organ.handle_rpc(sign_rpc(tool, {}))
        assert out["status"] == "OK"

    def test_an_unknown_tool_is_rejected_not_crashed(self, organ):
        out = organ.handle_rpc(sign_rpc("not_a_real_tool", {}))
        assert out["status"] == "REJECTED"
        assert out["reason"] == "unknown_tool"

    def test_no_organ_kills_a_process_by_default(self):
        """`page_curve_trap` can call os.kill, gated by allow_real_kill.

        §6's "[x] … rather than acting directly" is only true because that flag
        defaults to False. Phase 1 pins the default rather than the prose.
        """
        trap = PageCurveTrap()
        assert trap.allow_real_kill is False

    def test_the_kill_gate_is_documented_where_it_is_used(self):
        src = PageCurveTrap.__module__
        import inspect
        text = inspect.getsource(sys.modules[src])
        assert "os.kill" in text
        assert "allow_real_kill" in text, "the gate disappeared but the kill remained"


# --------------------------------------------------------------------------- #
# Rule 3: "Return a reason, never only a score"
# --------------------------------------------------------------------------- #
class TestReasonedEvents:
    def test_every_event_carries_a_reason(self, organ):
        event = organ.emit("CONTRACT_PROBE", 0.5)
        assert isinstance(event.get("reason"), str)
        assert event["reason"].strip(), "an empty reason is not a reason"

    def test_an_organ_supplied_reason_is_kept(self, organ):
        event = organ.emit("CONTRACT_PROBE", 0.5, reason="session 7 looked scripted")
        assert event["reason"] == "session 7 looked scripted"

    def test_junk_reason_does_not_crash_or_vanish(self, organ):
        event = organ.emit("CONTRACT_PROBE", 0.5, reason=None)
        assert event["reason"]


# --------------------------------------------------------------------------- #
# Rule 4: "Be deterministic — a demo that differs each run is not a demo"
# --------------------------------------------------------------------------- #
def _strip_volatile(event):
    return {k: v for k, v in event.items()
            if k not in ("event_id", "timestamp_utc", "mac", "signature")}


class TestDeterministic:
    def test_emit_is_deterministic(self, organ):
        a = [_strip_volatile(organ.emit("CONTRACT_PROBE", 0.4)) for _ in range(3)]
        assert a[0] == a[1] == a[2]

    def test_the_mac_is_deterministic_for_identical_bodies(self):
        body = {"ring": "R", "organ": "O", "severity": 0.5}
        assert seal_event(body)["mac"] == seal_event(body)["mac"]

    def test_organs_produce_stable_verdicts_on_identical_input(self):
        """The organ-level version of the same promise.

        Each organ is driven twice with the same input and must agree on the
        decision, not merely on the event shape.
        """
        # Organ 1: identical session matrix
        rng = np.random.default_rng(11)
        X = rng.normal(0, 1.0, size=(60, 8))
        a = BECSpectralFilter().analyze(X)
        b = BECSpectralFilter().analyze(X)
        assert a["condensation_ratio"] == b["condensation_ratio"]
        assert a["is_rank1_botnet"] == b["is_rank1_botnet"]

        # Organ 2: identical cadence
        def run_cookie():
            o = CookieFluidTurbulence()
            return [o.observe(1.2, 400.0, 500.0)["regime"] for _ in range(4)]
        assert run_cookie() == run_cookie()

        # Organ 8: identical mismatch sequence
        def run_muts():
            o = MutsEbpfRepair()
            o.register_invariant("SVC", "bounds_check_v1")
            return [o.report_mismatch("SVC")["status"] for _ in range(2)]
        assert run_muts() == run_muts()


# --------------------------------------------------------------------------- #
# Rule 5: "Label fixture-measured numbers as fixtures"
# --------------------------------------------------------------------------- #
class TestFixtureLabelling:
    def test_no_organ_claims_a_production_slo(self, organ):
        """Numbers measured on fixtures must never be presented as production.

        There is no fixture corpus yet (Phase 4), so there is nothing to label —
        which means any claim of a production SLO would be invented. This test
        fails if an organ starts advertising one.
        """
        event = organ.emit("CONTRACT_PROBE", 0.5, metrics={"latency_ms": 0.9})
        blob = str(event).lower()
        for claim in ("production", "slo", "measured_rate", "accuracy"):
            assert claim not in blob, f"{organ.organ} advertises {claim!r}"


# --------------------------------------------------------------------------- #
# Rule 6: "Fail closed on malformed input — a crashing organ must not pass traffic"
# --------------------------------------------------------------------------- #
class TestFailClosed:
    @pytest.mark.parametrize("junk", [
        None, "x", {}, [], float("nan"), float("inf"), float("-inf"),
        -1, 2.0, 1e9, True, False, object(),
    ])
    def test_emit_never_raises_on_a_bad_severity(self, organ, junk):
        event = organ.emit("CONTRACT_PROBE", junk)
        assert 0.0 <= event["severity"] <= 1.0

    def test_nan_never_becomes_a_maximum_severity(self):
        """The defect: max(0.0, min(1.0, nan)) == 1.0 in Python.

        Both comparisons against NaN are False, so min keeps its first argument
        and max picks the larger. A corrupt float silently became the most
        severe possible event — crying wolf and hiding the corruption at once.
        """
        value, source = coerce_severity(float("nan"))
        assert value == 0.0, "NaN was promoted to an alarm"
        assert source == "nan", "the reason for the default was not recorded"

    @pytest.mark.parametrize("bad,expected_source", [
        (float("nan"), "nan"),
        (float("inf"), "infinite"),
        (float("-inf"), "infinite"),
        (None, "not_numeric"),
        ("not a number", "not_numeric"),
        ({}, "not_numeric"),
        ([], "not_numeric"),
    ])
    def test_unusable_severities_are_quiet_and_explained(self, bad, expected_source):
        value, source = coerce_severity(bad)
        assert value == 0.0
        assert source == expected_source

    def test_usable_severities_are_clamped_not_invented(self):
        assert coerce_severity(0.37) == (0.37, "supplied")
        assert coerce_severity(-5) == (0.0, "supplied")
        assert coerce_severity(9) == (1.0, "supplied")

    def test_unparseable_entities_do_not_crash_emit(self, organ):
        event = organ.emit("CONTRACT_PROBE", 0.5, entities="not a dict",
                           metrics=[1, 2, 3])
        assert isinstance(event["entities"], dict)
        assert isinstance(event["metrics"], dict)

    def test_a_broken_event_sink_does_not_stop_the_organ(self):
        def explode(_event):
            raise RuntimeError("consumer is down")
        organ = BECSpectralFilter(event_sink=explode)
        event = organ.emit("CONTRACT_PROBE", 0.5)
        assert event["severity"] == 0.5


# --------------------------------------------------------------------------- #
# The three organs that had no test at all
# --------------------------------------------------------------------------- #
class TestCookieFluidTurbulence:
    """Organ 2 had zero coverage before Phase 1."""

    def test_laminar_traffic_is_not_revoked(self):
        organ = CookieFluidTurbulence()
        out = organ.observe(rho_cadence=1.0, v_cursor=200.0, l_nav=500.0)
        assert out["regime"] == "laminar"
        assert "action" not in out
        assert organ.drain_events() == []

    def test_a_replayed_cookie_reads_turbulent_and_emits(self):
        """A replayed cookie has no human cadence: high rate, fast cursor moves.

        Reynolds number = rho * v * L / mu. A bot inflates every term.
        """
        organ = CookieFluidTurbulence()
        out = organ.observe(rho_cadence=9.0, v_cursor=4000.0, l_nav=1200.0)
        assert out["regime"] == "turbulent"
        assert out["re_beh"] > 2300.0
        assert out["action"] == "SESSION_REVOKED_FIDO2_REQUIRED"
        events = organ.drain_events()
        assert len(events) == 1
        assert events[0]["signal_type"] == "TURBULENT_SESSION_REPLAY"

    def test_the_threshold_is_the_pipe_flow_constant(self):
        organ = CookieFluidTurbulence()
        assert organ.re_crit == 2300.0

    def test_the_transitional_band_sits_below_the_threshold(self):
        organ = CookieFluidTurbulence()
        # rho=1.0, v=600 px/s, L=1200 px -> Re = 1440, inside [1380, 2300).
        out = organ.observe(rho_cadence=1.0, v_cursor=600.0, l_nav=1200.0)
        assert 0.6 * organ.re_crit <= out["re_beh"] < organ.re_crit, out["re_beh"]
        assert out["regime"] == "transitional"
        assert "action" not in out, "transitional is a warning, not a revocation"

    def test_calibration_requires_a_real_baseline(self):
        organ = CookieFluidTurbulence()
        with pytest.raises(ValueError):
            organ.calibrate_baseline([{"rho_cadence": 1, "v_cursor": 200,
                                       "l_nav": 500}])

    def test_calibration_produces_a_finite_viscosity(self):
        organ = CookieFluidTurbulence()
        out = organ.calibrate_baseline(
            [{"rho_cadence": 1.0, "v_cursor": 200.0, "l_nav": 500.0}] * 8)
        assert np.isfinite(out["mu_baseline"])
        assert out["mu_baseline"] > 0
        assert out["n"] == 8


class TestLandauerThermalAudit:
    """Organ 6 had zero coverage before Phase 1."""

    @staticmethod
    def _benign(n=40, seed=3):
        rng = np.random.default_rng(seed)
        out = []
        for _ in range(n):
            ipc, temp = rng.uniform(1.0, 3.0), rng.uniform(45.0, 75.0)
            out.append({"ipc": float(ipc), "temp_c": float(temp),
                        "power_w": float(2.0 * ipc + 0.05 * temp + 5.0)})
        return out

    def test_audit_refuses_to_run_before_calibration(self):
        """No baseline means no prediction, which means no opinion.

        Inventing a baseline would make every first reading look anomalous.
        """
        organ = LandauerThermalAudit()
        with pytest.raises(RuntimeError):
            organ.audit(power_w=20.0, ipc=2.0, temp_c=60.0)

    def test_calibration_requires_enough_samples(self):
        organ = LandauerThermalAudit()
        with pytest.raises(ValueError):
            organ.calibrate(self._benign(5))

    def test_a_clean_host_produces_no_alarm(self):
        organ = LandauerThermalAudit()
        organ.calibrate(self._benign())
        for _ in range(8):
            out = organ.audit(power_w=float(2.0 * 2.0 + 0.05 * 60 + 5.0),
                              ipc=2.0, temp_c=60.0)
        assert out["sustained_anomaly"] is False
        assert organ.drain_events() == []

    def test_sustained_unexplained_power_raises_an_event(self):
        """The organ's whole thesis: covert work shows up as unexplained watts."""
        organ = LandauerThermalAudit()
        organ.calibrate(self._benign())
        expected = 2.0 * 2.0 + 0.05 * 60.0 + 5.0
        for _ in range(organ.sustain_samples):
            out = organ.audit(power_w=expected + 20.0, ipc=2.0, temp_c=60.0)
        assert out["sustained_anomaly"] is True
        assert out["action"] == "ISOLATE_HOST_RECOMMENDED"
        events = organ.drain_events()
        assert len(events) == 1
        assert events[0]["signal_type"] == "UNACCOUNTED_POWER_RESIDUAL"

    def test_one_spike_is_not_sustained(self):
        """Sustain is the point: a single hot sample is normal silicon."""
        organ = LandauerThermalAudit()
        organ.calibrate(self._benign())
        expected = 2.0 * 2.0 + 0.05 * 60.0 + 5.0
        out = organ.audit(power_w=expected + 40.0, ipc=2.0, temp_c=60.0)
        assert out["sustained_anomaly"] is False

    def test_the_landauer_floor_is_context_not_a_threshold(self):
        organ = LandauerThermalAudit()
        floor = organ.landauer_floor(1e9)
        assert floor > 0
        assert floor < 1e-9, "bit-erasure power is microscopic by construction"


class TestMutsEbpfRepair:
    """Organ 8 had zero coverage before Phase 1, and held a real logic bug."""

    def test_an_unknown_service_reports_no_invariant(self):
        organ = MutsEbpfRepair()
        out = organ.report_mismatch("NEVER_REGISTERED")
        assert out["status"] == "MISMATCH_NO_INVARIANT"

    def test_an_unknown_patch_profile_is_refused(self):
        organ = MutsEbpfRepair()
        with pytest.raises(ValueError):
            organ.register_invariant("SVC", "no_such_profile")

    def test_a_first_attempt_is_spliced(self):
        organ = MutsEbpfRepair()
        organ.register_invariant("SVC", "bounds_check_v1")
        out = organ.report_mismatch("SVC")
        assert out["status"] == "SHIELD_SPLICED"
        assert out["patch_profile_id"] == "bounds_check_v1"
        events = organ.drain_events()
        assert events[0]["signal_type"] == "MISMATCH_SHIELD_SPLICED"

    def test_the_second_attempt_is_genuinely_blocked(self):
        """The defect this test was written for.

        `second_attempt_blocked` was hard-coded `True` on **every** call,
        including the first. So the flag said nothing: the first mismatch and
        the second returned identical `status`, `splice_ms` and flag. The organ's
        entire thesis is that a repeat exploit fails — and the code could not
        tell a first attempt from a second.

        Now a repeat is a distinct outcome, so "the second attempt fails" is
        something the organ actually does rather than something it prints.
        """
        organ = MutsEbpfRepair()
        organ.register_invariant("SVC", "bounds_check_v1")
        first = organ.report_mismatch("SVC", "first")
        second = organ.report_mismatch("SVC", "repeat")
        assert first["status"] == "SHIELD_SPLICED"
        assert second["status"] == "ALREADY_REPAIRED"
        assert second["second_attempt_blocked"] is True
        assert first["second_attempt_blocked"] is False, \
            "the first attempt is not a 'second attempt'"
        assert second["invariant_id"] == first["invariant_id"]

    def test_the_splice_budget_can_actually_be_exceeded(self):
        """`within_budget` was unfalsifiable.

        `splice_ms` was clamped to the budget *before* being compared with it,
        so `within_budget` was True for every possible input — including a zero
        budget. A measurement that cannot fail is not a measurement.
        """
        organ = MutsEbpfRepair(splice_budget_ms=0.0)
        organ.register_invariant("SVC", "bounds_check_v1")
        out = organ.report_mismatch("SVC")
        assert out["within_budget"] is False

    def test_a_generous_budget_is_met(self):
        organ = MutsEbpfRepair(splice_budget_ms=10_000.0)
        organ.register_invariant("SVC", "bounds_check_v1")
        assert organ.report_mismatch("SVC")["within_budget"] is True

    def test_the_splice_history_records_every_call(self):
        organ = MutsEbpfRepair()
        organ.register_invariant("SVC", "bounds_check_v1")
        organ.report_mismatch("SVC")
        organ.report_mismatch("SVC")
        assert len(organ.splice_history()) == 2


# --------------------------------------------------------------------------- #
# The organ -> bus seam (Part 4, Phase 1.3)
# --------------------------------------------------------------------------- #
class TestOrganToBusSeam:
    """§3 says an unsigned event is inert and every event carries a reason.

    Both claims are about what the *Commander* receives, not about what the organ
    returns. Found by running the real bus rather than reading the organ:

        organ.emit(...)                              -> 12 keys, reason present
        sanitize_event(sign_event(organ.emit(...)))  -> 8 keys, reason GONE

    `sanitize_event` whitelists its output, so every field it does not name is
    deleted. `reason` was not named. The contract survived the organ and died in
    the sanitiser — the one place a SOC analyst's explanation has to get through.
    """

    @staticmethod
    def _bus_event(organ, signal="CONTRACT_PROBE", severity=0.5, reason=None):
        from spine.sanitizer import sanitize_event
        from spine.telemetry_mac import sign_event
        event = organ.emit(signal, severity, reason=reason)
        return event, sanitize_event(sign_event(dict(event)))

    def test_the_reason_survives_the_sanitiser(self):
        event, clean = self._bus_event(BECSpectralFilter(), reason="session 7 was scripted")
        assert event["reason"] == "session 7 was scripted"
        assert clean["reason"] == "session 7 was scripted", \
            "the reason was deleted between the organ and the Commander"

    def test_the_severity_source_survives_the_sanitiser(self):
        from sentinel.shields.base_organ import coerce_severity
        event, clean = self._bus_event(BECSpectralFilter(), severity=0.4)
        assert clean["severity_source"] == "supplied"

    def test_a_nan_reason_travel_reaches_the_bus_as_zero(self):
        """The Phase 1 fix must hold end to end, not just at the organ."""
        _, clean = self._bus_event(BECSpectralFilter(), severity=float("nan"))
        assert clean["severity"] == 0.0
        assert clean["severity_source"] == "nan"

    def test_a_reason_cannot_carry_control_characters_into_the_feed(self):
        """Reasons are written by the organ, but an organ may quote input.

        The sanitiser strips anything non-printable and bounds the length, so a
        crafted string cannot smuggle terminal escapes or megabytes into a SOC
        dashboard.
        """
        from spine.sanitizer import _clean_reason
        assert _clean_reason("evil\x00\x07text") == "evil text"
        assert "\n" not in _clean_reason("two\nlines")
        assert len(_clean_reason("x" * 5000)) <= 240

    def test_every_organ_reason_reaches_the_bus(self, organ):
        from spine.sanitizer import sanitize_event
        from spine.telemetry_mac import sign_event
        event = organ.emit("CONTRACT_PROBE", 0.5)
        clean = sanitize_event(sign_event(dict(event)))
        assert clean.get("reason"), f"{organ.organ}'s reason was lost in transit"

    def test_the_bus_still_re_signs_in_process_by_design(self):
        """A documented decision, asserted so it cannot change silently.

        `spine/telemetry_mac.py` states plainly: "inside one process this is an
        integrity tag, not a boundary; the boundary is created when the bus runs
        as a separate UID". `ingest_trusted` therefore re-signs, and a stripped
        event still verifies. That is intentional — calling it a security hole
        would be wrong, and pretending it is a boundary would be worse. This test
        pins the behaviour and records why.
        """
        import asyncio
        from spine.bus import create_app
        app = create_app()
        organ = BECSpectralFilter()
        stripped = {k: v for k, v in organ.emit("CONTRACT_PROBE", 0.5).items()
                    if k not in ("mac", "signature")}
        out = asyncio.run(app.state_ingest_trusted(stripped))
        assert out["verified"] is True, (
            "in-process ingest stopped re-signing; if this is now a real boundary, "
            "update spine/telemetry_mac.py's docstring — do not just flip this test")
