"""Part 4 Phase 4 — the fixture corpus and the published rates.

The tests here do not assert that Organ 1 scores 0.83. Pinning a number would
make the suite fail every time a case is added, and it would tell a reader
nothing about whether the number is meaningful. They assert the properties that
make the numbers *trustworthy*:

* every corpus is labelled, deterministic and provenance-stamped
* no case is scored without an oracle independent of the detector
* an organ that always fires cannot pass the corpus
* the identifiability controls behave as controls (identical input, identical
  output, regardless of label)
* the published rates are the ones this run measured
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corpora.harness import (build_case, build_identically, constant_rate_baseline,
                             list_corpora, load_corpus, score_corpus)
from corpora.run_corpus import ADAPTERS, compile_payload, evaluate_all


CORPORA = list_corpora()


# --------------------------------------------------------------------------- #
# Corpus integrity
# --------------------------------------------------------------------------- #
class TestEveryCorpusIsHonest:
    def test_eight_organs_each_have_a_corpus(self):
        organs = set()
        for name in CORPORA:
            organs.add(load_corpus(name)["organ"])
        assert len(organs) == 8, f"expected 8 organs, found {sorted(organs)}"
        assert organs == set(ADAPTERS), (
            f"corpus/adapter mismatch: {organs ^ set(ADAPTERS)}"
        )

    def test_every_corpus_declares_synthetic_provenance(self):
        """A captured-traffic corpus needs its own labelling argument, and this
        phase does not have one. Refusing to score it is the correct behaviour."""
        for name in CORPORA:
            corpus = load_corpus(name)
            assert corpus["provenance"] == "synthetic", name
            assert corpus.get("provenance_note"), f"{name} lacks a provenance note"
            assert corpus.get("positive_definition"), f"{name} lacks a positive definition"
            assert corpus.get("negative_definition"), f"{name} lacks a negative definition"

    def test_every_case_carries_a_generator_and_a_rationale(self):
        for name in CORPORA:
            for case in load_corpus(name)["cases"]:
                assert case["generator"].strip(), f"{name}:{case['id']}"
                assert len(case["rationale"]) > 40, (
                    f"{name}:{case['id']} rationale is too thin to review"
                )
                assert case["label"] in ("attack", "benign")

    def test_both_labels_are_present_in_every_corpus(self):
        """A corpus of only attacks scores 1.00 always and measures nothing."""
        for name in CORPORA:
            labels = {c["label"] for c in load_corpus(name)["cases"]}
            assert labels == {"attack", "benign"}, f"{name} has only {labels}"

    def test_every_corpus_has_at_least_one_adversarial_benign_case(self):
        """Benign cases must include the near-misses, not just the easy ones.

        Every corpus that scores well does so because its benign cases were
        chosen to be distinguishable. Tagging the hard ones makes the claim
        checkable instead of hopeful.
        """
        hard = {
            "organ1_spectral_condensation.json": {"homogeneous-fleet", "correlated"},
            "organ2_cookie_turbulence.json": {"human-expert"},
            "organ3_bragg_injection.json": {"procedural"},
            "organ4_lyapunov_trajectory.json": {"smooth"},
            "organ5_landauer_thermal.json": {"explained"},
            "organ6_page_curve.json": {"no-write"},
            "organ7_muts_splice.json": {"not-applicable"},
            "organ8_percolation.json": {"must-refuse"},
        }
        for name, required in hard.items():
            families = {c.get("family") for c in load_corpus(name)["cases"]
                        if c["label"] == "benign"}
            assert required <= families, f"{name} is missing {required - families}"


class TestDeterminism:
    def test_every_matrix_case_builds_identically_twice(self):
        for name in CORPORA:
            for case in load_corpus(name)["cases"]:
                if case.get("kind", "session_matrix") == "session_matrix":
                    assert build_identically(case), f"{name}:{case['id']} is not deterministic"

    def test_a_different_seed_gives_a_different_matrix(self):
        """Determinism must not be achieved by generating a constant."""
        case = load_corpus("organ1_spectral_condensation.json")["cases"][0]
        a = build_case(case, seed=1)
        b = build_case(case, seed=2)
        assert not np.array_equal(a, b)

    def test_the_whole_report_is_reproducible(self):
        first = evaluate_all()
        second = evaluate_all()
        for a, b in zip(first["reports"], second["reports"]):
            assert a.get("detection_rate") == b.get("detection_rate")
            assert a.get("false_positive_rate") == b.get("false_positive_rate")
            assert [r["fired"] for r in a["rows"]] == [r["fired"] for r in b["rows"]]


# --------------------------------------------------------------------------- #
# Scoring machinery
# --------------------------------------------------------------------------- #
class TestScoringIsNotGameable:
    def test_an_always_fire_detector_scores_perfectly_on_detection(self):
        """The harness must expose this, not hide it: it is why FPR is published."""
        corpus = load_corpus("organ1_spectral_condensation.json")
        rep = score_corpus(corpus, lambda case, payload: True)
        assert rep["detection_rate"] == 1.0
        assert rep["false_positive_rate"] == 1.0
        # Precision is tp/(tp+fp) over the *scored* cases: 6 attacks, 5 benign.
        # (An earlier draft asserted 0.5 — arithmetic from the 5-and-5 layout
        # before the corpus grew. The test was wrong, not the code.)
        assert rep["precision"] == pytest.approx(6 / 11)

    def test_a_never_fire_detector_scores_zero(self):
        corpus = load_corpus("organ1_spectral_condensation.json")
        rep = score_corpus(corpus, lambda case, payload: False)
        assert rep["detection_rate"] == 0.0
        assert rep["false_positive_rate"] == 0.0

    def test_a_perfect_detector_is_distinguishable_from_a_lazy_one(self):
        # organ1 is the matrix kind, so the default builder works here without
        # a supplied compiler. organ6 needs one; using it here was the mistake.
        corpus = load_corpus("organ1_spectral_condensation.json")
        perfect = score_corpus(corpus, lambda case, payload: case["label"] == "attack")
        lazy = score_corpus(corpus, lambda case, payload: True)
        assert perfect["precision"] == 1.0
        assert lazy["precision"] < 1.0

    def test_controls_are_excluded_from_every_rate(self):
        corpus = load_corpus("organ1_spectral_condensation.json")
        rep = score_corpus(corpus, lambda case, payload: case["label"] == "attack")
        assert rep["n_control"] == 2
        total = rep["n_attack"] + rep["n_benign"] + rep["n_control"]
        assert total == len(corpus["cases"])

    def test_a_control_case_cannot_improve_a_score(self):
        """Flipping a control's label must not change the published rate."""
        corpus = load_corpus("organ1_spectral_condensation.json")
        base = score_corpus(corpus, lambda case, payload: case["label"] == "attack")
        mutated = json.loads(json.dumps(corpus))
        for case in mutated["cases"]:
            if case.get("role") == "control":
                case["label"] = "benign" if case["label"] == "attack" else "attack"
        after = score_corpus(mutated, lambda case, payload: case["label"] == "attack")
        assert after["detection_rate"] == base["detection_rate"]
        assert after["false_positive_rate"] == base["false_positive_rate"]


