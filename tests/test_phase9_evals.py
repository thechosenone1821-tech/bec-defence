"""Phase 9 deterministic eval tests — no AI, no model endpoints, no VoiceGuard."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from evals import claims, corpus, replay, run_evals  # noqa: E402
from tools import check_claims_ledger, check_eval_drift  # noqa: E402

RESULTS = ROOT / "evals" / "results.json"
CAPABILITIES = ("citizen", "messageguard", "organs", "governance", "replay")


def test_unified_runner_drift_check_is_green():
    assert check_eval_drift.main([]) == 0
    assert run_evals.main(["--check"]) == 0


def test_one_corpus_and_one_replay_player_are_current():
    assert corpus.main(["--check"]) == 0
    assert replay.main(["--check"]) == 0


def test_claims_ledger_verifies():
    assert check_claims_ledger.main([]) == 0
    claims.verify()


def test_every_capability_has_conditioned_status():
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    assert results["capability_count"] == len(CAPABILITIES)
    assert set(results["sections"]) == set(CAPABILITIES)
    for name in CAPABILITIES:
        section = results["sections"][name]
        assert section["status"] == "ok"
        assert any(label in section["condition"] for label in claims.ALLOWED_CONDITIONS)
    assert results["measurement_policy"]["real_world"] == "UNMEASURED"
    assert results["voiceguard"]["included_in_runner"] is False
    assert results["voiceguard"]["future_phase"] == "Eleven"


def test_voiceguard_evals_stay_out_and_generated_docs_are_current():
    runner = (ROOT / "evals" / "run_evals.py").read_text(encoding="utf-8")
    corpus_source = (ROOT / "evals" / "corpus.py").read_text(encoding="utf-8")
    replay_source = (ROOT / "evals" / "replay.py").read_text(encoding="utf-8")
    assert "run_maya" not in runner + corpus_source + replay_source
    assert "VoiceGuard" in runner
    assert "excluded" in corpus_source.lower()
    # The runner's --check compares corpus, results, EVALS.md, claims ledger,
    # pointer and legacy results; a zero exit means none were hand-edited.
    assert run_evals.main(["--check"]) == 0
