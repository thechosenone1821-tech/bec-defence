"""Phase 10 compatibility package for the retired standalone RAAVAN player.

The implementation lives in ``archive/provenance/legacy-raavan``. The active
Phase 9 replay player is ``evals/replay.py``; this shim exists only so legacy
tests and historical imports keep working.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE_ROOT = ROOT / "raksha-code"
ARCHIVE = ROOT / "archive" / "provenance" / "legacy-raavan"
__path__ = [str(ARCHIVE)]
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))