# --------------------------------------------------------------------------- #
# The identifiability proof (Organ 1)
# --------------------------------------------------------------------------- #
class TestIdentifiability:
    """The finding this phase produced, expressed as an executable claim.

    If two populations are drawn from the same law, no function of the session
    matrix can tell them apart. Organ 1's score is therefore bounded by the
    data it is given, not only by the statistic it computes.
    """

    def _same_law(self, n_a: int, n_b: int, seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed)
        axis = np.array([1.0, 0.0, 0.0, 0.0, 0.0])
        a = np.outer(rng.normal(0, 6.0, n_a), axis) + rng.normal(0, 0.05, (n_a, 5))
        b = np.outer(rng.normal(0, 6.0, n_b), axis) + rng.normal(0, 0.05, (n_b, 5))
        return np.vstack([a, b])

    def test_the_organ_cannot_see_a_difference_that_is_not_there(self):
        from sentinel.shields.ring1_perimeter_identity import BECSpectralFilter
        organ = BECSpectralFilter()
        X = self._same_law(30, 10, seed=99)
        # Relabel the same rows and analyse again: the matrix is unchanged.
        first = organ.analyze(X.copy())["condensation_ratio"]
        organ.drain_events()
        second = BECSpectralFilter().analyze(X.copy())["condensation_ratio"]
        assert first == pytest.approx(second)
        assert first > 0.99, (
            "a homogeneous fleet condenses to ~1.0 regardless of how many of "
            "its members are hostile — the statistic is measuring homogeneity"
        )

    def test_condensation_is_invariant_to_the_bot_fraction(self):
        from sentinel.shields.ring1_perimeter_identity import BECSpectralFilter
        ratios = []
        for n_bots in (5, 10, 20, 30, 35):
            organ = BECSpectralFilter()
            X = self._same_law(40 - n_bots, n_bots, seed=5)
            ratios.append(organ.analyze(X)["condensation_ratio"])
            organ.drain_events()
        assert max(ratios) - min(ratios) < 0.01, (
            f"ratio moved with the label: {ratios}"
        )

    def test_the_two_control_cases_fire_identically(self):
        """X1 and A7 are different cases with opposite labels and the same law."""
        corpus = load_corpus("organ1_spectral_condensation.json")
        rep = score_corpus(corpus, ADAPTERS["BEC_SPECTRAL_PROJECTOR"],
                           compile_payload=compile_payload)
        by_id = {c["id"]: c for c in rep["controls"]}
        assert by_id["X1-identifiability-setup"]["fired"] == \
            by_id["A7-identical-law-enemy-label"]["fired"], (
                "the organ's verdict depended on which group we called hostile"
            )


