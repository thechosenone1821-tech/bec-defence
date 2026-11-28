#!/usr/bin/env python3
"""Active MessageGuard single-source checker."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from apps.citizen import messageguard as mg  # noqa: E402
from evals.messageguard import compute_results  # noqa: E402
from tools import run_phase4_pytest  # noqa: E402


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main(argv: list[str] | None = None) -> int:
    try:
        canonical = ROOT / "apps" / "citizen" / "messageguard" / "__init__.py"
        check(pathlib.Path(mg.__file__).resolve() == canonical.resolve(),
              "MessageGuard compatibility import is not the canonical scorer")
        check(importlib.util.find_spec("raksha.messageguard") is None,
              "an archived alternate scorer became importable")
        check(importlib.util.find_spec("messageguard") is None,
              "a second top-level scorer became importable")
        check(mg.SUPPORTED_LANGS == ("auto", "en", "hi", "te", "hinglish"),
              "MessageGuard language surface changed")
        check("538 hand-authored/in-distribution fixtures" in mg.ENGINE,
              "MessageGuard engine scope changed")
        check("real-world UNMEASURED" in mg.ENGINE,
              "MessageGuard must condition real-world claims as UNMEASURED")

        results = compute_results()
        check(results["status"] == "ok", "MessageGuard corpus measurement failed")
        check(results["corpus"]["fixture_total"] == 538, "MessageGuard corpus size changed")
        check(results["corpus"]["scam_total"] == 402, "MessageGuard scam corpus size changed")
        check(results["corpus"]["benign_total"] == 136, "MessageGuard benign corpus size changed")
        check(results["overall"]["tp_moderate"] == 399, "MessageGuard true positives changed")
        check(results["overall"]["tn_moderate"] == 122, "MessageGuard true negatives changed")
        check(results["overall"]["fp_moderate"] == 14, "MessageGuard false positives changed")
        check(results["overall"]["fn_moderate"] == 3, "MessageGuard false negatives changed")

        check("packages/vigil/tests" in run_phase4_pytest.ACTIVE_PYTEST_PATHS,
              "VIGIL runtime tests are outside the active pytest surface")
        check(len(run_phase4_pytest.ACTIVE_NODE_TESTS) == 4,
              "active browser test set changed")
        check(all((ROOT / rel).is_file() for rel in run_phase4_pytest.ACTIVE_NODE_TESTS),
              "an active browser test file is missing")
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("OK: one MessageGuard scorer, one corpus, one active test surface")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
