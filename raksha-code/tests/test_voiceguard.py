import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.voiceguard import score_voice


def _tone(freq, seconds=1.0, sr=16000):
    t = np.arange(int(seconds * sr)) / sr
    return (0.7 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_silence_verdict():
    v = score_voice(np.zeros(16000, dtype=np.float32))
    assert v["verdict"] == "SILENT"


def test_pure_synthetic_tone_flagged():
    v = score_voice(_tone(440))
    assert v["verdict"] == "SUSPICIOUS"
    assert v["features"]["spectral_flatness"] < 0.05


def test_noise_verdict_and_engine_label():
    rng = np.random.default_rng(7)
    v = score_voice(rng.uniform(-0.8, 0.8, 16000).astype(np.float32))
    assert v["verdict"] in {"SUSPICIOUS", "INCONCLUSIVE"}
    assert "spectral_fallback_v0" in v["engine"]
    assert "NOT a trained" in v["engine"]


def test_insufficient_samples():
    assert score_voice([0.1, 0.2])["verdict"] == "INCONCLUSIVE"


def test_invalid_payload_rejected_safe():
    bad = [float("inf")] * 1000
    assert score_voice(bad)["verdict"] == "INCONCLUSIVE"


def test_deterministic():
    a = _tone(330)
    assert score_voice(a) == score_voice(a)
