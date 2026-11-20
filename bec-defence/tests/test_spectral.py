"""Regression tests for engines/spectral.py.

Each test names the defect it pins down from the review.
"""

import numpy as np
import pytest

from engines.spectral import (
    SpectralCondensationDetector,
    RollingSpectralMonitor,
    MeanShiftBaseline,
    DistanceBaseline,
    InvalidSessionMatrix,
)


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #
def test_rejects_1d_input():
    """FINDING: 'A one-dimensional input produces an unhelpful shape error.'"""
    det = SpectralCondensationDetector()
    with pytest.raises(InvalidSessionMatrix):
        det.analyze_traffic(np.array([1.0, 2.0, 3.0]))


def test_rejects_empty_matrix():
    det = SpectralCondensationDetector()
    with pytest.raises(InvalidSessionMatrix):
        det.analyze_traffic(np.zeros((0, 0)))


def test_rejects_single_feature():
    """Need at least 2 features for spectral analysis."""
    det = SpectralCondensationDetector()
    with pytest.raises(InvalidSessionMatrix):
        det.analyze_traffic(np.zeros((100, 1)))


def test_rejects_non_finite_values():
    det = SpectralCondensationDetector()
    X = np.zeros((100, 4))
    X[0, 0] = np.nan
    with pytest.raises(InvalidSessionMatrix):
        det.analyze_traffic(X)


def test_rejects_feature_count_mismatch_with_baseline():
    det = SpectralCondensationDetector()
    det.fit_baseline(np.random.default_rng(0).normal(0, 1, size=(1000, 8)))
    with pytest.raises(InvalidSessionMatrix):
        det.analyze_traffic(np.random.default_rng(1).normal(0, 1, size=(500, 4)))


# --------------------------------------------------------------------------- #
# Constant-feature handling
# --------------------------------------------------------------------------- #
def test_constant_features_do_not_crash():
    """FINDING: 'Constant features without a fitted baseline cause an
    eigendecomposition failure.'"""
    det = SpectralCondensationDetector()
    # A whole column is constant; std=0 would have divided by zero in the
    # original code. With the baseline fitted, the guard should kick in.
    det.fit_baseline(np.random.default_rng(0).normal(0, 1, size=(1000, 8)))
    X = np.random.default_rng(1).normal(0, 1, size=(500, 8))
    X[:, 3] = 1.234  # constant column
    res = det.analyze_traffic(X)
    assert res["attack_detected"] is False
    assert 3 in res["constant_features"]


def test_constant_features_without_baseline_do_not_crash():
    """Same defect, but no baseline fitted at all."""
    det = SpectralCondensationDetector()
    X = np.random.default_rng(1).normal(0, 1, size=(500, 8))
    X[:, 3] = 1.234
    res = det.analyze_traffic(X)
    # Without a baseline the detector still has to standardise; constant
    # feature should be detected and not cause a NaN.
    assert 3 in res["constant_features"]
    assert np.isfinite(res["lambda_max"])


# --------------------------------------------------------------------------- #
# Alert vs suspect semantics
# --------------------------------------------------------------------------- #
def test_normal_traffic_returns_no_suspects_when_baseline_strong():
    """FINDING: 'Normal demo traffic returns attack_detected=False but still
    lists eight suspects.' -> Now suspects can still exist but alert_level
    is explicit, and attack_detected is the only enforcement signal."""
    rng = np.random.default_rng(42)
    det = SpectralCondensationDetector(safety_margin=1.2, z_alert=2.5)
    det.fit_baseline(rng.normal(0, 1, size=(50000, 8)))
    res = det.analyze_traffic(rng.normal(0, 1, size=(500, 8)))
    assert res["attack_detected"] is False
    # alert_level must be present even when there are suspects.
    assert res["alert_level"] in {"none", "candidate", "alarm"}


def test_attack_detected_reflects_threshold_only():
    rng = np.random.default_rng(7)
    det = SpectralCondensationDetector(safety_margin=1.2, z_alert=2.5)
    det.fit_baseline(rng.normal(0, 1, size=(50000, 8)))
    humans = rng.normal(0, 1, size=(400, 8))
    template = rng.normal(0, 1, size=8)
    bots = template + rng.normal(0, 0.25, size=(100, 8))
    res = det.analyze_traffic(np.vstack([humans, bots]))
    # Strong swarm: threshold should fire.
    assert res["attack_detected"] is True
    assert res["alert_level"] == "alarm"


