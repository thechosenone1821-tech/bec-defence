"""Root-level active eval and claims tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from evals import claims, corpus, replay, run_evals  # noqa: E402
from tools import check_claims_ledger, check_eval_drift  # noqa: E402

RESULTS = ROOT / "evals" / "results.json"
CAPABILITIES = ("citizen", "infra", "messageguard", "organs", "governance", "replay", "vigil")


def test_active_runner_drift_check_is_green():
    assert check_eval_drift.main([]) == 0
    assert run_evals.main(["--check"]) == 0
    assert check_claims_ledger.main([]) == 0


def test_one_corpus_replay_and_claims_story():
    assert corpus.main(["--check"]) == 0
    assert replay.main(["--check"]) == 0
    assert claims.main(["--check"]) == 0
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    assert tuple(sorted(results["sections"])) == tuple(sorted(CAPABILITIES))
    assert results["measurement_policy"]["model_backed"] is True
    assert results["measurement_policy"]["real_world"] == "UNMEASURED"
    assert results["sections"]["infra"]["status"] == "ok"
    assert results["sections"]["infra"]["executor_mode"] == "dry-run"
    assert results["sections"]["infra"]["hospital_demo_synthetic_organization"] is True
    assert results["sections"]["infra"]["hospital_demo_attack_steps"] >= 8
    assert results["sections"]["infra"]["hospital_demo_ledger_valid"] is True
    assert results["sections"]["infra"]["hospital_demo_live_runtime_unchanged"] is True
    assert results["sections"]["infra"]["hospital_demo_real_action_count"] == 0
    assert results["sections"]["infra"]["hospital_demo_executor_mode"] == "dry-run"
    assert results["sections"]["vigil"]["model_status"]["is_neural_active"] is True
