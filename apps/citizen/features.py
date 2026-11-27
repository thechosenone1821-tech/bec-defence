"""Phase 4 — Citizen feature flags and capability card.

The maintainer asked for the next phase without running AI models. This module
is the single place where that instruction is made executable: VoiceGuard/MAYA,
the MAYA classifier, and the local Commander/SLM are all disabled by default.
"""
from __future__ import annotations

from typing import Any, Dict

NO_AI_MODELS = True
PHASE = 4

FEATURE_FLAGS: Dict[str, bool] = {
    "messageguard": True,
    "risk_fusion": True,
    "report": True,
    "offline_queue": True,
    "panic_1930": True,
    "family_mode": True,
    "retention": True,
    "voiceguard": False,
    "maya_capture": False,
    "commander_model": False,
}


def voiceguard_enabled() -> bool:
    """VoiceGuard is frozen behind a hard-disabled flag. No env override."""
    return False


def no_ai_models() -> bool:
    return True


def capability_card() -> Dict[str, Any]:
    return {
        "app": "citizen",
        "phase": PHASE,
        "service": "apps.citizen.api",
        "pwa_shell": "/app/",
        "features": dict(FEATURE_FLAGS),
        "no_ai_models": NO_AI_MODELS,
        "invariants": {
            "no_raw_score_to_citizen": True,
            "no_safe_verdict": True,
            "no_pii_leaves_phone": True,
            "signature_required": True,
            "governor_required": True,
        },
        "voiceguard": {
            "enabled": False,
            "status": "not integrated yet",
            "model_invoked": False,
        },
    }


__all__ = ["FEATURE_FLAGS", "NO_AI_MODELS", "PHASE", "capability_card",
           "no_ai_models", "voiceguard_enabled"]
