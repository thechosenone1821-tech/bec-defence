"""Repo-root pytest path setup for the Phase 2 modular layout."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CODE_ROOT = ROOT / "raksha-code"
for path in (ROOT, CODE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
