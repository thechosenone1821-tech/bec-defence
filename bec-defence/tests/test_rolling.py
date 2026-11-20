"""Regression tests for the rolling CUSUM monitor end-to-end."""

import numpy as np

from engines.spectral import SpectralCondensationDetector, RollingSpectralMonitor


def test_no_alarm_before_attack_window():
    rng = np.random.default_rng(42)
    det = SpectralCondensationDetector()
    det.fit_baseline(rng.normal(0, 1, size=(50000, 8)))
    roller = RollingSpectralMonitor(
        det, window=500, check_every=25, drift=0.1, alarm_h=0.5
    )
    weak_template = rng.normal(0, 1, size=8) * 0.83
    alarms_before = 0
    for i in range(1500):
        feats = rng.normal(0, 1, size=8)
        a = roller.add_session(feats)
        if a is not None:
            alarms_before += 1
    # We do not require alarms_before == 0 strictly (CUSUM may fire on a
    # random benign elevation); we require it is small.
    assert alarms_before <= 2, f"{alarms_before} alarms before attack window"


def test_at_least_one_alarm_during_persistent_attack():
    rng = np.random.default_rng(42)
    det = SpectralCondensationDetector()
    det.fit_baseline(rng.normal(0, 1, size=(50000, 8)))
    roller = RollingSpectralMonitor(
        det, window=500, check_every=25, drift=0.1, alarm_h=0.5
    )
    weak_template = rng.normal(0, 1, size=8) * 0.83
    alarms = 0
    for i in range(3000):
        if 1500 <= i < 2500 and rng.random() < 0.10:
            feats = weak_template + rng.normal(0, 0.25, size=8)
        else:
            feats = rng.normal(0, 1, size=8)
        a = roller.add_session(feats)
        if a is not None:
            alarms += 1
    assert alarms >= 1, "expected at least one CUSUM alarm during the attack window"


def test_cusum_block_present_on_alarm():
    rng = np.random.default_rng(7)
    det = SpectralCondensationDetector()
    det.fit_baseline(rng.normal(0, 1, size=(50000, 8)))
    roller = RollingSpectralMonitor(
        det, window=500, check_every=10, drift=0.01, alarm_h=0.05
    )
    template = rng.normal(0, 1, size=8) * 1.5
    alarm = None
    for _ in range(1000):
        a = roller.add_session(template + rng.normal(0, 0.25, size=8))
        if a is not None:
            alarm = a
            break
    assert alarm is not None
    assert "cusum" in alarm
    assert "increment" in alarm["cusum"]
    # The increment is the (lambda_max - null - drift) value and can be
    # negative -- that's the decay fix.
