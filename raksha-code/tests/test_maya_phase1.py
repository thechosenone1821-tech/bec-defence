"""MAYA / VoiceGuard — Phase 1 tests: contract, frontend features, reasons.

Phase 1 exit criteria (VOICEGUARD_ROADMAP.md §2):
  * every legacy contract key still present and meaningful
  * feature extraction fast enough for a phone (< 5 ms for 1 s of audio)
  * every reason code reachable and boundary-tested
  * NaN/Inf can never leak into a JSON response or break determinism
  * LIKELY_SYNTHETIC is unreachable without a trained model
"""

import json
import math
import os
import sys
import time

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.voiceguard import (CONTRACT_VERSION, FEATURES_VERSION, VERDICTS,
                                engine_label, evaluate_reasons, extract,
                                max_verdict, may_claim_clone_detection,
                                score_voice, severity_rank, vector_for_model)
from citizen.voiceguard import contract as C
from citizen.voiceguard import features as F
from citizen.voiceguard import reasons as R

SR = 16000


# --------------------------------------------------------------------------- #
# Signal builders
# --------------------------------------------------------------------------- #
def tone(freq=440.0, seconds=1.0, sr=SR, amp=0.7):
    t = np.arange(int(seconds * sr)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def white_noise(seconds=1.0, sr=SR, seed=1):
    rng = np.random.default_rng(seed)
    return rng.uniform(-0.8, 0.8, int(seconds * sr)).astype(np.float32)


def human_like(seconds=2.0, sr=SR, seed=3, jitter=0.06, pauses=True):
    """Crude formant speech with jitter, breath noise and irregular pauses.

    Not real speech — just enough structure that the *production cues* differ
    from the synthetic builder below. Keeps the tests dependency-free.
    """
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    t = np.arange(n) / sr
    f0 = 120.0 * (1.0 + jitter * np.sin(2 * np.pi * 0.7 * t)
                  + 0.03 * rng.standard_normal(n).cumsum() / np.sqrt(n))
    phase = 2 * np.pi * np.cumsum(f0) / sr
    sig = (np.sin(phase) + 0.5 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase))
    sig *= (1.0 + 0.3 * np.sin(2 * np.pi * 3.1 * t))          # amplitude wobble
    sig += 0.02 * rng.standard_normal(n)                      # breath noise
    if pauses:
        for start, dur in [(0.5, 0.05), (1.1, 0.13), (1.6, 0.09)]:
            a, b = int(start * sr), int((start + dur) * sr)
            sig[a:b] *= 0.01
    return (0.6 * sig / (np.max(np.abs(sig)) + 1e-9)).astype(np.float32)


def synthetic_speech(seconds=2.0, sr=SR):
    """Machine-regular 'speech': fixed F0, no jitter, no breath, even gaps."""
    n = int(seconds * sr)
    t = np.arange(n) / sr
    f0 = 150.0
    phase = 2 * np.pi * f0 * t
    sig = np.sin(phase) + 0.4 * np.sin(2 * phase) + 0.15 * np.sin(3 * phase)
    env = np.ones(n)
    for start in (0.5, 1.0, 1.5):                 # identical gaps, identical length
        a, b = int(start * sr), int((start + 0.1) * sr)
        env[a:b] = 0.0
    return (0.6 * sig * env).astype(np.float32)


