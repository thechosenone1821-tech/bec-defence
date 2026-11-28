"""MessageGuard — the one deterministic, offline Citizen detector.

Public API:
    analyze(text, lang="auto") -> dict   measured result; explicit hinglish supported
    score_message(text) -> dict          Citizen API compatibility payload
    detect_language(text) -> str         script/cue-based matching hint
    band(score) -> str                   shared verdict band
    to_legacy_band(verdict) -> float     categorical 0.25-0.99 legacy band
    to_legacy_organ_payload(result)      ported operator adapter
    evaluate_fixtures(path) -> dict      one corpus diagnostic
    reason_for(code)                     one shared MSG-* catalogue

``citizen.messageguard`` and ``raksha-code/apps/citizen/messageguard`` are
compatibility aliases to this package, not second implementations. Phase 5
archived the independent ``raksha.messageguard`` scorer under
``archive/provenance/``. No model is run; the CLI and eval runner use this
same interface. Reason sentences render through the Phase 4 shared i18n
contract, never through a second reason catalogue.
"""

from .bandmap import LEGACY_BANDS, to_legacy_band
from .detect import SCRIPT_LANGS, SUPPORTED_LANGS, detect_language
from .legacy_organ import (
    LegacyOrganPayload, legacy_confidence, to_legacy_organ_payload,
)
from .reasons import REASON_CATALOGUE, reason_for
from .scorer import (
    ENGINE,
    FAMILY_WEIGHTS,
    SUPPORTED_DETECTOR_LANGS,
    VERDICT_ORDER,
    analyze,
    band,
    evaluate_fixtures,
    score_message,
    verdict_at_least,
)

__version__ = "0.4.0+phase5"

__all__ = [
    "analyze",
    "score_message",
    "evaluate_fixtures",
    "verdict_at_least",
    "band",
    "to_legacy_band",
    "reason_for",
    "detect_language",
    "SCRIPT_LANGS",
    "SUPPORTED_LANGS",
    "SUPPORTED_DETECTOR_LANGS",
    "LegacyOrganPayload",
    "legacy_confidence",
    "to_legacy_organ_payload",
    "FAMILY_WEIGHTS",
    "VERDICT_ORDER",
    "LEGACY_BANDS",
    "REASON_CATALOGUE",
    "ENGINE",
    "__version__",
]
