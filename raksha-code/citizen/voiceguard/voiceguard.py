"""MAYA / VoiceGuard — voice-clone *screening* (spectral build, Phase 1).

HONESTY LABEL (read before believing any output):
This module is a **deterministic signal-processing screen**, not a trained
anti-spoof model. It measures timbre and production cues (LFCC/MFCC, pitch
stability, pause regularity, harmonicity) and reports interpretable reasons.
It **cannot detect a modern neural voice clone** — a good TTS will pass this
module as ``INCONCLUSIVE``. Production detection needs the trained model
described in ``MAYA_BUILD.md``; until that model exists the engine label says
so, and ``contract.may_claim_clone_detection()`` returns False.

What changed in Phase 1 and why it matters:
  * Features went from 5 numbers to a full LFCC/MFCC + prosody frontend
    (:mod:`citizen.voiceguard.features`), which is what a model will consume.
  * Every verdict now carries **structured reason codes** with parameters
    (:mod:`citizen.voiceguard.reasons`) instead of a single prose string, so
    they can be translated (Phase 4) without touching the model.
  * The output schema is additive: every key that existed before still exists
    with the same meaning, so the PWA and the report rail keep working.

Backward compatibility is a hard requirement: ``tests/test_voiceguard.py``
was written against the old contract and must keep passing untouched.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Sequence

import numpy as np

from . import contract as C
from . import features as F
from . import model as _model
from . import reasons as R

_MAX_ABS_OK = 4.0
_MIN_SAMPLES = 512


def _invalid(reason_code: str, extra: str = "") -> Dict[str, Any]:
    return {
        "verdict": C.INCONCLUSIVE,
        "score": 0.0,
        "engine": C.engine_label(),
        "reason": extra or "invalid or insufficient audio payload",
        "features": {},
        "reasons": [C.reason(reason_code)],
        "contract_version": C.CONTRACT_VERSION,
        "features_version": F.FEATURES_VERSION,
        "model": None,
        "raw_score": 0.0,
    }


def score_voice(samples: Sequence[float] | np.ndarray,
                sr: int = F.SAMPLE_RATE) -> Dict[str, Any]:
    """Screen one clip. Never raises; degrades to ``INCONCLUSIVE``.

    Parameters
    ----------
    samples : mono float32/float64, nominally 16 kHz.
    sr      : sample rate; only 16 kHz is measured today (documented limit).

    Returns a dict whose keys are stable across versions (see module docstring).
    """
    # Phase 3 fuzz finding: this cast sat OUTSIDE the try/except, so
    # `score_voice(["a", "b"])` raised ValueError despite the function's
    # documented promise that it never raises. The docstring is the contract;
    # the conversion had simply been placed above the guard that honours it.
    try:
        audio = np.asarray(list(samples), dtype=np.float64) \
            if not isinstance(samples, np.ndarray) \
            else np.asarray(samples, dtype=np.float64)
        audio = audio.ravel()
    except (TypeError, ValueError):
        return _invalid(C.R_INVALID_PAYLOAD, "audio could not be interpreted as numbers")

    if audio.size < _MIN_SAMPLES:
        return _invalid(C.R_TOO_SHORT, "insufficient samples (<512)")
    if not np.isfinite(audio).all() or float(np.max(np.abs(audio))) > _MAX_ABS_OK:
        return _invalid(C.R_INVALID_PAYLOAD, "invalid audio payload")
    if sr != F.SAMPLE_RATE:
        return _invalid(C.R_INVALID_PAYLOAD,
                        f"unsupported sample rate {sr}; resample to {F.SAMPLE_RATE} first")

    try:
        feats = F.extract(audio, sr=sr)
        scalars = feats["scalars"]
        found = R.evaluate(scalars)
        verdict = R.verdict_from_reasons(found)
    except Exception as exc:                      # never let a screen crash the app
        out = _invalid(C.R_INTERNAL_ERROR, f"screening failed safely: {type(exc).__name__}")
        return out

    # --- Phase 3: the trained model contributes its own reason ------------- #
    #
    # The model is consulted ONLY when there is actual speech to judge. This is
    # a safety rule, not an optimisation. Found live during Phase 3: pure
    # digital silence scored P(spoof)=0.94 and the app announced "this is
    # probably an AI-generated voice" about a recording containing no voice at
    # all. A model trained on 2-second speech clips has no idea what silence
    # is; it must never be asked. Silence and unjudgeable input stay SILENT /
    # INCONCLUSIVE no matter what the model thinks.
    _MODEL_ELIGIBLE = {C.INCONCLUSIVE, C.SUSPICIOUS, C.LIKELY_SYNTHETIC}
    model = _model.get_model() if verdict in _MODEL_ELIGIBLE else None
    model_prob = None
    if model is not None:
        try:
            row = [scalars.get(k) for k in _model.ROBUST_KEYS]
            model_prob = model.probability_from_row(np.asarray(row, dtype=np.float64))
            if model_prob >= model.decision_threshold:
                found = found + [C.reason(C.R_MODEL_CLONE, p=round(model_prob, 3))]
                # The model may escalate, and this is the ONLY path to
                # LIKELY_SYNTHETIC. It may never de-escalate a deterministic
                # verdict: a confident model does not get to overrule a
                # measured pure tone.
                if C.severity_rank(C.LIKELY_SYNTHETIC) > C.severity_rank(verdict):
                    verdict = C.LIKELY_SYNTHETIC
            else:
                found = found + [C.reason(C.R_MODEL_CLEAN, p=round(model_prob, 3))]
        except Exception:
            model = None                          # model trouble degrades, never crashes
            model_prob = None
    elif verdict in _MODEL_ELIGIBLE:
        # No model artefact available at all (weights missing/unreadable).
        found = found + [C.reason(C.R_NO_MODEL)]
    # else: verdict is SILENT or otherwise out of the model's domain — no
    # reason is added, because "no model was consulted" and "no model exists"
    # are different statements and conflating them misleads a reader of the
    # payload.

    if not found:
        found = [C.reason(C.R_LOW_CONFIDENCE)]

    score = _score_from(verdict, found, model_prob)

    return {
        "verdict": verdict,
        "score": round(score, 3),
        "engine": C.engine_label(model.model_id if model is not None else None),
        "reason": _primary_text(verdict, found),
        "features": _flatten(scalars),
        "reasons": found,
        "contract_version": C.CONTRACT_VERSION,
        "features_version": feats["version"],
        "model": ({"id": model.model_id, "p_spoof": round(model_prob, 4),
                   "threshold": model.decision_threshold,
                   "trained_on": "SYNTHETIC corpus (real-world UNMEASURED)"}
                  if model is not None and model_prob is not None else None),
        "raw_score": round(score, 3),
        "audio_sha256": hashlib.sha256(audio.astype(np.float32).tobytes()).hexdigest()[:16],
        "duration_s": scalars.get("duration_s"),
    }


def _score_from(verdict: str, found: list, model_prob: float | None = None) -> float:
    """Interpretable 0..1 confidence, not a calibrated probability.

    Phase 3 replaces this with a calibrated model probability. Until then it is
    a deterministic function of how many production cues fired — documented as
    such so nobody puts it in a paper.
    """
    if verdict == C.SILENT:
        return 0.0
    codes = {r.get("code") for r in found if isinstance(r, dict)}
    if codes & {C.R_PURE_TONE, C.R_WHITE_NOISE}:
        return 0.9
    if verdict == C.LIKELY_SYNTHETIC and model_prob is not None:
        return round(min(0.99, max(0.80, model_prob)), 3)
    n_prod = len(codes & R.PRODUCTION_CODES)
    if verdict == C.SUSPICIOUS:
        return min(0.95, 0.55 + 0.12 * n_prod)
    return 0.3 if verdict == C.INCONCLUSIVE else 0.1


_SUMMARY = {
    C.SILENT: "no audible speech in this clip",
    C.INCONCLUSIVE: "cannot tell from this clip — treat with care if they ask for money, OTP or an 'arrest'",
    C.SUSPICIOUS: "the audio has machine-like characteristics",
    C.LIKELY_SYNTHETIC: "this is probably an AI-generated voice — hang up and call back on an official number",
}


def _primary_text(verdict: str, found: list) -> str:
    """Legacy single-sentence field. Phase 4 renders per-language sentences
    from ``reasons`` instead; this stays until the PWA switches over."""
    if verdict == C.SILENT:
        return "no measurable energy"
    prod = [r["code"] for r in found if r.get("code") in R.PRODUCTION_CODES]
    if verdict == C.SUSPICIOUS and prod:
        return "machine-like speech production: " + ", ".join(prod).lower().replace("_", " ")
    if verdict == C.SUSPICIOUS:
        return "trivial synthetic signal detected"
    return _SUMMARY.get(verdict, "indeterminate")


_LEGACY_FEATURE_KEYS = {
    "rms": "rms",
    "zcr": "zcr",
    "spectral_flatness": "spec_flatness",
    "crest_factor": "spec_crest",
}


def _flatten(scalars: Dict[str, Any]) -> Dict[str, Any]:
    """Preserve the old ``features`` keys (contract) and add the new ones."""
    out: Dict[str, Any] = {}
    for old, new in _LEGACY_FEATURE_KEYS.items():
        out[old] = scalars.get(new)
    out["spectral_centroid_hz"] = scalars.get("spec_centroid_hz")
    out.update({k: v for k, v in scalars.items() if k not in out})
    return out
