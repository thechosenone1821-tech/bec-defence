"""MessageGuard — deterministic, offline scam-script detection.

Public API:
    analyze(text, lang="auto") -> dict   measured v1 result
    score_message(text) -> dict          Citizen API compatibility payload
    band(score) -> str
    to_legacy_band(verdict) -> float    (0.25-0.99 legacy organ RPC)

Deliberately rules-based, not a trained model; see `scorer.py` for the six
signal families, the weighting, and the stated failure modes. Reason codes
live in `reasons.py` and render through `citizen.voiceguard.i18n`.
"""

from .bandmap import LEGACY_BANDS, to_legacy_band
from .reasons import REASON_CATALOGUE, reason_for
from .scorer import (
    ENGINE,
    FAMILY_WEIGHTS,
    VERDICT_ORDER,
    analyze,
    band,
    evaluate_fixtures,
    score_message,
    verdict_at_least,
)

__version__ = "0.3.0+integrated"

__all__ = [
    "analyze",
    "score_message",
    "evaluate_fixtures",
    "verdict_at_least",
    "band",
    "to_legacy_band",
    "reason_for",
    "FAMILY_WEIGHTS",
    "VERDICT_ORDER",
    "LEGACY_BANDS",
    "REASON_CATALOGUE",
    "ENGINE",
    "__version__",
]
