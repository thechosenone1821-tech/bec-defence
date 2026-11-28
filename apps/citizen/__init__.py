"""Boundary for the RAKSHA Citizen app.

The editable Citizen implementation lives here. The physical PWA assets are
served through the ``raksha-code/citizen`` compatibility tree; VIGIL is a shared
package mounted by the one Citizen service. There is no second Citizen process.
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
ACTIVE_SURFACES = (
    "apps/citizen/api.py",
    "apps/citizen/app/",
    "packages/vigil/",
)

__all__ = ["APP_NAME", "ACTIVE_SURFACES", "build_app", "score_message", "assess"]


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
