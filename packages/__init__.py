"""Shared RAKSHA packages — the only allowed cross-app integration layer."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_LEGACY_CODE_ROOT = _REPO_ROOT / "raksha-code"
if str(_LEGACY_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LEGACY_CODE_ROOT))

PACKAGE_NAMES = ("contracts", "spine", "governance", "ledger")

__all__ = ["PACKAGE_NAMES"]
