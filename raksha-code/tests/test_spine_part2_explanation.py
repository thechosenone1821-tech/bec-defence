"""CITIZEN SPINE — PART TWO: the Explanation Layer.

The five invariants from `specs/01c_citizen_spine_four_parts.md` §Part Two:

  1. Total        every band, verdict and reason code renders in en/hi/te
  2. Code-free    no citizen-facing string contains an internal name
  3. Honest       no sentence claims accuracy or certainty we do not have
  4. Actionable   any non-trivial verdict carries something to *do*
  5. Single-path  i18n.py is the only module that produces citizen sentences

Most of these were written *after* the defects they now guard, so each carries a
note on what was wrong. A test whose history is forgotten gets deleted by the
next person who finds it inconvenient.
"""

import re
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.risk import assess
from citizen.risk import engine
from citizen.voiceguard import contract as C
from citizen.voiceguard import i18n

LATIN_WORD = re.compile(r"\b[A-Z][a-z]{3,}\b")
NATIVE_SCRIPT = re.compile(r"[\u0900-\u097F\u0C00-\u0C7F]")


# --------------------------------------------------------------------------- #
# 1. Total
# --------------------------------------------------------------------------- #
class TestTotal:
    @pytest.mark.parametrize("lang", i18n.LANGUAGES)
    def test_every_reason_code_renders(self, lang):
        i18n.reset_fallbacks()
        for code in i18n._REASONS:
            sentence = i18n.render_reason(code, lang)
            assert sentence and sentence.strip(), f"{code} rendered empty in {lang}"
        assert i18n.fallbacks() == [], f"fell back during a full render: {i18n.fallbacks()}"

    @pytest.mark.parametrize("lang", i18n.LANGUAGES)
    def test_every_band_renders(self, lang):
        from citizen.risk.fusion import BANDS
        for band in BANDS:
            out = i18n.render_band(band, lang)
            assert out["headline"] and out["action"]
            assert out["lang"] == lang

    def test_every_band_in_the_fusion_core_has_copy(self):
        """The catalogue must keep up with the scoring core.

        Band copy used to live in the risk engine; when it moved here the two
        lists could drift. This is the seam, so it gets a test.
        """
        from citizen.risk.fusion import BANDS
        for band in BANDS:
            assert band in i18n._BAND_COPY, f"band {band} has no citizen copy"

    @pytest.mark.parametrize("lang", i18n.LANGUAGES)
    def test_advisory_renders_in_every_language(self, lang):
        assert i18n.render_advisory(lang).strip()

    def test_an_unknown_band_falls_back_to_cannot_judge(self):
        """The safe rendering of an unrecognised band is "we cannot tell".

        Never "all clear": a band this build does not know about is not
        evidence of safety.
        """
        out = i18n.render_band("A_BAND_FROM_THE_FUTURE")
        assert out["headline"] == i18n._BAND_COPY["LOW_CONFIDENCE"]["en"][0]


# --------------------------------------------------------------------------- #
# 2. Code-free
# --------------------------------------------------------------------------- #
class TestCodeFree:
    @pytest.mark.parametrize("lang", i18n.LANGUAGES)
    def test_no_reason_sentence_contains_a_code(self, lang):
        for code in i18n._REASONS:
            sentence = i18n.render_reason(code, lang)
            assert "_" not in sentence, f"{code}/{lang} leaked an underscore: {sentence}"
            assert code not in sentence, f"{code}/{lang} named itself: {sentence}"

    def test_band_explanation_never_leaks_the_score(self):
        """A citizen cannot act on "fused score 0.400".

        Part One's reasons are prose for engineers and contain the number. The
        renderer must turn them into words, and an unrecognised reason must
        render as nothing rather than as the raw string.
        """
        for why in ("no signals contributed",
                    "a single weak signal is not enough without corroboration",
                    "fused score 0.400 falls in [elevated]",
                    "fused score 0.9476 exceeds every threshold"):
            for lang in i18n.LANGUAGES:
                out = i18n.render_band_reason(why, lang)
                assert not re.search(r"\d\.\d", out), f"a score leaked: {out!r}"
                assert "[" not in out and "]" not in out

    def test_an_unrecognised_band_reason_renders_as_nothing(self):
        """Empty beats wrong. A guessed explanation about a scam is harmful."""
        assert i18n.render_band_reason("some new wording nobody translated") == ""
        assert i18n.render_band_reason(None) == ""
        assert i18n.render_band_reason(12345) == ""


