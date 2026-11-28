#!/usr/bin/env python3
"""Phase 10 CI gate: verify the one claims ledger and outward-number sources."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals import claims  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    return claims.main(["--check"])


if __name__ == "__main__":
    raise SystemExit(main())
