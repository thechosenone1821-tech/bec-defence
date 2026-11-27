"""Verdict types, constants and the Reason/Verdict data model.

The scoring math is fixed by the Part 3 specification:

    weights      credential 0.45, authority 0.40, money_action 0.30,
                 prize 0.30, urgency 0.20, link_grab 0.25
    raw score    sum of the weights of the distinct families that fired
    boost        3 or more families hit  =>  raw x 1.3
    cap          1.0 (never higher)
    bands        < 0.20 LOW | < 0.45 MODERATE | < 0.70 HIGH | >= 0.70 CRITICAL
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

BAND_THRESHOLDS: tuple[float, float, float] = (0.20, 0.45, 0.70)
BOOST_MIN_FAMILIES: int = 3
BOOST_FACTOR: float = 1.3
SCORE_CAP: float = 1.0

__all__ = [
    "BAND_THRESHOLDS",
    "BOOST_MIN_FAMILIES",
    "BOOST_FACTOR",
    "SCORE_CAP",
    "Band",
    "Reason",
    "Verdict",
    "band_for",
]


class Band(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def order(self) -> int:
        return BAND_ORDER.index(self)


BAND_ORDER: tuple[Band, ...] = (
    Band.LOW,
    Band.MODERATE,
    Band.HIGH,
    Band.CRITICAL,
)


def band_for(score: float) -> Band:
    """Map a raw score in [0, 1] onto the verdict bands from the spec."""
    if score < BAND_THRESHOLDS[0]:
        return Band.LOW
    if score < BAND_THRESHOLDS[1]:
        return Band.MODERATE
    if score < BAND_THRESHOLDS[2]:
        return Band.HIGH
    return Band.CRITICAL


@dataclass(frozen=True)
class Reason:
    """One explainable hit.

    Every reason names the family that fired (DoD requirement), the matched
    phrase, how it was matched and where it matched. ``spans`` are character
    offsets into the *normalized* text (casefolded, whitespace collapsed) that
    the matcher searched; the UI can highlight from these.
    """

    code: str                 # ReasonCode value from the Part 1 catalogue
    family: str               # one of the six signal families
    trigger: str              # "phrase" | "pattern" | "pair"
    matched: str              # matched phrase / pattern hit / "entity + partner"
    spans: tuple[tuple[int, int], ...] = ()

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "family": self.family,
            "trigger": self.trigger,
            "matched": self.matched,
            "spans": [list(s) for s in self.spans],
        }


@dataclass(frozen=True)
class Verdict:
    """Full deterministic verdict for one message."""

    text: str                          # original message text
    lang: str                          # resolved matching language ("en"/"hi"/"te"/"hinglish")
    score: float                       # in [0.0, 1.0], capped
    band: Band
    families: tuple[str, ...]          # distinct families that fired, weight order
    reasons: tuple[Reason, ...]
    boosted: bool                      # whether the x1.3 multi-family boost applied
    family_hits: dict[str, int] = field(default_factory=dict, compare=False)

    def to_dict(self) -> dict:
        return {
            "lang": self.lang,
            "score": round(self.score, 4),
            "band": self.band.value,
            "families": list(self.families),
            "boosted": self.boosted,
            "family_hits": dict(self.family_hits),
            "reasons": [r.to_dict() for r in self.reasons],
        }

    def citizen(self, lang: str | None = None) -> dict:
        """Citizen-facing summary: band label, advice and reason sentences.

        Uses the Part 1 i18n catalogue. ``lang`` may be "en", "hi", "te" or the
        detector's own language tag (``hinglish`` is shown Hindi).
        """
        from ..reasons import BAND_ADVICE, BAND_LABELS, ReasonCode, display_lang, reason_text

        lang = display_lang(lang or self.lang)
        reasons = []
        for r in self.reasons:
            try:
                code = ReasonCode(r.code)
            except ValueError:
                continue
            reasons.append(reason_text(code, lang, phrase=r.matched))
        return {
            "lang": lang,
            "band": self.band.value,
            "band_label": BAND_LABELS[self.band.value][lang],
            "advice": BAND_ADVICE[self.band.value][lang],
            "reasons": reasons,
        }
