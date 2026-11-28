"""Phase 10 compatibility package for the retired standalone corpora tree.

The implementation lives in ``archive/provenance/legacy-corpora``. This shim
keeps legacy imports such as ``corpora.harness`` working for historical tests
without creating a second runtime implementation.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE_ROOT = ROOT / "raksha-code"
ARCHIVE = ROOT / "archive" / "provenance" / "legacy-corpora"
__path__ = [str(ARCHIVE)]
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))
