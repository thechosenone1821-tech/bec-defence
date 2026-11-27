"""Phase 2 boundary for the RAKSHA Citizen app.

The editable Citizen implementation lives here. The frozen VoiceGuard/MAYA tree
and the existing PWA assets remain under ``raksha-code/citizen``; this package
adds that legacy directory to its search path so the frozen seam is importable
without moving or editing any VoiceGuard/MAYA file.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LEGACY_CODE_ROOT = _REPO_ROOT / "raksha-code"
if str(_LEGACY_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LEGACY_CODE_ROOT))

_LEGACY_CITIZEN_DIR = _LEGACY_CODE_ROOT / "citizen"
if str(_LEGACY_CITIZEN_DIR) not in __path__:
    __path__.append(str(_LEGACY_CITIZEN_DIR))

APP_NAME = "citizen"
FROZEN_SEAMS = (
    "raksha-code/citizen/voiceguard/",
    "raksha-code/citizen/app/maya-capture*.js",
    "raksha-code/citizen/voiceguard/MODEL_CARD.md",
    "raksha-code/citizen/voiceguard/maya_lr_v1.json",
)

__all__ = ["APP_NAME", "FROZEN_SEAMS", "build_app", "score_message", "assess"]


def __getattr__(name: str) -> Any:
    """Lazy exports keep importing the app boundary cheap and side-effect free."""
    if name == "build_app":
        from .api import build_app
        return build_app
    if name == "score_message":
        from .messageguard import score_message
        return score_message
    if name == "assess":
        from .risk import assess
        return assess
    raise AttributeError(name)