# --------------------------------------------------------------------------- #
# 1. Contract surface
# --------------------------------------------------------------------------- #
class TestContract:
    def test_version_is_pinned(self):
        assert CONTRACT_VERSION == "voiceguard-contract-v1"
        assert FEATURES_VERSION.startswith("maya-features-")

    def test_all_documented_verdicts_exist(self):
        assert set(VERDICTS) == {"SILENT", "INCONCLUSIVE", "SUSPICIOUS",
                                 "LIKELY_SYNTHETIC", "ERROR"}

    def test_severity_ordering_is_monotonic(self):
        ordered = ["ERROR", "SILENT", "INCONCLUSIVE", "SUSPICIOUS", "LIKELY_SYNTHETIC"]
        ranks = [severity_rank(v) for v in ordered]
        assert ranks == sorted(ranks)

    def test_unknown_verdict_does_not_rank_high(self):
        assert severity_rank("NOT_A_VERDICT") == 0

    def test_max_verdict_picks_worst(self):
        assert max_verdict(["SILENT", "SUSPICIOUS", "INCONCLUSIVE"]) == "SUSPICIOUS"

    def test_max_verdict_of_empty_is_inconclusive(self):
        assert max_verdict([]) == "INCONCLUSIVE"

    def test_reason_builder_shape(self):
        r = C.reason(C.R_MONOTONE_PITCH, cv=0.01)
        assert r == {"code": "MONOTONE_PITCH", "params": {"cv": 0.01}}

    def test_reason_codes_are_unique_constants(self):
        codes = [v for k, v in vars(C).items() if k.startswith("R_")]
        assert len(codes) == len(set(codes))
        assert all(isinstance(c, str) for c in codes)


# --------------------------------------------------------------------------- #
# 2. The honesty gate — the most important tests in the file
# --------------------------------------------------------------------------- #
class TestHonestyGate:
    def test_cannot_claim_clone_detection_without_measured_model(self):
        assert may_claim_clone_detection() is False

    def test_engine_label_always_contains_honesty_clause(self):
        label = engine_label()
        assert "NOT a trained" in label

    def test_engine_label_with_unmeasured_model_still_hedges(self):
        label = engine_label("maya-v1")
        assert "SYNTHETIC" in label and "UNMEASURED" in label
        assert "NOT a validated" in label

    def test_phase1_model_gate_was_closed(self):
        """Phase 1 shipped with no model. Phase 3 added one, so the *gate
        constants* are what this test pins — not the live behaviour, which
        Phase 3 legitimately changed (see test_maya_phase3.py). The invariant
        that survives every phase: claiming clone detection needs a model AND
        real-world measurement.
        """
        assert may_claim_clone_detection() is False
        assert "NOT a validated" in engine_label("maya-lr-v1")

    def test_silence_never_asks_the_model(self):
        """Phase-3 regression: silence once scored P(spoof)=0.94 and produced
        'this is probably an AI-generated voice' for a clip of no speech."""
        v = score_voice(np.zeros(SR, dtype=np.float32))
        assert v["verdict"] == "SILENT"
        assert v["model"] is None
        assert "SILENT_AUDIO" in {r["code"] for r in v["reasons"]}

    def test_unjudgeable_input_never_asks_the_model(self):
        for clip in ([0.1, 0.2], [float("inf")] * 1000):
            v = score_voice(clip)
            assert v["model"] is None
            assert v["verdict"] == "INCONCLUSIVE"