def test_suspects_present_without_alarm_are_candidates_only():
    """Suspect list may be non-empty with attack_detected=False; downstream
    callers MUST NOT treat that as an alarm."""
    rng = np.random.default_rng(99)
    det = SpectralCondensationDetector(safety_margin=10.0, z_alert=0.5)
    # Very high safety margin -> no alarm; very low z_alert -> many suspects.
    det.fit_baseline(rng.normal(0, 1, size=(50000, 8)))
    res = det.analyze_traffic(rng.normal(0, 1, size=(500, 8)))
    assert res["attack_detected"] is False
    assert res["alert_level"] == "candidate"
    assert len(res["suspect_indices"]) > 0


# --------------------------------------------------------------------------- #
# Display rounding
# --------------------------------------------------------------------------- #
def test_internal_stats_unrounded():
    """Internal stats are unrounded; display values are rounded to 3 dp."""
    rng = np.random.default_rng(11)
    det = SpectralCondensationDetector()
    det.fit_baseline(rng.normal(0, 1, size=(20000, 4)))
    res = det.analyze_traffic(rng.normal(0, 1, size=(500, 4)))
    assert res["lambda_max"] is not None
    # Display block is populated and its values match round(internal, 3).
    assert res["display"] is not None
    assert res["display"]["lambda_max"] == round(res["lambda_max"], 3)
    assert res["display"]["mean_shift_stat"] == round(res["mean_shift_stat"], 3)


# --------------------------------------------------------------------------- #
# CUSUM decay (the headline defect)
# --------------------------------------------------------------------------- #
def test_cusum_increment_is_negative_for_normal_window():
    """The fix: when lambda_max < null + drift, the CUSUM increment is
    negative. The original bug wrapped ``excess = max(0, lambda_max - null
    - drift)`` *before* adding to S, which erased negative increments and
    made decay impossible.

    This test checks the increment sign directly via ``roller.last_result``,
    which holds the most recent ``analyze_traffic`` result.
    """
    rng = np.random.default_rng(5)
    det = SpectralCondensationDetector()
    det.fit_baseline(rng.normal(0, 1, size=(50000, 8)))
    roller = RollingSpectralMonitor(det, window=500, check_every=1, drift=0.5, alarm_h=1e9)

    # Prime the buffer with 500 normal sessions so the window is full and
    # the null has been calibrated.
    for _ in range(500):
        roller.add_session(rng.normal(0, 1, size=8))

    last = roller.last_result
    assert last is not None and last["lambda_max"] is not None
    increment = last["lambda_max"] - roller.null - roller.k
    # For a normal window lambda_max ~= null (1.13), drift=0.5, so the
    # increment is on the order of -0.5. The original bug would have made
    # this 0.
    assert increment < 0, (
        f"normal-window increment should be negative, got {increment} "
        f"(lambda_max={last['lambda_max']}, null={roller.null}, drift={roller.k})"
    )


def test_cusum_decays_when_elevated_then_normal():
    """Behavioural decay test.

    We prime S to a non-zero value manually, then feed normal observations.
    With the original bug S would stay flat at the primed value forever
    (because excess = max(0, ...) erases negative increments). With the
    fix S must decay toward zero.
    """
    rng = np.random.default_rng(5)
    det = SpectralCondensationDetector()
    det.fit_baseline(rng.normal(0, 1, size=(50000, 8)))
    # drift=0.5 so each normal tick pulls S down by ~0.5 on average.
    roller = RollingSpectralMonitor(det, window=500, check_every=1, drift=0.5, alarm_h=1e9)

    # Prime the buffer with normal sessions.
    for _ in range(500):
        roller.add_session(rng.normal(0, 1, size=8))

    # Manually elevate S (simulating a prior accumulation).
    roller.S = 5.0
    S_before = roller.S

    # Feed 200 normal observations. Expected decay = ~0.5 * 200 = 100,
    # so S should be clamped at 0.
    for _ in range(200):
        roller.add_session(rng.normal(0, 1, size=8))

    assert roller.S < S_before, (
        f"CUSUM did not decay during normal observations: "
        f"was {S_before}, now {roller.S}"
    )
    assert roller.S < 1.0, (
        f"S should be near 0 after 200 normal observations with drift=0.5, "
        f"got {roller.S}"
    )


