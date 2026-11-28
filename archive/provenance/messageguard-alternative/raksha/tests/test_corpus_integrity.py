"""Corpus integrity tests — the mechanical part of the detection DoD.

Spec definition of done: fixture corpus >= 300 messages with per-language
coverage, and a genuine-bank-alert set for false-positive measurement.
"""

import json
import unicodedata

import pytest

from raksha.evals.run_evals import BANK_ALERT_CATEGORIES, LANGS, load_corpus

FIXTURES = load_corpus()
SCAM = [r for r in FIXTURES if r["label"] == "scam"]
BENIGN = [r for r in FIXTURES if r["label"] == "benign"]

VALID_CATEGORIES = {
    "otp_request",
    "upi_collect",
    "digital_arrest",
    "police_cbi_ed",
    "rbi_freeze",
    "electricity_cutoff",
    "kyc_expiry",
    "lottery_prize",
    "loan_fee",
    "refund_fee",
    "sim_suspend",
    "parcel_customs",
    "job_task",
    "card_block_phish",
    "bail_emergency",
    "insurance_lapse",
    "tax_refund",
    "obfuscation_gap",
    "bank_txn",
    "otp_notice",
    "kyc_official",
    "loan_emi",
    "salary",
    "bill_receipt",
    "bank_fraud_alert",
    "marketing",
    "govt_service",
    "delivery",
}


class TestDefinitionOfDoneCounts:
    def test_scam_corpus_at_least_300(self):
        assert len(SCAM) >= 300

    def test_per_language_scam_coverage(self):
        for lang in LANGS:
            n = sum(1 for r in SCAM if r["lang"] == lang)
            assert n >= 20, f"{lang}: {n}"

    def test_benign_corpus_exists(self):
        assert len(BENIGN) >= 90

    def test_genuine_bank_alerts_at_least_60(self):
        bank = [r for r in BENIGN if r["category"] in BANK_ALERT_CATEGORIES]
        assert len(bank) >= 60


class TestSchema:
    @pytest.mark.parametrize("row", FIXTURES, ids=lambda r: r["id"])
    def test_required_fields(self, row):
        for field in ("id", "label", "lang", "category", "text"):
            assert field in row, (row.get("id"), field)
        assert row["label"] in ("scam", "benign")
        assert row["lang"] in LANGS
        assert row["category"] in VALID_CATEGORIES
        assert 5 <= len(row["text"]) <= 600

    def test_ids_unique(self):
        ids = [r["id"] for r in FIXTURES]
        assert len(ids) == len(set(ids))

    def test_id_prefix_matches_label(self):
        for r in FIXTURES:
            assert r["id"].startswith(r["label"]), r["id"]

    def test_jsonl_files_parse_cleanly(self):
        from pathlib import Path

        corpus_dir = Path(__file__).resolve().parents[1] / "corpus"
        files = sorted(corpus_dir.glob("*.jsonl"))
        assert len(files) == 8
        for path in files:
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.strip():
                    json.loads(line)  # raises on malformed lines


class TestScriptCoverage:
    @staticmethod
    def _letter_ratio(text, lo, hi):
        letters = [ch for ch in text if unicodedata.category(ch).startswith("L")]
        if not letters:
            return 0.0
        in_range = sum(1 for ch in letters if lo <= ord(ch) <= hi)
        return in_range / len(letters)

    @pytest.mark.parametrize("row", SCAM + BENIGN, ids=lambda r: r["id"])
    def test_script_matches_language_tag(self, row):
        text = row["text"]
        if row["lang"] == "hi":
            assert self._letter_ratio(text, 0x0900, 0x097F) >= 0.4, row["id"]
        elif row["lang"] == "te":
            assert self._letter_ratio(text, 0x0C00, 0x0C7F) >= 0.4, row["id"]
        else:
            assert self._letter_ratio(text, 0x0041, 0x017F) >= 0.7, row["id"]

    def test_hinglish_rows_contain_latin_hindi_words(self):
        markers = (
            "aap", "karein", "karo", "karne", "batao", "bhejo", "paisa", "paise",
            "warna", "ghante", "jeet", "hai", "khate", "jama", "gaya", "nahi",
            "denge", "dekhein", "nikale", "hafte", "roz", "kiye", "rakhe",
        )
        for r in FIXTURES:
            if r["lang"] != "hinglish":
                continue
            if r["category"] == "obfuscation_gap":
                continue  # spaced-letter rows are deliberately obfuscated
            low = r["text"].lower()
            assert any(m in low for m in markers), r["id"]


class TestCorpusDesign:
    def test_obfuscation_gap_fixtures_exist_in_multiple_languages(self):
        gaps = {r["lang"] for r in SCAM if r["category"] == "obfuscation_gap"}
        assert {"en", "hi", "te"} <= gaps

    def test_hard_benign_cases_present(self):
        """The corpus must stress the documented FP failure modes."""
        texts = [r["text"].lower() for r in BENIGN]
        assert any("never share" in t or "do not share" in t or "share na" in t
                   or "शेयर न" in " ".join(texts) for t in texts)
        assert any("expire" in t for t in texts)  # marketing expiry vs scam expiry
        assert any("autopay" in t for t in texts)  # genuine tonight-autopay reminders

    def test_every_scam_fixture_is_detectable_or_deliberate_gap(self):
        from raksha.messageguard import assess

        for r in SCAM:
            if r["category"] == "obfuscation_gap":
                continue
            v = assess(r["text"], lang=r["lang"])
            heavy = {"credential", "authority"}
            assert v.score >= 0.45 or (len(v.families) >= 2) or (set(v.families) & heavy), (
                f"{r['id']} scores {v.score} with families {v.families}"
            )
