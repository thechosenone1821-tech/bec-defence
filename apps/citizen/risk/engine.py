"""RAKSHA Citizen — Risk Engine.

One verdict for a person, built from independent signals scored separately:

    message verdict (MessageGuard) -- does the text look like a scam script?
    campaign link   (report rail)  -- has this pattern been reported before?
    repeat contact  (on device)    -- are they contacting you again and again?
    user doubt      (explicit tap) -- do you feel something is wrong?

There is a "we don't know" answer. A citizen screen that says "safe" when it has
no information transfers trust to a system that has not earned it. Empty or weak
input returns LOW_CONFIDENCE, never SAFE. Bounded noisy-OR keeps every
contribution inspectable and the fused score at or below 1.0.

Honesty note: the weights are engineering judgement, not calibrated against real
fraud outcomes. Real-world accuracy, recall and false-positive rate are
UNMEASURED.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import fusion
from packages.contracts import i18n as VC
from .. import copy as i18n
from ..copy import render_source as fusion_reason

W_MESSAGE_HIGH = 0.35
W_MESSAGE_CRITICAL = 0.60
W_CAMPAIGN_LINK = 0.45
W_REPEAT_CONTACT = 0.20
W_USER_DOUBT = 0.15

BAND_LOW_CONFIDENCE = "LOW_CONFIDENCE"
BAND_LOW = "LOW"
BAND_ELEVATED = "ELEVATED"
BAND_HIGH = "HIGH"
BAND_CRITICAL = "CRITICAL"
BANDS = (BAND_LOW_CONFIDENCE, BAND_LOW, BAND_ELEVATED, BAND_HIGH, BAND_CRITICAL)
_BAND_TABLE = ((0.20, BAND_LOW), (0.45, BAND_ELEVATED),
               (0.70, BAND_HIGH), (1.01, BAND_CRITICAL))
_MIN_MEANINGFUL = 0.10
_MIN_SIGNAL_COUNT = 2
_STANDALONE_SOURCES = frozenset({"message", "campaign"})


def _safe_int(v: Any) -> int:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0
    if f != f or f in (float("inf"), float("-inf")):
        return 0
    try:
        return int(f)
    except (ValueError, OverflowError):
        return 0


def _safe_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v == 1
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return False


def _clamp01(v: Any) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    if f != f:
        return 0.0
    return max(0.0, min(1.0, f))


def noisy_or(weights: List[float]) -> float:
    remaining = 1.0
    for w in weights:
        remaining *= (1.0 - _clamp01(w))
    return 1.0 - remaining


def band_for(score: float, n_signals: int,
             sources: Optional[List[str]] = None) -> str:
    if n_signals == 0 or score < _MIN_MEANINGFUL:
        return BAND_LOW_CONFIDENCE
    srcs = set(sources or [])
    corroborated = n_signals >= _MIN_SIGNAL_COUNT or bool(srcs & _STANDALONE_SOURCES)
    if not corroborated:
        return BAND_LOW_CONFIDENCE
    for limit, band in _BAND_TABLE:
        if score < limit:
            return band
    return BAND_CRITICAL


def assess(message: Optional[Dict[str, Any]] = None,
           campaign_linked: bool = False,
           repeat_contacts: int = 0,
           user_doubt: bool = False,
           lang: str = "en") -> Dict[str, Any]:
    lang = i18n.normalise_language(lang)
    core = fusion.evaluate(
        message=message,
        campaign_linked=campaign_linked,
        repeat_contacts=repeat_contacts,
        user_doubt=user_doubt,
    )
    band = core["band"]
    display = i18n.render_band(band, lang)
    reasons = [fusion_reason(s, lang) for s in core["signals"]]
    if not reasons:
        reasons = [i18n.render_reason(VC.R_LOW_CONFIDENCE, lang)]
    return {
        "band": band,
        "band_reason": core["band_reason"],
        "score": core["score"],
        "signals": core["signals"],
        "skipped": core["skipped"],
        "weights_used": core["weights_used"],
        "headline": display["headline"],
        "action": display["action"],
        "reasons": reasons,
        "helpline": i18n.HELPLINE,
        "lang": lang,
        "degraded": core["degraded"],
        "advisory": i18n.render_advisory(lang),
        "band_explanation": i18n.render_band_reason(core["band_reason"], lang),
    }
