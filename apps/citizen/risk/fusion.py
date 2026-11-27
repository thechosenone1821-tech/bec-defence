"""Citizen Risk Engine — Signal Fusion Core (Part One).

This module decides **only** how signals combine into a score and a band. It
contains no sentences, no languages, no HTTP, and no I/O. That separation is the
whole point of the split:

    Part 1 (this file)  decides *how much* evidence there is
    Part 2 (i18n)       decides *what to say* about it
    Part 4 (api/app)    decides *where it goes*

If you find yourself wanting to add a string to this file, it belongs in Part 2.
If you want to add a weight to Part 2, it belongs here.

Design notes worth keeping:

* **Rules are data.** Each input source is one entry in ``RULES``, so adding a
  signal is a table edit rather than another branch in a function that is already
  the most safety-critical code in the app. A reviewer reads the table; they do
  not have to trace control flow.
* **Every result is auditable.** ``fired`` and ``skipped`` both come back, with a
  human-readable reason for each skip. "Why did this not fire?" is the question an
  audit asks, and it previously had no answer in the payload at all.
* **Absence of evidence is not evidence of absence.** ``INCONCLUSIVE`` and
  ``SILENT`` voice readings, an unknown message verdict, and unparseable input all
  produce *no* contribution — never a negative one, and never a reassuring band.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from packages.contracts import i18n as VC
from .. import copy as i18n  # language normalisation only; sentences stay in the app

# --------------------------------------------------------------------------- #
# Bands, in increasing severity. LOW_CONFIDENCE sorts below LOW on purpose:
# "we cannot tell" is a weaker statement than "we looked and found little".
# --------------------------------------------------------------------------- #
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

# "Nothing found" must never be reported as "nothing wrong".
_MIN_MEANINGFUL = 0.10     # fused score must clear this to leave LOW_CONFIDENCE
_MIN_SIGNAL_COUNT = 2      # ... or be corroborated by at least two signals
_STANDALONE_SOURCES = frozenset({"voice", "message", "campaign"})


# --------------------------------------------------------------------------- #
# Coercion — never raise, and never let junk masquerade as evidence
# --------------------------------------------------------------------------- #
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
    """Only real truthy *values* count — not merely truthy *strings*.

    `campaign_linked="nope"` used to add the full campaign weight because a
    non-empty string is truthy. That is an accusation produced from a type error,
    so it is excluded here by naming the accepted spellings explicitly.
    """
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v == 1
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return False


def clamp01(v: Any) -> float:
    return max(0.0, min(1.0, safe_float(v, 0.0)))


# --------------------------------------------------------------------------- #
# The rule table
# --------------------------------------------------------------------------- #
# Each rule: (source, weight, predicate, why-not-fired explanation)
# A predicate returns True only when that source contributes real evidence.
# --------------------------------------------------------------------------- #
RuleResult = Tuple[str, float, str]      # source, weight, detail


def _voice_rule(payload: Any) -> Tuple[float, Optional[str], str]:
    """Returns (weight, detail, skip_reason)."""
    if not isinstance(payload, dict):
        return 0.0, None, "no voice reading supplied"
    verdict = payload.get("verdict")
    if verdict == VC.LIKELY_SYNTHETIC:
        return 0.65, verdict, ""
    if verdict == VC.SUSPICIOUS:
        return 0.40, verdict, ""
    if verdict in (VC.INCONCLUSIVE, VC.SILENT):
        return 0.0, None, f"voice reading was {verdict} — absence of evidence"
    return 0.0, None, "voice verdict not recognised"


def _message_rule(payload: Any) -> Tuple[float, Optional[str], str]:
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


def _campaign_rule(payload: Any, *_safe) -> Tuple[float, Optional[str], str]:
    if safe_bool(payload):
        return 0.45, "same pattern already reported", ""
    return 0.0, None, "no campaign linkage"


def _repeat_rule(payload: Any) -> Tuple[float, Optional[str], str]:
    n = safe_int(payload, 0)
    if n >= 3:
        return 0.20, f"{n} attempts", ""
    if n <= 0:
        return 0.0, None, "no repeat-contact count supplied"
    return 0.0, None, f"{n} attempt(s) is below the threshold of 3"


def _doubt_rule(payload: Any, *_safe) -> Tuple[float, Optional[str], str]:
    if safe_bool(payload):
        return 0.15, "user reported unease", ""
    return 0.0, None, "user did not report doubt"


RULES: Dict[str, Callable[..., Tuple[float, Optional[str], str]]] = {
    "voice": _voice_rule,
    "message": _message_rule,
    "campaign": _campaign_rule,
    "repeat_contact": _repeat_rule,
    "user_doubt": _doubt_rule,
}

# Public, for reviewers and for tests that pin the arithmetic.
SOURCE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "voice": {"LIKELY_SYNTHETIC": 0.65, "SUSPICIOUS": 0.40},
    "message": {"CRITICAL": 0.60, "HIGH": 0.35},
    "campaign": {"linked": 0.45},
    "repeat_contact": {"three_or_more": 0.20},
    "user_doubt": {"reported": 0.15},
}


# --------------------------------------------------------------------------- #
# Fusion maths
# --------------------------------------------------------------------------- #
def noisy_or(weights: List[float]) -> float:
    """Bounded union of independent evidence. Never exceeds 1.0."""
    remaining = 1.0
    for w in weights:
        remaining *= (1.0 - clamp01(w))
    return 1.0 - remaining


def band_for(score: float, n_signals: int,
             sources: Optional[List[str]] = None) -> Tuple[str, str]:
    """Map a fused score to a band. Returns (band, why).

    A band above LOW_CONFIDENCE requires either one standalone source or at least
    ``_MIN_SIGNAL_COUNT`` contributing signals. The second return value explains
    the decision, because "why is this only LOW_CONFIDENCE" is a question a
    support engineer will ask and previously could not answer.
    """
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


# --------------------------------------------------------------------------- #
# The entry point
# --------------------------------------------------------------------------- #
def evaluate(voice: Optional[Dict[str, Any]] = None,
             message: Optional[Dict[str, Any]] = None,
             campaign_linked: Any = False,
             repeat_contacts: Any = 0,
             user_doubt: Any = False) -> Dict[str, Any]:
    """Fuse signals into a score, a band, and a full audit trail.

    No text, no language, no I/O. Callers render this (Part 2) and deliver it
    (Part 4).
    """
    payloads = {
        "voice": voice,
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
        except Exception as exc:      # a broken rule must never break the screen
            skipped.append({"source": source, "reason": f"rule error: {type(exc).__name__}"})
            continue
        if weight > 0:
            weights.append(weight)
            fired.append({"source": source, "weight": round(weight, 3),
                          "detail": detail})
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
    """Kept here so Part 4 has one import; delegates to the Part 2 catalogue."""
    return i18n.normalise_language(lang)
