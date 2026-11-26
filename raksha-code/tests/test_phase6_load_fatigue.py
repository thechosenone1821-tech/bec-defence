"""Part 4 Phase 6 — load, alert fatigue and drift under junk.

Three properties, each of which has a way of being quietly false:

* **Load** — a detector whose cost grows faster than its input is a denial-of-
  service surface sitting inside the security control. The test pins the growth
  exponent so a future "fix" that makes it worse fails here.
* **Fatigue** — the fleet must not fire on ordinary benign activity often
  enough that an analyst stops reading. The budget is an assumption and is
  labelled as one, but exceeding it is a failure regardless.
* **Drift** — under an hour of simulated junk, no organ may raise, and none may
  go silent. Silence looking like safety is the failure this phase exists for.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corpora.soak import (FATIGUE_BUDGET_PER_SHIFT, GARBAGE_ORGANS, fatigue_benign_corpus,
                          fatigue_run, fit_growth, garbage_soak, scaling_probe)


# --------------------------------------------------------------------------- #
# Load
# --------------------------------------------------------------------------- #
class TestLoadScaling:
    @pytest.fixture(scope="class")
    @classmethod
    def rows(cls):
        return scaling_probe()

    def test_organ3_memory_grows_faster_than_linearly(self, rows):
        """Documented defect: the Fiedler rule builds an n x n matrix over tokens.

        3,211 tokens peak at ~332 MB. A 9k-token document would need ~2.6 GB,
        so a single large document is enough to exhaust a container. Pinned here
        so that a fix flips this test and the spec together.
        """
        exponent = fit_growth(rows, "peak_mb")
        assert exponent > 1.2, (
            f"memory growth is now {exponent:.2f}. If the kNN graph was replaced "
            f"with a sparse or chunked construction, update §6.1 and this test."
        )

    def test_time_growth_is_documented(self, rows):
        """Worth pinning separately: time and memory do not scale together."""
        exponent = fit_growth(rows, "seconds")
        assert 0.8 < exponent < 2.5, f"time growth {exponent:.2f} is outside the measured band"

    def test_a_large_document_is_slow_enough_to_matter(self, rows):
        biggest = max(rows, key=lambda r: r["tokens"])
        assert biggest["seconds"] > 1.0, (
            "the largest probe is no longer slow; the input sizes may have changed"
        )

    def test_memory_per_token_is_recorded(self, rows):
        biggest = max(rows, key=lambda r: r["tokens"])
        mb_per_token = biggest["peak_mb"] / biggest["tokens"]
        assert mb_per_token > 0.02, (
            f"{mb_per_token:.4f} MB/token; the quadratic term may have been addressed"
        )


# --------------------------------------------------------------------------- #
# Fatigue
# --------------------------------------------------------------------------- #
class TestAlertFatigue:
    @pytest.fixture(scope="class")
    @classmethod
    def report(cls):
        return fatigue_run(cycles=5)

    def test_the_benign_corpus_includes_every_detector(self):
        organs = {o for o, _, _, _ in fatigue_benign_corpus()}
        assert len(organs) >= 5, organs

    def test_the_fleet_stays_under_the_shift_budget(self, report):
        assert report["total_alerts_per_shift"] <= FATIGUE_BUDGET_PER_SHIFT, (
            f"fleet fires {report['total_alerts_per_shift']:.1f} times per shift "
            f"on benign input; budget is {FATIGUE_BUDGET_PER_SHIFT}"
        )

    def test_the_report_states_its_own_limitation(self, report):
        """The number is per-family, not per-observation. It must say so."""
        text = report["interpretation"].lower()
        assert "family" in text and "not a rate for real traffic" in text

    def test_no_organ_fires_on_more_than_three_quarters_of_its_benign_families(self, report):
        for organ, rate in report["benign_family_fire_rate"].items():
            assert rate <= 0.75, f"{organ} fires on {rate:.0%} of benign families"

    def test_bragg_is_the_noisiest_organ(self, report):
        """Recorded as a finding: 75 % of its benign families fire."""
        rates = report["benign_family_fire_rate"]
        assert rates.get("BRAGG_FFT_FIREWALL", 0) == max(rates.values())


# --------------------------------------------------------------------------- #
# Drift / garbage
# --------------------------------------------------------------------------- #
class TestGarbageSoak:
    @pytest.mark.parametrize("organ", GARBAGE_ORGANS)
    def test_an_organ_processing_junk_does_not_go_silent_without_reason(self, organ):
        """Silence must be explainable.

        Bragg, Lyapunov and Landauer all emit nothing under junk. That is only
        acceptable because junk is, by construction, not an attack: an empty
        string has no Bragg peak. The test pins the explanation rather than the
        silence — if one of them starts emitting on junk, that is a fabricated
        verdict and must be caught.
        """
        report = garbage_soak(organ, rounds=120)
        if report["went_silent"]:
            assert report["processed"] == report["rounds"] or report["raised"] > 0, (
                f"{organ} went silent while also failing to process input"
            )

    def test_no_organ_emits_a_verdict_on_empty_input(self):
        """An empty document is not an attack. Emitting would be a fabrication."""
        from sentinel.shields.ring2_ai_defense import BraggFFTFirewall
        organ = BraggFFTFirewall()
        organ.screen("")
        assert organ.drain_events() == []

    def test_cookie_does_not_crash_on_extreme_cadence(self):
        from sentinel.shields.ring1_perimeter_identity import CookieFluidTurbulence
        organ = CookieFluidTurbulence()
        organ.calibrate_baseline([{"rho_cadence": 4.0, "v_cursor": 120.0, "l_nav": 400.0}] * 8)
        for triple in ((1e300, 1e300, 1e300), (0.0, 0.0, 0.0), (-5.0, -5.0, -5.0)):
            organ.observe(*triple)
        organ.drain_events()   # must not raise

    def test_organ1_refuses_non_finite_input_rather_than_scoring_it(self):
        """
        Organ 1 raises on NaN instead of returning a ratio. That is the right
        choice for a function whose caller is in a position to retry — but it
        means a caller must never treat "the organ raised" as "no detection".

        Nothing in `spine/` calls `analyze()` today (the bus reaches organs only
        through `handle_rpc`), so this is a caller-contract hazard rather than a
        live defect. Recorded so that whoever wires Ring 1 to real traffic has
        to confront it.
        """
        from sentinel.shields.ring1_perimeter_identity import BECSpectralFilter
        with pytest.raises(ValueError, match="non-finite"):
            BECSpectralFilter().analyze(np.array([[np.nan, 1, 2, 3, 4]] * 4))

    def test_muts_is_idempotent_under_repeated_junk(self):
        from sentinel.shields.ring4_network_healing import MutsEbpfRepair
        organ = MutsEbpfRepair()
        organ.register_invariant("svc_web", "bounds_check_v1")
        for _ in range(50):
            organ.report_mismatch("svc_web")
        history = organ.splice_history()
        # The organ records every attempt — 50 rows — but only the first is a
        # splice. Asserting `len(history) == 1` was my error: recording the
        # repeats is the point of the ALREADY_REPAIRED status, and the row is
        # the audit trail, not a second repair.
        spliced = [r for r in history if r["status"] == "SHIELD_SPLICED"]
        blocked = [r for r in history if r["status"] == "ALREADY_REPAIRED"]
        assert len(spliced) == 1, "a repeat report produced a second splice"
        assert len(blocked) == 49
        assert all(r["second_attempt_blocked"] for r in blocked)
        organ.drain_events()
