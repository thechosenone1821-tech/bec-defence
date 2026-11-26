"""End-to-end evaluation gates — the measured part of the detection DoD.

These encode the published targets from raksha/EVALS.md:
    - detection@HIGH (excluding deliberate gap fixtures) >= 0.90
    - false-positive rate@HIGH on genuine bank alerts <= 0.10
    - determinism: two full passes produce identical verdict hashes
"""

from raksha.evals.run_evals import run_evaluation


class TestDoDGates:
    def test_all_gates_pass(self):
        results = run_evaluation()
        failed = {name: ok for name, ok in results["gates"].items() if not ok}
        assert not failed, failed

    def test_detection_high_excl_gap(self):
        results = run_evaluation()
        det = results["detection"]["excl_gap"]
        assert det["det_high"] >= 0.90
        assert det["det_moderate"] >= 0.95

    def test_fp_high_on_bank_alerts(self):
        results = run_evaluation()
        fp = results["false_positives"]["bank_alerts"]
        assert fp["fp_high"] <= 0.10

    def test_per_language_detection(self):
        results = run_evaluation()
        for lang, blk in results["detection"]["by_lang"].items():
            core = blk["excl_gap"]
            if core["n"] == 0:
                continue
            assert core["det_high"] >= 0.85, (lang, core)

    def test_determinism_across_two_passes(self):
        results = run_evaluation()
        assert results["determinism"]["verified"] is True
        assert len(results["determinism"]["verdict_hash"]) == 16

    def test_only_deliberate_gaps_miss(self):
        results = run_evaluation()
        for miss in results["scam_misses"]:
            assert miss["category"] == "obfuscation_gap", miss

    def test_results_files_written(self):
        import json
        from pathlib import Path

        results = run_evaluation()
        results_dir = Path(__file__).resolve().parents[1] / "raksha" / "evals" / "results"
        data = json.loads((results_dir / "latest.json").read_text(encoding="utf-8"))
        assert data["determinism"]["verified"]
        assert (results_dir / "latest.md").exists()
