"""Public API for MessageGuard (Part 3).

    from raksha.messageguard import assess

    v = assess("Your KYC expires today, update at bit.ly/kyc9 or account closes")
    v.score          # 0.45
    v.band           # Band.HIGH
    v.reasons        # every hit, naming family + matched phrase
    v.citizen("hi")  # Hindi citizen-facing summary for the app UI
    v.to_dict()      # serialisable form

See the package docstring in ``scorer.py`` for the honest statement of what
this detector cannot do — that statement is part of the contract.
"""

from .detect import detect_language
from .families import FAMILY_TO_CODE, FAMILY_WEIGHTS
from .legacy_organ import LegacyOrganPayload, legacy_confidence, to_legacy_organ_payload
from .scorer import SignalFamilyScorer, assess, score
from .types import Band, Reason, Verdict, band_for

__all__ = [
    "assess",
    "score",
    "SignalFamilyScorer",
    "Verdict",
    "Reason",
    "Band",
    "band_for",
    "detect_language",
    "FAMILY_WEIGHTS",
    "FAMILY_TO_CODE",
    "legacy_confidence",
    "LegacyOrganPayload",
    "to_legacy_organ_payload",
]
