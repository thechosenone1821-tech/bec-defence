"""Citizen feature flags and capability card for the VIGIL-integrated build."""
from __future__ import annotations

from typing import Any, Dict

ACTIVE_MODEL = "VIGIL PrivacyNet TorchScript"
MODEL_BACKED = True
PHASE = 11
VIGIL_STATUS_PATH = "/api/citizen/vigil/status"

FEATURE_FLAGS: Dict[str, bool] = {
    "messageguard": True,
    "risk_fusion": True,
    "report": True,
    "offline_queue": True,
    "panic_1930": True,
    "family_mode": True,
    "retention": True,
    "vigil": True,
    "commander_model": False,
}


def vigil_enabled() -> bool:
    """VIGIL is an in-process model-backed Citizen capability."""
    return FEATURE_FLAGS["vigil"]


def vigil_card() -> Dict[str, Any]:
    return {
        "enabled": vigil_enabled(),
        "route": "/vigil/",
        "api_prefix": "/vigil/api",
        "status_path": VIGIL_STATUS_PATH,
        "active_model": ACTIVE_MODEL,
        "weights": "cloakpixel_privacynet_384.torchscript.pt",
        "model_backed": MODEL_BACKED,
        "executor": "none",
        "privacy_efficacy": "UNMEASURED",
        "claims_not_made": ["deepfake prevention", "modern face-recognition defeat", "anonymity guarantee"],
    }


def capability_card() -> Dict[str, Any]:
    return {
        "app": "citizen",
        "phase": PHASE,
        "service": "apps.citizen.api",
        "pwa_shell": "/app/",
        "features": dict(FEATURE_FLAGS),
        "model_backed": MODEL_BACKED,
        "active_model": ACTIVE_MODEL,
        "vigil_status_path": VIGIL_STATUS_PATH,
        "invariants": {
            "no_raw_score_to_citizen": True,
            "no_safe_verdict": True,
            "no_pii_leaves_phone": True,
            "signature_required": True,
            "governor_required": True,
        },
        "vigil": vigil_card(),
    }


__all__ = [
    "ACTIVE_MODEL", "FEATURE_FLAGS", "MODEL_BACKED", "PHASE", "VIGIL_STATUS_PATH",
    "capability_card", "vigil_card", "vigil_enabled",
]
