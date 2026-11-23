import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citizen.voiceguard import score_voice

def _tone(freq, seconds=2.0, sr=16000):
    t = np.arange(int(seconds * sr)) / sr
    return (0.7 * np.sin(2 * np.pi * freq * t)).astype(np.float32)

def test_silence_verdict():
    assert score_voice(np.zeros(32000, dtype=np.float32))["verdict"] == "SILENT"

def test_pure_tone_is_signal_anomaly_not_clone_claim():
    result = score_voice(_tone(440))
    assert result["verdict"] == "SUSPICIOUS"
    assert result["features"]["spectral_flatness"] < 0.05
    assert "not evidence" in result["reason"]

def test_noise_never_becomes_likely_genuine_without_model():
    noise = np.random.default_rng(7).uniform(-0.8, 0.8, 32000).astype(np.float32)
    assert score_voice(noise)["verdict"] in {"SUSPICIOUS", "INCONCLUSIVE"}

def test_insufficient_samples():
    assert score_voice([0.1, 0.2])["verdict"] == "INCONCLUSIVE"

def test_non_finite_payload_rejected():
    assert score_voice([float("inf")] * 1000)["verdict"] == "INCONCLUSIVE"
    assert score_voice([float("nan")] * 1000)["verdict"] == "INCONCLUSIVE"

def test_mono_only_and_two_second_limit():
    assert score_voice(np.zeros((2, 4096), dtype=np.float32))["verdict"] == "INCONCLUSIVE"
    assert score_voice(np.zeros(32001, dtype=np.float32))["verdict"] == "INCONCLUSIVE"

def test_sample_rate_must_be_16khz():
    result = score_voice(_tone(220), sample_rate=44100)
    assert result["verdict"] == "INCONCLUSIVE"
    assert "16000" in result["reason"]

def test_lfcc_and_lpcc_are_present_and_finite():
    result = score_voice(_tone(330))
    for key in ("lfcc_mean", "lfcc_std", "lpcc_mean"):
        values = np.asarray(result["features"][key], dtype=float)
        assert values.shape == (13,)
        assert np.isfinite(values).all()

def test_fallback_does_not_claim_real_speech_is_genuine():
    t = np.arange(32000) / 16000
    speech_like = (0.20 * np.sin(2 * np.pi * 170 * t)
                   + 0.12 * np.sin(2 * np.pi * 330 * t)
                   + 0.08 * np.sin(2 * np.pi * 510 * t)).astype(np.float32)
    result = score_voice(speech_like)
    assert result["verdict"] != "LIKELY_GENUINE"
    assert result["advisory"] is True
    assert "does not verify" in result["disclaimer"]

def test_deterministic_output():
    samples = _tone(330)
    assert score_voice(samples) == score_voice(samples)
