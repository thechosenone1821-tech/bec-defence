#!/usr/bin/env python3
"""Phase 10 compatibility shim for the retired legacy M6 eval runner.

The one active runner is root ``evals/run_evals.py``. This module preserves the
historical ``evals.run_evals.sign_event`` identity used by the Phase 3 contract
test and delegates the CLI to the canonical runner. It imports no model, legacy
spine bus, Commander endpoint or frozen VoiceGuard/MAYA eval.
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.contracts.envelope import sign_event  # noqa: E402

RUNNER = ROOT / "evals" / "run_evals.py"


def _runner():
    spec = importlib.util.spec_from_file_location("raksha_unified_run_evals", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the canonical eval runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compatibility wrapper for make eval")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    return _runner().main(["--check"] if args.check else [])


if __name__ == "__main__":
    raise SystemExit(main())
