"""Compatibility wrapper: one shared Phase 3 ledger CLI.

    python -m spine.ledger_cli verify [--ledger PATH]
    python -m packages.ledger.cli verify [--ledger PATH]
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from packages.contracts.config import DEFAULT_LEDGER
    from packages.ledger.cli import main as _shared_main
except ImportError:  # pragma: no cover - minimal standalone checkout
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from packages.contracts.config import DEFAULT_LEDGER
    from packages.ledger.cli import main as _shared_main

DEFAULT_LEDGER_PATH = str(DEFAULT_LEDGER)


def main() -> int:
    return _shared_main()


if __name__ == "__main__":
    sys.exit(main())
