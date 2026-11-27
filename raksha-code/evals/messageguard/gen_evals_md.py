#!/usr/bin/env python3
"""Phase 10 compatibility wrapper for the one generated eval document.

Root ``evals/gen_evals_md.py`` generates ``EVALS.md`` and the MessageGuard
pointer. This wrapper exists so historical commands do not edit a generated doc
by hand.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "evals" / "gen_evals_md.py"


def main(argv: list[str] | None = None) -> int:
    spec = importlib.util.spec_from_file_location("raksha_unified_gen_evals_md", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the canonical eval generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main(argv or [])


if __name__ == "__main__":
    raise SystemExit(main())
