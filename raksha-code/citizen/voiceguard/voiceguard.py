"""VoiceGuard acoustic screening contract.

The default engine is a transparent signal-quality fallback. It may identify
silence, pure tones, or noise-like input; it does not identify real-world voice
clones. Real speech stays INCONCLUSIVE unless a validated anti-spoof model is
explicitly supplied. Input is mono float audio at 16 kHz, no longer than two
seconds. Audio is processed in memory only and never written by this module.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Sequence, Tuple
import numpy as np
from .features import SAMPLE_RATE, extract_features

_MAX_ABS_OK = 4.0
_MAX_SAMPLES = SAMPLE_RATE * 2
_MIN_SAMPLES = 512

def _audio_array(samples: Sequence[float]) -> Tuple[Optional[np.ndarray], str]:
    try:
        audio = np.asarray(samples if isinstance(samples, np.ndarray) else list(samples),
                           dtype=np.float32)
    except (TypeError, ValueError, OverflowError):
        return None, "audio samples must be a one-dimensional numeric sequence"
    if audio.ndim != 1:
        return None, "audio must be mono"
    if audio.size < _MIN_SAMPLES:
        return None, "insufficient samples (<512)"
    if audio.size > _MAX_SAMPLES:
        return None, "audio exceeds the two-second screening window"
    if not np.isfinite(audio).all() or float(np.max(np.abs(audio))) > _MAX_ABS_OK:
        return None, "invalid audio payload"
    return audio, ""

def _result(verdict: str, score: float, reason: str, engine: str,
            features: Optional[Dict[str, object]] = None, **extra: Any) -> Dict[str, Any]:
    return {
        "verdict": verdict, "score": round(float(score), 4), "reason": reason,
        "engine": engine, "features": features or {}, "advisory": True,
        "disclaimer": "Advisory screening only. This does not verify a caller's identity or prove that a voice is cloned.",
        **extra,
    }

def score_voice(samples: Sequence[float], sample_rate: int = SAMPLE_RATE,
                model: Any = None) -> Dict[str, Any]:
    """Screen a short mono window.

    A supplied model must expose predict_spoof_probability(audio) and return
    a finite [0, 1] probability where 1 means spoof-like. The fallback never
    classifies ordinary speech as genuine.
    """
    if sample_rate != SAMPLE_RATE:
        return _result("INCONCLUSIVE", 0.0, "unsupported sample rate; expected 16000 Hz",
                       "spectral_fallback_v1", sample_rate=sample_rate)
    audio, error = _audio_array(samples)
    if audio is None:
        return _result("INCONCLUSIVE", 0.0, error, "spectral_fallback_v1")
    feats = extract_features(audio, sample_rate)
    if float(feats["rms"]) < 1e-4:
        return _result("SILENT", 0.0, "no measurable audio energy", "spectral_fallback_v1", feats)
    if model is not None:
        try:
            probability = float(model.predict_spoof_probability(audio))
            if not np.isfinite(probability) or not 0.0 <= probability <= 1.0:
                raise ValueError("model probability must be finite and within [0, 1]")
        except Exception as exc:
            return _result("INCONCLUSIVE", 0.0,
                           "anti-spoof model unavailable or failed; no model verdict issued",
                           "model_error_fail_closed", feats, model_error=type(exc).__name__)
        if probability >= 0.80:
            verdict, reason = "SUSPICIOUS", "the configured anti-spoof model found elevated spoof-like evidence"
        elif probability <= 0.20:
            verdict, reason = "LIKELY_GENUINE", "the configured anti-spoof model found low spoof-like evidence; identity is still unverified"
        else:
            verdict, reason = "INCONCLUSIVE", "the configured anti-spoof model returned an uncertain result"
        return _result(verdict, probability, reason, "onnx_anti_spoof_v1", feats,
                       model_available=True)
    flatness = float(feats["spectral_flatness"])
    crest = float(feats["crest_factor"])
    if flatness < 0.02 and crest < 3.5:
        return _result("SUSPICIOUS", 0.9,
                       "near-pure-tone signal anomaly; this is not evidence that a human caller is cloned",
                       "spectral_fallback_v1", feats, model_available=False)
    if flatness > 0.85:
        return _result("SUSPICIOUS", 0.5,
                       "noise-like spectrum; possible sensor, noise, or replay artefact — not a clone determination",
                       "spectral_fallback_v1", feats, model_available=False)
    return _result("INCONCLUSIVE", 0.3,
                   "ordinary speech cannot be judged by the heuristic fallback; a validated model is required",
                   "spectral_fallback_v1", feats, model_available=False)
