"""MAYA / VoiceGuard — deterministic reason rules over frontend features.

These are *not* the verdict. They are the interpretable evidence an ordinary
person can be shown ("the voice never varies in pitch", "the pauses are
machine-regular"). The verdict in Phase 1 comes from these rules; from Phase 3
a calibrated model contributes its own reason alongside them.

Every rule is:
  * deterministic and pure,
  * **NaN-tolerant** (a feature that could not be measured never fires),
  * conservative — it fires only when the evidence is clear, because a false
    accusation ("your father's voice is fake") is worse than a miss.

Thresholds live in one block so a reviewer can audit them without reading code.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

from . import contract as C

# --------------------------------------------------------------------------- #
# Thresholds. Chosen to fire on the clearly-synthetic cases and stay silent on
# ordinary speech; every one of them is exercised by a test with a boundary
# value just inside and just outside.
# --------------------------------------------------------------------------- #
PURE_TONE_FLATNESS_MAX: float = 0.02
PURE_TONE_CREST_MAX: float = 3.5
# Noise detection uses *two* independent cues. Phase 1 originally tested only
# spectral flatness at 0.85 and white noise measured 0.56 — it slipped through
# as INCONCLUSIVE, a silent regression against the pre-Phase-1 behaviour.
# Flatness is diluted by Hann-window sidelobes plus the geometric mean over
# 257 bins; a high zero-crossing rate is the more robust discriminator for
# aperiodic, broadband input. Requiring both keeps speech safe.
WHITE_NOISE_FLATNESS_MIN: float = 0.45
WHITE_NOISE_ZCR_MIN: float = 0.35
CLIPPED_RATIO_MIN: float = 0.02
SILENCE_RMS_MAX: float = 1e-4
MIN_DURATION_S: float = 0.20
MONOTONE_PITCH_CV_MAX: float = 0.012      # humans sit ~0.10–0.30
MECHANICAL_PAUSE_CV_MAX: float = 0.06     # very regular gaps
MECHANICAL_PAUSE_COUNT_MIN: int = 3
SPECTRAL_REGULARITY_FLUX_MAX: float = 0.02
NO_BREATH_HARMONICITY_MIN: float = 0.92   # sustained, breath-free voicing


def _finite(v: Any) -> bool:
    return isinstance(v, (int, float)) and math.isfinite(float(v))


def evaluate(scalars: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the reasons supported by these measurements (possibly empty)."""
    out: List[Dict[str, Any]] = []
    s = scalars or {}

    def add(code: str, **params: Any) -> None:
        out.append(C.reason(code, **params))

    duration = s.get("duration_s")
    if _finite(duration) and float(duration) < MIN_DURATION_S:
        add(C.R_TOO_SHORT, seconds=round(float(duration), 3))

    rms = s.get("rms")
    if _finite(rms) and float(rms) < SILENCE_RMS_MAX:
        add(C.R_SILENT)
        return out                      # nothing else is meaningful

    clipped = s.get("clipped_ratio")
    if _finite(clipped) and float(clipped) > CLIPPED_RATIO_MIN:
        add(C.R_CLIPPED, ratio=round(float(clipped), 4))

    flatness = s.get("spec_flatness")
    crest = s.get("spec_crest")
    if _finite(flatness) and float(flatness) < PURE_TONE_FLATNESS_MAX:
        if not _finite(crest) or float(crest) < PURE_TONE_CREST_MAX:
            add(C.R_PURE_TONE, flatness=round(float(flatness), 5))
    elif (_finite(flatness) and float(flatness) > WHITE_NOISE_FLATNESS_MIN
          and _finite(s.get("zcr")) and float(s["zcr"]) > WHITE_NOISE_ZCR_MIN):
        add(C.R_WHITE_NOISE, flatness=round(float(flatness), 5),
            zcr=round(float(s["zcr"]), 4))

    # --- production cues: the ones a citizen can actually understand -------- #
    f0_cv = s.get("f0_cv")
    voiced = s.get("voiced_pct")
    if (_finite(f0_cv) and float(f0_cv) < MONOTONE_PITCH_CV_MAX
            and _finite(voiced) and float(voiced) > 60.0):
        add(C.R_MONOTONE_PITCH, cv=round(float(f0_cv), 4),
            voiced_pct=round(float(voiced), 1))

    pcount = s.get("n_pauses")
    pcv = s.get("pause_cv")
    if (_finite(pcount) and int(pcount) >= MECHANICAL_PAUSE_COUNT_MIN
            and _finite(pcv) and float(pcv) < MECHANICAL_PAUSE_CV_MAX):
        add(C.R_MECHANICAL_PAUSES, count=int(pcount), cv=round(float(pcv), 4))

    hnr = s.get("harmonicity")
    if (_finite(hnr) and float(hnr) > NO_BREATH_HARMONICITY_MIN
            and _finite(f0_cv) and float(f0_cv) < 0.05):
        add(C.R_NO_BREATH, harmonicity=round(float(hnr), 4))

    flux = s.get("spec_flux")
    if (_finite(flux) and float(flux) < SPECTRAL_REGULARITY_FLUX_MAX
            and _finite(f0_cv) and float(f0_cv) < 0.05):
        add(C.R_SPECTRAL_REGULARITY, flux=round(float(flux), 5))

    return out


# Codes that are evidence of *production artefacts* rather than "bad audio".
PRODUCTION_CODES = frozenset({
    C.R_MONOTONE_PITCH, C.R_MECHANICAL_PAUSES, C.R_NO_BREATH,
    C.R_SPECTRAL_REGULARITY,
})

# Codes that mean "we cannot judge", which must never read as an accusation.
_UNJUDGEABLE = frozenset({C.R_TOO_SHORT, C.R_SILENT})


def verdict_from_reasons(reasons: List[Dict[str, Any]]) -> str:
    """Phase-1 verdict policy. Deliberately blunt and auditable.

    * nothing to judge (too short / silent)  -> SILENT or INCONCLUSIVE
    * clear degenerate audio (tone, noise)   -> SUSPICIOUS
    * **two or more** production cues        -> SUSPICIOUS
        (one cue alone is common in real compressed telephony — do not accuse)
    * anything else                          -> INCONCLUSIVE
    """
    codes = {r.get("code") for r in reasons if isinstance(r, dict)}
    if C.R_SILENT in codes:
        return C.SILENT
    if codes & {C.R_INVALID_PAYLOAD, C.R_INTERNAL_ERROR}:
        return C.INCONCLUSIVE
    if C.R_TOO_SHORT in codes and not codes & {C.R_PURE_TONE, C.R_WHITE_NOISE}:
        return C.INCONCLUSIVE
    if codes & {C.R_PURE_TONE, C.R_WHITE_NOISE}:
        return C.SUSPICIOUS
    if len(codes & PRODUCTION_CODES) >= 2:
        return C.SUSPICIOUS
    if codes & _UNJUDGEABLE:
        return C.INCONCLUSIVE
    return C.INCONCLUSIVE