# --------------------------------------------------------------------------- #
# 3. Honest
# --------------------------------------------------------------------------- #
# Claims we cannot support. Note "almost certainly" is NOT on this list and must
# not be: it is hedged language, which is the opposite of the failure this list
# guards against. The first draft matched the bare word "certain" and flagged
# "almost certainly a scam" — a correct, appropriately hedged sentence. A test
# that forbids a hedge is a test that pushes copy towards *overclaiming*.
FORBIDDEN_CLAIMS = [
    "99%", "99.9", "100%", "accurate", "accuracy", "proven", "guarantee",
    "definitely", "verified scam", "detects all", "is certainly",
]


class TestHonest:
    def _all_sentences(self):
        out = []
        for lang in i18n.LANGUAGES:
            for code in i18n._REASONS:
                out.append(i18n.render_reason(code, lang))
            for band in i18n._BAND_COPY:
                b = i18n.render_band(band, lang)
                out.extend([b["headline"], b["action"]])
            out.append(i18n.render_advisory(lang))
        return out

    def test_no_sentence_claims_accuracy_we_cannot_measure(self):
        for s in self._all_sentences():
            low = s.lower()
            for claim in FORBIDDEN_CLAIMS:
                assert claim not in low, f"unmeasured claim {claim!r} in: {s}"

    def test_the_honesty_label_still_says_it_is_not_calibrated(self):
        """The single most important sentence in the product.

        If this ever loses the word "calibrated" or "not a verdict", the screen
        has started claiming more than the measurements support. In every
        language, not just English.
        """
        for lang in i18n.LANGUAGES:
            label = i18n.render_advisory(lang).lower()
            assert "कैलिब्रेटेड" in label or "కాలిబ్రేట్" in label or "calibrated" in label, \
                f"advisory in {lang} lost its calibration disclaimer: {label}"
            assert ("not a verdict" in label or "निर्णय नहीं" in label
                    or "తీర్పు కాదు" in label), f"advisory in {lang} stopped disclaiming: {label}"

    def test_no_sentence_accuses_the_person_on_the_other_end(self):
        """The app describes signals, not people. "This is a criminal" is a
        libel risk and, more importantly, useless to the reader."""
        for s in self._all_sentences():
            low = s.lower()
            for accusation in ("criminal", "fraudster", "thief", "scammer"):
                assert accusation not in low, f"accusation {accusation!r} in: {s}"


# --------------------------------------------------------------------------- #
# 4. Actionable
# --------------------------------------------------------------------------- #
class TestActionable:
    @pytest.mark.parametrize("band", ["ELEVATED", "HIGH", "CRITICAL"])
    def test_a_serious_band_tells_the_person_what_to_do(self, band):
        for lang in i18n.LANGUAGES:
            action = i18n.render_band(band, lang)["action"]
            assert len(action) > 10, f"{band}/{lang} action is not an instruction"
            if lang == "en":
                continue      # English is Latin by design, not a missing translation
            assert NATIVE_SCRIPT.search(action), f"{band}/{lang} action is not translated"

    def test_every_band_except_all_clear_mentions_the_helpline_or_an_action(self):
        for band in ("LOW_CONFIDENCE", "HIGH", "CRITICAL"):
            action = i18n.render_band(band, "en")["action"]
            assert ("1930" in action or "hang up" in action.lower()
                    or "verify" in action.lower() or "trust" in action.lower()), action


