"""Part 4 Phase 5 — calibration, and the evidence that does not exist.

Phase 5's deliverable is "thresholds either earn their values or are replaced".
The tests here enforce the part of that sentence a program can enforce: a
threshold may only be reported as calibrated when the data justifies it, and the
absence of data must produce `INSUFFICIENT_DATA` rather than a reused default
dressed up as an answer.

They also pin the phase's real finding: Organ 3 blocks most canonical project
documents, and it does so with the rule whose threshold was believed to be
secondary. Phase 2 added new app/package docs and compatibility symlinks; the
collector now skips symlink duplicates so each document is counted once.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corpora.capture import (CaptureError, calibrate, read_capture, summarize,
                             write_capture)
from corpora.calibrate_organs import REGISTRY, status
from corpora.real_documents import collect_documents, measure


# --------------------------------------------------------------------------- #
# Capture loading must be strict
# --------------------------------------------------------------------------- #
class TestCaptureFormat:
    def _row(self, **over):
        row = {"organ": "COOKIE_FLUID_TURBULENCE", "label": "benign",
               "captured_at": "2026-11-23T10:00:00Z", "source": "gw-01",
               "features": {"re_beh": 1100.0}}
        row.update(over)
        return row

    def test_a_well_formed_capture_round_trips(self, tmp_path):
        path = tmp_path / "cap.jsonl"
        n = write_capture(str(path), [self._row(), self._row(label="attack")])
        assert n == 2
        rows = read_capture(str(path))
        assert len(rows) == 2
        assert {r["label"] for r in rows} == {"attack", "benign"}

    @pytest.mark.parametrize("bad,why", [
        ({"label": "malicious"}, "bad label"),
        ({"features": {}}, "empty features"),
        ({"features": {"re_beh": "fast"}}, "non-numeric feature"),
        ({"features": {"re_beh": float("nan")}}, "non-finite feature"),
    ])
    def test_a_malformed_line_is_refused_not_skipped(self, tmp_path, bad, why):
        """Skipping a bad line would calibrate on an unknown subset of traffic."""
        path = tmp_path / "cap.jsonl"
        path.write_text(json.dumps(self._row(**bad)) + "\n")
        with pytest.raises(CaptureError):
            read_capture(str(path))

    def test_a_bad_line_among_good_ones_is_refused(self, tmp_path):
        """The gap a single-line test cannot see.

        With one line, a loader that skips bad JSON falls through to the
        "no observations" check and still raises — so the skip is invisible and
        the test passes against a broken loader. (The Phase 5 mutation run found
        exactly this: M3 survived.) Three lines make the difference observable:
        a skipping loader returns 2 rows and calibrates on 66 % of the capture,
        silently.
        """
        good_a = json.dumps(self._row())
        good_b = json.dumps(self._row(label="attack"))
        path = tmp_path / "cap.jsonl"
        path.write_text(f"{good_a}\nNOT JSON\n{good_b}\n")
        with pytest.raises(CaptureError, match="not JSON"):
            read_capture(str(path))

    def test_a_bad_feature_among_good_rows_is_refused(self, tmp_path):
        """Same reasoning for a semantic error, not just a syntax error."""
        path = tmp_path / "cap.jsonl"
        path.write_text(json.dumps(self._row()) + "\n"
                        + json.dumps(self._row(features={"re_beh": float("inf")})) + "\n")
        with pytest.raises(CaptureError, match="finite"):
            read_capture(str(path))

    def test_a_missing_field_is_refused(self, tmp_path):
        path = tmp_path / "cap.jsonl"
        row = self._row()
        row.pop("organ")
        path.write_text(json.dumps(row) + "\n")
        with pytest.raises(CaptureError, match="organ"):
            read_capture(str(path))

    def test_an_empty_capture_is_refused(self, tmp_path):
        path = tmp_path / "cap.jsonl"
        path.write_text("\n\n")
        with pytest.raises(CaptureError, match="no observations"):
            read_capture(str(path))

    def test_summarize_counts_both_classes(self, tmp_path):
        path = tmp_path / "cap.jsonl"
        write_capture(str(path), [self._row()] * 3 + [self._row(label="attack")] * 2)
        s = summarize(read_capture(str(path)), "COOKIE_FLUID_TURBULENCE")
        assert (s["n_benign"], s["n_attack"]) == (3, 2)


# --------------------------------------------------------------------------- #
# Calibration may not invent a threshold
# --------------------------------------------------------------------------- #
class TestCalibrationRefuses:
    def _rows(self, n_attack, n_benign, attack_val=5000.0, benign_val=1100.0):
        rows = []
        for _ in range(n_benign):
            rows.append({"organ": "COOKIE_FLUID_TURBULENCE", "label": "benign",
                         "features": {"re_beh": benign_val}})
        for _ in range(n_attack):
            rows.append({"organ": "COOKIE_FLUID_TURBULENCE", "label": "attack",
                         "features": {"re_beh": attack_val}})
        return rows

    def test_no_data_is_insufficient_not_calibrated(self):
        rep = calibrate([], "COOKIE_FLUID_TURBULENCE", "re_beh")
        assert rep["status"] == "INSUFFICIENT_DATA"
        assert rep["default_in_use"] is None
        assert "0 attack" in rep["reason"]

    def test_benign_only_is_insufficient(self):
        """An operator can collect benign traffic on day one. Attacks need an
        incident. Benign-only data cannot pick a threshold, and saying so is the
        whole point of this phase."""
        rows = self._rows(n_attack=0, n_benign=500)
        rep = calibrate(rows, "COOKIE_FLUID_TURBULENCE", "re_beh")
        assert rep["status"] == "INSUFFICIENT_DATA"
        assert "have 0 attack" in rep["reason"]

    def test_just_under_the_minimum_is_insufficient(self):
        rows = self._rows(n_attack=29, n_benign=500)
        rep = calibrate(rows, "COOKIE_FLUID_TURBULENCE", "re_beh")
        assert rep["status"] == "INSUFFICIENT_DATA"
        assert "29 attack" in rep["reason"]

    def test_overlapping_distributions_are_not_separable(self):
        """If attacks and benign occupy the same range, no threshold works and
        the tool must say so rather than pick the midpoint of nothing."""
        rows = []
        for i in range(100):
            v = 1000.0 + (i % 20) * 50.0
            rows.append({"organ": "COOKIE_FLUID_TURBULENCE", "label": "benign",
                         "features": {"re_beh": v}})
            rows.append({"organ": "COOKIE_FLUID_TURBULENCE", "label": "attack",
                         "features": {"re_beh": v}})
        rep = calibrate(rows, "COOKIE_FLUID_TURBULENCE", "re_beh")
        assert rep["status"] == "NOT_SEPARABLE"
        assert rep["default_in_use"] is None

    def test_a_separable_capture_is_calibrated_and_says_why(self):
        rows = self._rows(n_attack=60, n_benign=60)
        rep = calibrate(rows, "COOKIE_FLUID_TURBULENCE", "re_beh")
        assert rep["status"] == "CALIBRATED"
        assert rep["threshold"] is not None
        assert rep["benign_p95"] < rep["threshold"] < rep["attack_p05"] or \
            rep["threshold"] <= rep["attack_p05"]
        assert "attack" in rep["reason"] and "benign" in rep["reason"]

    def test_low_direction_is_handled(self):
        """lambda2 flags when BELOW threshold; the quantile logic must mirror."""
        rows = []
        for _ in range(60):
            rows.append({"organ": "BRAGG_FFT_FIREWALL", "label": "benign",
                         "features": {"fiedler_lambda2": 0.20}})
            rows.append({"organ": "BRAGG_FFT_FIREWALL", "label": "attack",
                         "features": {"fiedler_lambda2": 0.01}})
        rep = calibrate(rows, "BRAGG_FFT_FIREWALL", "fiedler_lambda2", direction="low")
        assert rep["status"] == "CALIBRATED"
        assert 0.01 < rep["threshold"] < 0.20

    def test_calibration_never_returns_a_value_for_insufficient_data(self):
        for n_a, n_b in ((0, 0), (0, 100), (100, 0), (10, 10), (29, 31)):
            rep = calibrate(self._rows(n_a, n_b), "COOKIE_FLUID_TURBULENCE", "re_beh")
            assert "threshold" not in rep
            assert rep["status"] in ("INSUFFICIENT_DATA", "NOT_SEPARABLE")


# --------------------------------------------------------------------------- #
# The registry: nothing is silently called calibrated
# --------------------------------------------------------------------------- #
class TestRegistry:
    def test_with_no_capture_every_threshold_is_insufficient(self):
        reports = status([])
        assert len(reports) == len(REGISTRY)
        for rep in reports:
            assert rep["status"] == "INSUFFICIENT_DATA"
            assert rep["default_in_use"] == rep["default"]

    def test_every_registry_entry_names_where_its_default_came_from(self):
        for entry in REGISTRY:
            assert entry["origin"] in ("unvalidated", "documented-deviation",
                                       "calibrated-from-capture"), entry["symbol"]
            assert entry["note"].strip(), entry["symbol"]

    def test_a_seeded_capture_calibrates_only_what_it_covers(self, tmp_path):
        """Writing a capture for one organ must leave the other six insufficient."""
        path = tmp_path / "cookie.jsonl"
        rows = []
        for _ in range(40):
            rows.append({"organ": "COOKIE_FLUID_TURBULENCE", "label": "benign",
                         "features": {"re_beh": 900.0}})
            rows.append({"organ": "COOKIE_FLUID_TURBULENCE", "label": "attack",
                         "features": {"re_beh": 90000.0}})
        write_capture(str(path), rows)
        reports = status([str(path)])
        by_symbol = {r["symbol"]: r for r in reports}
        assert by_symbol["re_crit"]["status"] == "CALIBRATED"
        assert by_symbol["rank1_threshold"]["status"] == "INSUFFICIENT_DATA"
        assert by_symbol["cliff_threshold"]["status"] == "INSUFFICIENT_DATA"


# --------------------------------------------------------------------------- #
# The real-document finding
# --------------------------------------------------------------------------- #
class TestOrgan3OnRealDocuments:
    """The only out-of-sample evidence this repository can produce.

    The documents were written over months for reasons unrelated to the
    detector. If the firewall blocks them, it blocks the documentation an agent
    would be asked to read.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def report(cls):
        # isolate_rules=False: the per-rule attribution costs three full passes
        # over ~53k words (~2.5 min) and is measured separately, once, by
        # test_the_fiedler_rule_carries_every_block below.
        return measure(collect_documents(), isolate_rules=False)

    def test_the_documents_are_real_and_substantial(self, report):
        assert report["n_documents"] >= 20
        assert report["total_words"] >= 20000

    def test_oversized_documents_are_reported_not_silently_dropped(self, report):
        """The organ's quadratic memory forces a size cap. A cap that vanishes
        documents would make the corpus look complete when it is not."""
        assert report["size_cap_tokens"] > 0
        for path, tokens in report["skipped_too_large"]:
            assert tokens > report["size_cap_tokens"], (path, tokens)

    def test_organ3_blocks_almost_every_real_document(self, report):
        assert report["blocked_pct"] >= 0.88, (
            f"Organ 3 now passes too much real documentation ({report['blocked']}/"
            f"{report['n_documents']} blocked = {report['blocked_pct']:.1%}). "
            "That would be a fix; update §5.4 and this test together."
        )

    def test_the_peak_rule_never_fires_on_real_documents(self, report):
        assert report["flagged_by_peak"] == 0, (
            "the peak rule started firing on real documents; the finding that it "
            "is inert no longer holds"
        )

    def test_the_fiedler_rule_carries_every_block(self, report):
        """Run the attribution once, on a small sample of blocked documents.

        The sample is three of the *smallest blocked* canonical documents:
        attribution re-screens each one three times, and the organ's quadratic
        memory makes a larger sample cost gigabytes rather than seconds.
        """
        blocked_paths = {row["path"] for row in report["rows"] if not row["allowed"]}
        docs = sorted(
            ((p, t) for p, t in collect_documents() if p in blocked_paths),
            key=lambda dt: len(dt[1].split()),
        )[:3]
        sampled = measure(docs, isolate_rules=True)
        assert sampled["blocked"] == len(docs) > 0
        assert sampled["peak_only_would_block"] == 0
        assert sampled["fiedler_only_would_block"] == sampled["blocked"]

    def test_one_rare_token_disconnects_a_normal_sentence(self):
        """The mechanism, at the smallest possible scale.

        lambda2 is the algebraic connectivity of a kNN token graph. Add a token
        that is unlike its neighbours and the graph splits; a disconnected graph
        has lambda2 = 0.
        """
        from sentinel.shields.ring2_ai_defense import BraggFFTFirewall
        clean = "the server read the log file and wrote a report"
        base = BraggFFTFirewall()
        base_result = base.screen(clean)
        base.drain_events()

        odd = clean + " xq7zvm"
        organ = BraggFFTFirewall()
        odd_result = organ.screen(odd)
        organ.drain_events()

        assert odd_result["fiedler_lambda2"] < base_result["fiedler_lambda2"], (
            "adding a rare token did not reduce connectivity; the mechanism "
            "described in §5.4 has changed"
        )

    def test_the_documents_would_be_read_by_an_agent(self, report):
        """Not a property of the code — a statement of the consequence.

        Every blocked path is a document an agent could be asked to summarise.
        The assertion is that the blocked set is not some pathological subset.
        """
        blocked = [r["path"] for r in report["rows"] if not r["allowed"]]
        assert any("README" in p.upper() for p in blocked), (
            "the README was expected among the blocked documents"
        )
