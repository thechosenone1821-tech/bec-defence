"""VoiceGuard — interface + deterministic spectral fallback.

HONESTY LABEL (read before believing any output):
This module is the *contract* for voice-clone screening, plus a spectral
fallback that can flag only degenerate inputs (pure tones, silence, clipped
noise). It is NOT a trained anti-spoofing model and CANNOT detect modern
neural voice clones. Verdicts here are advisory at best; production needs a
trained AASIST/RawNet-class model behind the same interface. The stage demo
ships with the fallback and says so out loud.

Input: mono float32 samples, nominal 16 kHz. Out-of-range payloads degrade
to INCONCLUSIVE — never to a confident verdict.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Sequence

import numpy as np

_MAX_ABS_OK = 4.0


def _features(samples: np.ndarray) -> Dict[str, float]:
    if samples.size < 512:
        return {}
    x = samples.astype(np.float64)
    rms = float(np.sqrt(np.mean(x * x)))
    zcr = float(np.mean(np.abs(np.diff(np.signbit(x)))))
    spec = np.abs(np.fft.rfft(x * np.hanning(x.size))) + 1e-12
    p = spec / spec.sum()
    centroid = float(np.sum(p * np.fft.rfftfreq(x.size, d=1.0 / 16000.0)))
    geo = float(np.exp(np.mean(np.log(spec))))
    arith = float(np.mean(spec))
    flatness = geo / arith
    peak = float(np.max(np.abs(x)))
    crest = peak / (rms + 1e-12)
    return {"rms": round(rms, 6), "zcr": round(zcr, 4),
            "spectral_centroid_hz": round(centroid, 1),
            "spectral_flatness": round(flatness, 6),
            "crest_factor": round(crest, 3)}


def score_voice(samples: Sequence[float]) -> Dict[str, Any]:
    audio = np.asarray(list(samples), dtype=np.float32) if not isinstance(samples, np.ndarray) else samples
    if audio.size < 512:
        return {"verdict": "INCONCLUSIVE", "score": 0.0,
                "engine": "spectral_fallback_v0", "reason": "insufficient samples (<512)",
                "features": {}}
    if not np.isfinite(audio).all() or float(np.max(np.abs(audio))) > _MAX_ABS_OK:
        return {"verdict": "INCONCLUSIVE", "score": 0.0,
                "engine": "spectral_fallback_v0", "reason": "invalid audio payload",
                "features": {}}
    feats = _features(audio)
    if feats["rms"] < 1e-4:
        verdict, reason, score = "SILENT", "no measurable energy", 0.0
    elif feats["spectral_flatness"] < 0.02 and feats["crest_factor"] < 3.5:
        verdict, reason, score = "SUSPICIOUS", "pure-tone-like signal: trivially synthetic", 0.9
    elif feats["spectral_flatness"] > 0.85:
        verdict, reason, score = "SUSPICIOUS", "near-white spectrum: sensor/noise anomaly or replay artifact", 0.5
    else:
        verdict, reason, score = "INCONCLUSIVE", "indeterminate for heuristic fallback — requires trained model", 0.3
    return {"verdict": verdict, "score": score,
            "engine": "spectral_fallback_v0 (heuristic — NOT a trained anti-spoof model)",
            "reason": reason, "features": feats}