# --------------------------------------------------------------------------- #
# 3. Frontend features
# --------------------------------------------------------------------------- #
class TestFeatures:
    def test_frame_count_matches_formula(self):
        x = tone(seconds=1.0)
        frames = F.frame_signal(x, F.WIN, F.HOP)
        expected = 1 + (x.size - F.WIN) // F.HOP
        assert frames.shape == (expected, F.WIN)

    def test_feature_matrix_is_rectangular_and_versioned(self):
        out = extract(human_like(seconds=1.5))
        assert out["matrix"].ndim == 2
        assert out["matrix"].shape[1] == len(out["dims"])
        assert out["matrix"].shape[1] == F.N_LFCC * 2 + F.N_MFCC * 2
        assert out["version"] == FEATURES_VERSION

    def test_mel_filterbank_is_stable_and_shaped(self):
        fb = F.mel_filterbank()
        assert fb.shape == (F.N_MELS, F.N_FFT // 2 + 1)
        assert np.all(fb >= 0)
        assert np.isfinite(fb).all()

    def test_dct_matrix_is_orthonormal(self):
        m = F._dct_matrix(20, 20)
        assert np.allclose(m @ m.T, np.eye(20), atol=1e-9)

    def test_pitch_of_known_tone_is_accurate(self):
        """A 220 Hz sawtooth-ish tone must be measured near 220 Hz."""
        t = np.arange(SR) / SR
        sig = np.zeros(SR, dtype=np.float32)
        for h in range(1, 6):
            sig += (0.5 / h) * np.sin(2 * np.pi * 220 * h * t)
        f0 = F.f0_track(sig.astype(np.float32))
        finite = f0[np.isfinite(f0)]
        assert finite.size > 0
        assert abs(float(np.median(finite)) - 220.0) < 6.0

    def test_pitch_is_nan_on_silence_not_zero(self):
        f0 = F.f0_track(np.zeros(SR, dtype=np.float32))
        assert np.all(np.isnan(f0))

    def test_harmonicity_high_for_clean_voicing(self):
        assert F.harmonicity(tone(200)) > 0.5

    def test_harmonicity_low_for_noise(self):
        assert F.harmonicity(white_noise()) < 0.5

    def test_pause_stats_detect_regular_gaps(self):
        x = synthetic_speech()
        frames = F.frame_signal(x, F.WIN, F.HOP)
        rms = np.sqrt(np.mean(frames ** 2, axis=1))
        stats = F.pause_stats(rms)
        assert stats["count"] >= 2
        assert stats["cv"] is not None and stats["cv"] < 0.2

    def test_pause_stats_on_continuous_signal_has_no_nan(self):
        frames = F.frame_signal(tone(), F.WIN, F.HOP)
        stats = F.pause_stats(np.sqrt(np.mean(frames ** 2, axis=1)))
        json.dumps(stats)             # must be JSON-safe

    @pytest.mark.parametrize("builder", [tone, white_noise, human_like, synthetic_speech])
    def test_no_non_finite_value_ever_escapes(self, builder):
        scalars = extract(builder())["scalars"]
        for k, v in scalars.items():
            if isinstance(v, float):
                assert math.isfinite(v), f"{k} leaked a non-finite value"
        json.dumps(scalars)

    def test_extraction_is_fast_enough_for_a_phone(self):
        clip = human_like(seconds=1.0)
        extract(clip)                                   # warm up
        t0 = time.perf_counter()
        for _ in range(5):
            extract(clip)
        per_call_ms = (time.perf_counter() - t0) / 5 * 1000
        assert per_call_ms < 60.0, f"frontend too slow: {per_call_ms:.1f} ms"

    def test_model_vector_has_fixed_length(self):
        """vector_for_model is a general-purpose fixed-length embedding of the
        frontend. Phase 3's shipped classifier uses the robust scalar path
        instead (see model.ROBUST_KEYS), but this helper must stay stable for
        anything that wants the full cepstral view."""
        a = vector_for_model(human_like())
        b = vector_for_model(synthetic_speech())
        assert a.shape == b.shape
        assert a.size == len(F._model_columns(
            [f"lfcc_{i}" for i in range(F.N_LFCC)] +
            [f"lfcc_d_{i}" for i in range(F.N_LFCC)] +
            [f"mfcc_{i}" for i in range(F.N_MFCC)] +
            [f"mfcc_d_{i}" for i in range(F.N_MFCC)])) * 2

    def test_model_vector_tolerates_tiny_clip(self):
        v = vector_for_model(np.zeros(100, dtype=np.float32))
        assert v.size > 0 and np.isfinite(v).all()


# --------------------------------------------------------------------------- #
# 4. Reason rules, including boundaries
# --------------------------------------------------------------------------- #
class TestReasons:
    def test_too_short_fires(self):
        codes = {r["code"] for r in evaluate_reasons({"duration_s": 0.05})}
        assert "TOO_SHORT" in codes

    def test_silence_fires_and_short_circuits(self):
        got = evaluate_reasons({"rms": 0.0, "duration_s": 2.0})
        assert [r["code"] for r in got] == ["SILENT_AUDIO"]

    def test_clipping_fires_above_threshold(self):
        codes = {r["code"] for r in
                 evaluate_reasons({"clipped_ratio": R.CLIPPED_RATIO_MIN + 0.01})}
        assert "CLIPPED_AUDIO" in codes

    def test_clipping_silent_just_below_threshold(self):
        codes = {r["code"] for r in
                 evaluate_reasons({"clipped_ratio": R.CLIPPED_RATIO_MIN - 0.001})}
        assert "CLIPPED_AUDIO" not in codes

    def test_pure_tone_fires_inside_threshold(self):
        codes = {r["code"] for r in
                 evaluate_reasons({"spec_flatness": 0.001, "spec_crest": 2.0})}
        assert "PURE_TONE" in codes

    def test_pure_tone_does_not_fire_just_outside(self):
        codes = {r["code"] for r in
                 evaluate_reasons({"spec_flatness": R.PURE_TONE_FLATNESS_MAX + 0.01,
                                   "spec_crest": 2.0})}
        assert "PURE_TONE" not in codes

    def test_white_noise_requires_both_cues(self):
        both = {r["code"] for r in
                evaluate_reasons({"spec_flatness": 0.60, "zcr": 0.48})}
        flat_only = {r["code"] for r in
                     evaluate_reasons({"spec_flatness": 0.95, "zcr": 0.05})}
        zcr_only = {r["code"] for r in
                    evaluate_reasons({"spec_flatness": 0.10, "zcr": 0.60})}
        assert "WHITE_NOISE" in both
        assert "WHITE_NOISE" not in flat_only      # a hissy sibilant, not noise
        assert "WHITE_NOISE" not in zcr_only       # tonal but zero-crossy

    def test_white_noise_regression_pre_phase1_behaviour_is_kept(self):
        """Guard: Phase 1 briefly lost this case by testing flatness alone.

        The old 5-feature code flagged white noise. White noise measures
        flatness ~0.56 and ZCR ~0.50, so a flatness-only threshold of 0.85
        silently missed it. This test pins the behaviour end-to-end.
        """
        v = score_voice(white_noise())
        assert v["verdict"] == "SUSPICIOUS"
        assert "WHITE_NOISE" in {r["code"] for r in v["reasons"]}

    def test_speech_is_not_mistaken_for_noise(self):
        from citizen.voiceguard import features as F2
        s = F2.extract(human_like())["scalars"]
        codes = {r["code"] for r in evaluate_reasons(s)}
        assert "WHITE_NOISE" not in codes

    def test_monotone_pitch_fires_when_voiced(self):
        codes = {r["code"] for r in
                 evaluate_reasons({"f0_cv": 0.005, "voiced_pct": 90.0})}
        assert "MONOTONE_PITCH" in codes

    def test_monotone_pitch_silent_when_mostly_unvoiced(self):
        codes = {r["code"] for r in
                 evaluate_reasons({"f0_cv": 0.005, "voiced_pct": 20.0})}
        assert "MONOTONE_PITCH" not in codes

    def test_mechanical_pauses_need_enough_gaps(self):
        many = {r["code"] for r in
                evaluate_reasons({"n_pauses": 5, "pause_cv": 0.02})}
        few = {r["code"] for r in
               evaluate_reasons({"n_pauses": 1, "pause_cv": 0.02})}
        assert "MECHANICAL_PAUSES" in many and "MECHANICAL_PAUSES" not in few

    def test_no_breath_fires_only_with_very_stable_pitch(self):
        stable = {r["code"] for r in
                  evaluate_reasons({"harmonicity": 0.97, "f0_cv": 0.01})}
        wobbly = {r["code"] for r in
                  evaluate_reasons({"harmonicity": 0.97, "f0_cv": 0.20})}
        assert "NO_BREATH_SOUNDS" in stable
        assert "NO_BREATH_SOUNDS" not in wobbly

    def test_rules_never_fire_on_missing_features(self):
        assert evaluate_reasons({}) == []
        assert evaluate_reasons({"f0_cv": None, "harmonicity": None,
                                 "n_pauses": None, "pause_cv": None}) == []

    def test_one_production_cue_is_not_enough_to_accuse(self):
        verdict = R.verdict_from_reasons([C.reason(C.R_MONOTONE_PITCH)])
        assert verdict == C.INCONCLUSIVE

    def test_two_production_cues_escalate(self):
        verdict = R.verdict_from_reasons(
            [C.reason(C.R_MONOTONE_PITCH), C.reason(C.R_MECHANICAL_PAUSES)])
        assert verdict == C.SUSPICIOUS

    def test_degenerate_audio_escalates_alone(self):
        assert R.verdict_from_reasons([C.reason(C.R_PURE_TONE)]) == C.SUSPICIOUS

    def test_silence_beats_everything(self):
        assert R.verdict_from_reasons(
            [C.reason(C.R_PURE_TONE), C.reason(C.R_SILENT)]) == C.SILENT


# --------------------------------------------------------------------------- #
# 5. End-to-end behaviour on realistic clips
# --------------------------------------------------------------------------- #
class TestEndToEnd:
    def test_machine_regular_speech_is_flagged(self):
        """Deterministic rules alone must flag it; Phase 3's model may then
        escalate the same clip to LIKELY_SYNTHETIC."""
        v = score_voice(synthetic_speech())
        assert v["verdict"] in {"SUSPICIOUS", "LIKELY_SYNTHETIC"}
        codes = {r["code"] for r in v["reasons"]}
        assert codes & R.PRODUCTION_CODES

    def test_human_like_speech_is_usually_inconclusive_not_accused(self):
        """The safe failure mode: never confidently accuse ordinary speech."""
        v = score_voice(human_like())
        assert v["verdict"] in {"INCONCLUSIVE", "SUSPICIOUS"}

    def test_every_result_is_json_serialisable(self):
        for clip in [tone(), white_noise(), human_like(), synthetic_speech()]:
            json.dumps(score_voice(clip), allow_nan=False)

    def test_result_is_deterministic(self):
        clip = human_like()
        assert score_voice(clip) == score_voice(clip)

    def test_score_is_bounded(self):
        for clip in [tone(), white_noise(), human_like(), synthetic_speech(),
                     np.zeros(SR, dtype=np.float32)]:
            s = score_voice(clip)["score"]
            assert 0.0 <= s <= 1.0

    def test_unsupported_sample_rate_is_refused_not_guessed(self):
        v = score_voice(tone(), sr=8000)
        assert v["verdict"] == "INCONCLUSIVE"
        assert {r["code"] for r in v["reasons"]} >= {"INVALID_PAYLOAD"}

    def test_internal_error_fails_safe(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("simulated")
        monkeypatch.setattr(F, "extract", boom)
        v = score_voice(human_like())
        assert v["verdict"] == "INCONCLUSIVE"
        assert {r["code"] for r in v["reasons"]} >= {"INTERNAL_ERROR"}

    def test_audio_hash_is_stable_and_not_the_audio(self):
        v = score_voice(tone())
        assert len(v["audio_sha256"]) == 16
        assert json.dumps(v)  # no raw samples anywhere in the payload
        assert "samples" not in json.dumps(v)


# --------------------------------------------------------------------------- #
# 6. Backward compatibility with the pre-Phase-1 contract
# --------------------------------------------------------------------------- #
class TestLegacyContract:
    LEGACY_KEYS = {"verdict", "score", "engine", "reason", "features"}

    def test_all_legacy_keys_survive(self):
        assert self.LEGACY_KEYS <= set(score_voice(human_like()))

    def test_legacy_feature_keys_survive(self):
        feats = score_voice(human_like())["features"]
        assert {"rms", "zcr", "spectral_flatness", "crest_factor"} <= set(feats)

    def test_new_features_are_added_not_replacing(self):
        feats = score_voice(human_like())["features"]
        assert "f0_cv" in feats and "pause_cv" in feats and "harmonicity" in feats

    def test_reason_is_still_a_readable_string(self):
        r = score_voice(human_like())["reason"]
        assert isinstance(r, str) and len(r) > 5