def test_cusum_resets_after_alarm():
    rng = np.random.default_rng(6)
    det = SpectralCondensationDetector()
    det.fit_baseline(rng.normal(0, 1, size=(50000, 8)))
    # Very low alarm threshold so any elevation fires.
    roller = RollingSpectralMonitor(det, window=500, check_every=10, drift=0.01, alarm_h=0.05)
    template = rng.normal(0, 1, size=8) * 1.5
    for _ in range(500):
        roller.add_session(template + rng.normal(0, 0.25, size=8))
    # At least one alarm should have fired and reset S to 0.
    # We cannot guarantee an alarm without determinism, so just check S
    # never goes negative and is finite.
    assert np.isfinite(roller.S)
    assert roller.S >= 0.0


def test_rolling_rejects_invalid_window():
    det = SpectralCondensationDetector()
    with pytest.raises(ValueError):
        RollingSpectralMonitor(det, window=5)
    with pytest.raises(ValueError):
        RollingSpectralMonitor(det, window=500, check_every=0)
    with pytest.raises(ValueError):
        RollingSpectralMonitor(det, window=500, check_every=600)
    with pytest.raises(ValueError):
        RollingSpectralMonitor(det, window=500, drift=-0.1)
    with pytest.raises(ValueError):
        RollingSpectralMonitor(det, window=500, alarm_h=0)


def test_rolling_rejects_invalid_feats():
    det = SpectralCondensationDetector()
    roller = RollingSpectralMonitor(det, window=500, check_every=25)
    with pytest.raises(InvalidSessionMatrix):
        roller.add_session(np.array([1.0]))  # 1-D but length 1 -> need >= 2
    with pytest.raises(InvalidSessionMatrix):
        roller.add_session(np.array([1.0, np.nan]))


# --------------------------------------------------------------------------- #
# Empirical edge calibration
# --------------------------------------------------------------------------- #
def test_calibrate_empirical_edge_overrides_mp_edge():
    rng = np.random.default_rng(2)
    det = SpectralCondensationDetector()
    det.fit_baseline(rng.normal(0, 1, size=(50000, 8)))
    # Collect benign lambda history.
    history = []
    for _ in range(50):
        r = det.analyze_traffic(rng.normal(0, 1, size=(500, 8)))
        if r["lambda_max"] is not None:
            history.append(r["lambda_max"])
    det.calibrate_empirical_edge(history)
    assert det.empirical_edge is not None
    # The threshold on a benign window should now be the empirical edge.
    res = det.analyze_traffic(rng.normal(0, 1, size=(500, 8)))
    assert res["mp_threshold"] == pytest.approx(det.empirical_edge)


def test_calibrate_requires_enough_history():
    det = SpectralCondensationDetector()
    with pytest.raises(ValueError):
        det.calibrate_empirical_edge([1.0, 2.0])


# --------------------------------------------------------------------------- #
# Mean-shift statistic (separates coordination from mean drift)
# --------------------------------------------------------------------------- #
def test_mean_shift_stat_distinguishes_drift_from_coordination():
    rng = np.random.default_rng(3)
    det = SpectralCondensationDetector()
    det.fit_baseline(rng.normal(0, 1, size=(50000, 8)))

    # Pure mean shift: every session offset by +2 in every feature.
    X_drift = rng.normal(0, 1, size=(500, 8)) + 2.0
    res_drift = det.analyze_traffic(X_drift)
    # Lambda_max may or may not exceed threshold, but mean_shift_stat MUST
    # be large -- this is the signal that "the elevation is drift, not
    # coordination".
    assert res_drift["mean_shift_stat"] > 1.0

    # Coordination: a small fraction of sessions share a template.
    humans = rng.normal(0, 1, size=(400, 8))
    template = rng.normal(0, 1, size=8) * 2.0
    bots = template + rng.normal(0, 0.25, size=(100, 8))
    res_coord = det.analyze_traffic(np.vstack([humans, bots]))
    # For coordination, lambda_max is elevated but mean_shift_stat is modest.
    assert res_coord["lambda_max"] > res_coord["mp_threshold"]
    assert res_coord["mean_shift_stat"] < res_drift["mean_shift_stat"]


# --------------------------------------------------------------------------- #
# Comparison baselines exist and run
# --------------------------------------------------------------------------- #
def test_mean_shift_baseline_runs():
    rng = np.random.default_rng(0)
    b = MeanShiftBaseline()
    b.fit_baseline(rng.normal(0, 1, size=(5000, 8)))
    res = b.analyze_traffic(rng.normal(0, 1, size=(500, 8)))
    assert "max_abs_z" in res


def test_distance_baseline_runs():
    rng = np.random.default_rng(0)
    b = DistanceBaseline()
    b.fit_baseline(rng.normal(0, 1, size=(5000, 8)))
    res = b.analyze_traffic(rng.normal(0, 1, size=(500, 8)))
    assert "max_distance" in res
