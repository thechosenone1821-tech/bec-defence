"""MAYA / VoiceGuard package.

Public surface is frozen by ``contract.CONTRACT_VERSION``. Import from here,
never from the submodules, so a model swap cannot ripple through the app.
"""

from .contract import (
    CONTRACT_VERSION,
    VERDICTS,
    engine_label,
    may_claim_clone_detection,
    max_verdict,
    severity_rank,
)
from .features import FEATURES_VERSION, extract, vector_for_model
from .reasons import evaluate as evaluate_reasons
from .voiceguard import score_voice

__all__ = [
    "score_voice",
    "extract",
    "vector_for_model",
    "evaluate_reasons",
    "CONTRACT_VERSION",
    "FEATURES_VERSION",
    "VERDICTS",
    "engine_label",
    "may_claim_clone_detection",
    "max_verdict",
    "severity_rank",
]
