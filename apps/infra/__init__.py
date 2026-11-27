"""Phase 2 boundary for the RAKSHA Infra / Sentinel app."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LEGACY_CODE_ROOT = _REPO_ROOT / "raksha-code"
if str(_LEGACY_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LEGACY_CODE_ROOT))

APP_NAME = "infra"

__all__ = ["APP_NAME", "create_app"]


def __getattr__(name: str) -> Any:
    if name == "create_app":
        from .backend.app import create_app
        return create_app
    raise AttributeError(name)