# --------------------------------------------------------------------------- #
# The published numbers
# --------------------------------------------------------------------------- #
class TestPublishedRates:
    def test_the_report_scores_all_eight_organs(self):
        bundle = evaluate_all()
        scored = [r for r in bundle["reports"] if "refused" not in r]
        assert len(scored) == 8
        for rep in scored:
            assert rep["detection_rate"] is not None
            assert rep["false_positive_rate"] is not None
            assert rep["rows"], rep["organ"]

    def test_a_corpus_without_provenance_is_refused(self, tmp_path, monkeypatch):
        """The refusal must come from the loader, on a real file.

        An earlier draft deleted the field from an in-memory dict and then
        asserted a raise from a call that never read it. That test could not
        fail, and a test that cannot fail is worse than none.
        """
        import corpora.harness as harness
        original = load_corpus("organ6_page_curve.json")
        broken = dict(original)
        broken.pop("provenance")
        target = tmp_path / "organ9_broken.json"
        target.write_text(json.dumps(broken))
        monkeypatch.setattr(harness, "ORGAN_DIR", str(tmp_path))
        with pytest.raises(ValueError, match="provenance"):
            harness.load_corpus("organ9_broken.json")

    def test_organ1_publishes_a_high_false_positive_rate(self):
        """
        Not a bug report — a recorded finding. Three of five benign families
        fire. If a future threshold change fixes this, the assertion fails and
        the spec's Phase 4 table must be updated with the new number rather
        than quietly left stale.
        """
        bundle = evaluate_all()
        organ1 = next(r for r in bundle["reports"]
                      if r.get("organ") == "BEC_SPECTRAL_PROJECTOR")
        assert organ1["false_positive_rate"] >= 0.4, (
            f"Organ 1 FPR is now {organ1['false_positive_rate']:.2f}. If this "
            f"was fixed deliberately, update the Phase 4 report and this test."
        )

    def test_organ3_cannot_separate_injection_from_procedural_text(self):
        bundle = evaluate_all()
        organ3 = next(r for r in bundle["reports"]
                      if r.get("organ") == "BRAGG_FFT_FIREWALL")
        assert organ3["false_positive_rate"] >= 0.5, (
            "Bragg now separates injections from listicles. That would be news; "
            "update the report with the corpus cases that prove it."
        )

    def test_two_organs_publish_a_clean_signal(self):
        """Page-Curve and MUTS are mechanistic, not statistical — and they show it."""
        bundle = evaluate_all()
        for organ_name in ("ENDPOINT_PAGE_CURVE", "MUTS_EBPF_REPAIR"):
            rep = next(r for r in bundle["reports"] if r.get("organ") == organ_name)
            assert rep["detection_rate"] == 1.0
            assert rep["false_positive_rate"] == 0.0
