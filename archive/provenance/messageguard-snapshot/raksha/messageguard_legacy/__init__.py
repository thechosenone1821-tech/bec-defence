"""MessageGuard — deterministic, offline scam-script detection.

Public API:
    analyze(text, lang="auto") -> dict   (score, verdict, reasons, ...)
    band(score) -> str
    to_legacy_band(verdict) -> float     (0.25-0.99 legacy organ RPC)

Deliberately rules-based, not a trained model; see scorer.py docstring
for the six signal families, the weighting, and the stated failure
modes. Reason codes come from the shared Part 1 catalogue
(messageguard.reasons) and are stable across languages.
"""

from .bandmap import LEGACY_BANDS, to_legacy_band
from .reasons import REASON_CATALOGUE
from .scorer import FAMILY_WEIGHTS, VERDICT_ORDER, analyze, band

__version__ = "0.3.0"

__all__ = [
    "analyze",
    "band",
    "to_legacy_band",
    "FAMILY_WEIGHTS",
    "VERDICT_ORDER",
    "LEGACY_BANDS",
    "REASON_CATALOGUE",
    "__version__",
]