# --------------------------------------------------------------------------- #
# 5. Single-pathed
# --------------------------------------------------------------------------- #
class TestSinglePath:
    def test_the_risk_engine_holds_no_citizen_sentences(self):
        """Part Two's boundary, as a test.

        `engine.py` used to carry `_BAND_COPY` — five bands of copy in three
        languages inside the module that Part One had just been cleared of
        English. It also hard-coded an English `advisory` literal. Both are
        gone; this fails if either comes back.
        """
        src = inspect.getsource(engine)
        for gone in ("_BAND_COPY", "Not enough information to judge",
                     "This looks like a scam attempt",
                     "Judgement-based weighting"):
            assert gone not in src, f"citizen copy crept back into engine.py: {gone!r}"

    def test_the_engine_asks_the_catalogue_for_every_sentence(self):
        src = inspect.getsource(engine)
        for call in ("i18n.render_band(", "i18n.render_advisory(",
                     "i18n.render_band_reason(", "i18n.render_reason("):
            assert call in src, f"engine.py stopped using {call}"

    @pytest.mark.parametrize("lang", i18n.LANGUAGES)
    def test_assess_produces_no_english_for_a_non_english_reader(self, lang):
        """End-to-end: the assembled payload, not just the catalogue.

        The `advisory` defect was invisible to catalogue-level tests because
        the string never lived in the catalogue. This test reads what a citizen
        actually receives.
        """
        r = assess(voice={"verdict": "LIKELY_SYNTHETIC"}, lang=lang)
        if lang == "en":
            pytest.skip("English output is Latin by design")
        for field in ("headline", "action", "advisory"):
            value = r[field]
            assert not LATIN_WORD.search(value), \
                f"{lang}/{field} still contains English: {value!r}"

    def test_band_explanation_reaches_the_citizen(self):
        r = assess(lang="en")
        assert r["band_explanation"], "the most useful sentence in the payload is empty"


# --------------------------------------------------------------------------- #
# Fallback accounting (task 2.3)
# --------------------------------------------------------------------------- #
class TestFallbackAccounting:
    def test_a_missing_translation_is_recorded_not_silent(self, monkeypatch):
        """A gap must leave a trace.

        Before task 2.3 the fallback to English was silent, so a missing Telugu
        string looked exactly like a working screen.
        """
        i18n.reset_fallbacks()
        broken = {C.R_SILENT: {"en": "Only English exists."}}
        monkeypatch.setattr(i18n, "_REASONS", broken)
        out = i18n.render_reason(C.R_SILENT, "te")
        assert out == "Only English exists."
        assert i18n.fallbacks() == [{"code": C.R_SILENT, "lang": "te"}]

    def test_an_unknown_code_is_recorded(self):
        i18n.reset_fallbacks()
        i18n.render_reason("A_CODE_THAT_NEVER_EXISTED", "hi")
        assert i18n.fallbacks()[0]["code"] == "A_CODE_THAT_NEVER_EXISTED"

    def test_the_log_is_bounded(self):
        """A diagnostic hook must not become a memory leak on a cheap phone."""
        i18n.reset_fallbacks()
        for i in range(i18n._FALLBACK_LIMIT + 50):
            i18n.render_reason(f"MISSING_{i}", "te")
        assert len(i18n.fallbacks()) <= i18n._FALLBACK_LIMIT

    def test_reset_clears_the_log(self):
        i18n.render_reason("ANOTHER_MISSING_ONE", "te")
        i18n.reset_fallbacks()
        assert i18n.fallbacks() == []

    def test_the_real_catalogue_produces_no_fallbacks_at_all(self):
        """The assertion that makes every other test here meaningful.

        If the catalogue were complete, this passes trivially; it exists so that
        the day someone adds a code in English only, this fails loudly instead of
        a Telugu reader getting an English sentence.
        """
        i18n.reset_fallbacks()
        for lang in i18n.LANGUAGES:
            for code in i18n._REASONS:
                i18n.render_reason(code, lang)
            for band in i18n._BAND_COPY:
                i18n.render_band(band, lang)
            i18n.render_advisory(lang)
        assert i18n.fallbacks() == []
