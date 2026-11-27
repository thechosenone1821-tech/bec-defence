"""Phase 4 — documented, disabled VoiceGuard interface.

This is the only active Citizen voice seam. It deliberately contains no import
from ``citizen.voiceguard``, no MAYA model, no capture worklet and no inference
call. The frozen implementation remains behind
``apps/citizen/legacy_voiceguard.py`` for future Phase 11 work only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol

from . import copy as citizen_copy
from .features import NO_AI_MODELS, voiceguard_enabled

INTERFACE_VERSION = "voiceguard-disabled-v1"


class VoiceGuardInterface(Protocol):
    """The contract a future VoiceGuard integration must implement."""

    def status(self) -> Dict[str, Any]: ...

    def screen(self, samples: Any, *, consent: bool, lang: str = "en") -> Dict[str, Any]: ...


@dataclass(frozen=True)
class DisabledVoiceGuard:
    """Fail-closed implementation used until VoiceGuard is explicitly integrated."""

    def status(self) -> Dict[str, Any]:
        return {
            "interface": INTERFACE_VERSION,
            "enabled": False,
            "status": "not integrated yet",
            "model_invoked": False,
            "no_ai_models": NO_AI_MODELS,
            "frozen_assets": "untouched — see tools/frozen_assets.sha256",
        }

    def screen(self, samples: Any, *, consent: bool, lang: str = "en") -> Dict[str, Any]:
        """Return honest copy without processing, storing or scoring samples."""
        lang = citizen_copy.normalise_language(lang)
        copy = citizen_copy.voice_tab_copy(lang)
        return {
            "status": "NOT_INTEGRATED",
            "verdict": "INCONCLUSIVE",
            "audio_processed": False,
            "model_invoked": False,
            "samples_echoed": False,
            "helpline": citizen_copy.HELPLINE,
            "lang": lang,
            "explanation": {
                "title": copy["title"],
                "detail": copy["detail"],
                "helpline": copy["helpline"],
                "lang": lang,
                "actionable": False,
            },
            "feature_flag_enabled": voiceguard_enabled(),
        }


VOICEGUARD: VoiceGuardInterface = DisabledVoiceGuard()

VOICEGUARD_INTERFACE_CARD = {
    "interface": INTERFACE_VERSION,
    "implementation": "DisabledVoiceGuard",
    "enabled": False,
    "status": "not integrated yet",
    "required_methods": ["status()", "screen(samples, consent, lang)"],
    "forbidden_until_phase_11": [
        "citizen.voiceguard.model", "citizen.voiceguard.voiceguard",
        "maya_lr_v1.json", "maya-capture.js", "maya-capture-worklet.js",
    ],
    "no_ai_models": True,
}


__all__ = ["INTERFACE_VERSION", "DisabledVoiceGuard", "VOICEGUARD",
           "VOICEGUARD_INTERFACE_CARD", "VoiceGuardInterface"]
