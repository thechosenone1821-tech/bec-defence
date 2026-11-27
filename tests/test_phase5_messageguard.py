"""Root-side active MessageGuard single-source tests."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from apps.citizen import messageguard as mg  # noqa: E402
from evals.messageguard import compute_results  # noqa: E402
from tools import check_phase5_messageguard  # noqa: E402


def test_messageguard_checker_is_green():
    assert check_phase5_messageguard.main([]) == 0


def test_one_deterministic_scorer_and_active_corpus():
    results = compute_results()
    assert results["status"] == "ok"
    assert results["corpus"]["fixture_total"] == 538
    assert mg.SUPPORTED_LANGS == ("auto", "en", "hi", "te", "hinglish")
    assert "real-world UNMEASURED" in mg.ENGINE
