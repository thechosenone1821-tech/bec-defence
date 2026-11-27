#!/usr/bin/env python3
"""Phase 9/10 — the one eval drift gate.

Runs the canonical runner in --check mode, then verifies the claims ledger.
No files are written and no AI/model-dependent test is loaded.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals import claims, run_evals  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    if run_evals.main(["--check"]) != 0:
        return 1
    if claims.main(["--check"]) != 0:
        return 1
    print("OK: eval drift check green; generated docs and claims ledger are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
