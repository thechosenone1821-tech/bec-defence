"""Citizen Risk Engine — Signal Fusion Core.

This module decides only how signals combine into a score and a band. It contains
no sentences, no languages, no HTTP and no I/O. Citizen copy renders the result.

The retired scorer is gone: MessageGuard, campaign linkage, repeat contacts
and explicit user doubt are the remaining independent signals. Absence of
evidence never becomes a negative contribution or a reassuring band.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from .. import copy as i18n  # language normalisation only; sentences stay in the app

BAND_LOW_CONFIDENCE = "LOW_CONFIDENCE"
BAND_LOW = "LOW"
BAND_ELEVATED = "ELEVATED"
BAND_HIGH = "HIGH"
BAND_CRITICAL = "CRITICAL"

BANDS: Tuple[str, ...] = (BAND_LOW_CONFIDENCE, BAND_LOW, BAND_ELEVATED,
                          BAND_HIGH, BAND_CRITICAL)

_BAND_TABLE: Tuple[Tuple[float, str], ...] = (
    (0.20, BAND_LOW),
    (0.45, BAND_ELEVATED),
    (0.70, BAND_HIGH),
    (1.01, BAND_CRITICAL),
)

_MIN_MEANINGFUL = 0.10
_MIN_SIGNAL_COUNT = 2
_STANDALONE_SOURCES = frozenset({"message", "campaign"})


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if f != f or f in (float("inf"), float("-inf")):
        return default
    return f


def safe_int(v: Any, default: int = 0) -> int:
    f = safe_float(v, default=float(default))
    try:
        return int(f)
    except (ValueError, OverflowError):
        return default


def safe_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v == 1
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return False


def clamp01(v: Any) -> float:
    return max(0.0, min(1.0, safe_float(v, 0.0)))


RuleResult = Tuple[float, Optional[str], str]


def _message_rule(payload: Any) -> RuleResult:
    if not isinstance(payload, dict):
        return 0.0, None, "no message reading supplied"
    verdict = str(payload.get("verdict") or "").upper()
    if verdict == "CRITICAL":
        return 0.60, verdict, ""
    if verdict == "HIGH":
        return 0.35, verdict, ""
    if verdict in ("LOW", "MODERATE"):
        return 0.0, None, f"message reading was {verdict} — below the bar"
    return 0.0, None, "message verdict not recognised"


def _campaign_rule(payload: Any, *_safe) -> RuleResult:
    if safe_bool(payload):
        return 0.45, "same pattern already reported", ""
    return 0.0, None, "no campaign linkage"


def _repeat_rule(payload: Any) -> RuleResult:
    n = safe_int(payload, 0)
    if n >= 3:
        return 0.20, f"{n} attempts", ""
    if n <= 0:
        return 0.0, None, "no repeat-contact count supplied"
    return 0.0, None, f"{n} attempt(s) is below the threshold of 3"


def _doubt_rule(payload: Any, *_safe) -> RuleResult:
    if safe_bool(payload):
        return 0.15, "user reported unease", ""
    return 0.0, None, "user did not report doubt"


RULES: Dict[str, Callable[..., RuleResult]] = {
    "message": _message_rule,
    "campaign": _campaign_rule,
    "repeat_contact": _repeat_rule,
    "user_doubt": _doubt_rule,
}

SOURCE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "message": {"CRITICAL": 0.60, "HIGH": 0.35},
    "campaign": {"linked": 0.45},
    "repeat_contact": {"three_or_more": 0.20},
    "user_doubt": {"reported": 0.15},
}


def noisy_or(weights: List[float]) -> float:
    remaining = 1.0
    for w in weights:
        remaining *= (1.0 - clamp01(w))
    return 1.0 - remaining


def band_for(score: float, n_signals: int,
             sources: Optional[List[str]] = None) -> Tuple[str, str]:
    if n_signals == 0:
        return BAND_LOW_CONFIDENCE, "no signals contributed"
    if score < _MIN_MEANINGFUL:
        return BAND_LOW_CONFIDENCE, f"fused score {score:.3f} is below {_MIN_MEANINGFUL}"
    srcs = set(sources or [])
    if not (n_signals >= _MIN_SIGNAL_COUNT or srcs & _STANDALONE_SOURCES):
        return (BAND_LOW_CONFIDENCE,
                "a single weak signal is not enough without corroboration")
    for limit, band in _BAND_TABLE:
        if score < limit:
            return band, f"fused score {score:.3f} falls in [{band.lower()}]"
    return BAND_CRITICAL, f"fused score {score:.3f} exceeds every threshold"


def evaluate(message: Optional[Dict[str, Any]] = None,
             campaign_linked: Any = False,
             repeat_contacts: Any = 0,
             user_doubt: Any = False) -> Dict[str, Any]:
    payloads = {
        "message": message,
        "campaign": campaign_linked,
        "repeat_contact": repeat_contacts,
        "user_doubt": user_doubt,
    }
    fired: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    weights: List[float] = []
    for source, fn in RULES.items():
        try:
            weight, detail, skip_reason = fn(payloads.get(source))
        except Exception as exc:
            skipped.append({"source": source, "reason": f"rule error: {type(exc).__name__}"})
            continue
        if weight > 0:
            weights.append(weight)
            fired.append({"source": source, "weight": round(weight, 3), "detail": detail})
        else:
            skipped.append({"source": source, "reason": skip_reason or "no evidence"})

    score = round(noisy_or(weights), 4)
    band, band_reason = band_for(score, len(weights), [f["source"] for f in fired])
    return {
        "band": band,
        "band_reason": band_reason,
        "score": score,
        "signals": fired,
        "skipped": skipped,
        "weights_used": [round(w, 3) for w in weights],
        "degraded": band == BAND_LOW_CONFIDENCE,
        "sources_evaluated": len(RULES),
        "sources_fired": len(fired),
    }


def normalise_language(lang: Any) -> str:
    return i18n.normalise_language(lang)
