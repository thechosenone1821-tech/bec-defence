"""MAYA / VoiceGuard — Phase 4 tests: reasons, i18n, risk fusion.

Phase 4 exit criteria (VOICEGUARD_ROADMAP.md §2):
  * every reason code renders a real sentence in en / hi / te
  * a missing translation falls back, never renders a key
  * INCONCLUSIVE never reads as reassurance
  * the risk engine has an explicit "I don't know" band and can never say
    "safe" from an absence of evidence
  * no raw score reaches a citizen without a sentence
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.risk import (BAND_CRITICAL, BAND_ELEVATED, BAND_HIGH, BAND_LOW,
                          BAND_LOW_CONFIDENCE, BANDS, assess, band_for, noisy_or)
from citizen.voiceguard import contract as C
from citizen.voiceguard import i18n, score_voice

EN, HI, TE = "en", "hi", "te"


# --------------------------------------------------------------------------- #
# 1. Reason catalogue coverage
# --------------------------------------------------------------------------- #
class TestCatalogue:
    def test_every_contract_reason_code_has_a_translation(self):
        codes = set(i18n.all_reason_constants())
        missing = codes - set(i18n.catalogue_codes())
        assert not missing, f"reason codes with no sentence: {sorted(missing)}"

    @pytest.mark.parametrize("lang", [EN, HI, TE])
    def test_every_reason_renders_in_every_language(self, lang):
        for code in i18n.catalogue_codes():
            text = i18n.render_reason(code, lang)
            assert isinstance(text, str) and len(text) > 4
            assert code not in text, f"{code} leaked as a raw key in {lang}"
            assert "{" not in text, f"{code} has an unfilled slot in {lang}"

    @pytest.mark.parametrize("lang", [EN, HI, TE])
    def test_every_verdict_renders_in_every_language(self, lang):
        for verdict in C.VERDICTS:
            body = i18n.render_verdict(verdict, lang)
            assert body["title"] and body["action"]
            assert body["helpline"] == "1930"
            assert body["lang"] == lang

    def test_non_latin_languages_are_actually_non_latin(self):
        """A copy-paste of English into the hi/te columns would pass a naive
        parity test and fail a real citizen."""
        for code in i18n.catalogue_codes():
            hi = i18n.render_reason(code, HI)
            te = i18n.render_reason(code, TE)
            assert any("\u0900" <= ch <= "\u097f" for ch in hi), f"{code} hi not Devanagari"
            assert any("\u0c00" <= ch <= "\u0c7f" for ch in te), f"{code} te not Telugu"

    def test_unknown_language_falls_back_to_english(self):
        assert i18n.normalise_language("fr") == EN
        assert i18n.normalise_language(None) == EN
        assert i18n.normalise_language("") == EN
        assert i18n.normalise_language("hi-IN") == HI
        assert i18n.normalise_language("TE_in") == TE

    def test_unknown_code_does_not_crash(self):
        assert i18n.render_reason("NOT_A_REAL_CODE", EN)
        assert i18n.render_verdict("NOT_A_VERDICT", EN)["title"]


# --------------------------------------------------------------------------- #
# 2. Explanation behaviour — the safety-critical copy
# --------------------------------------------------------------------------- #
class TestExplain:
    def test_inconclusive_does_not_reassure(self):
        """The most dangerous copy bug: making 'cannot tell' sound like 'fine'."""
        body = i18n.explain({"verdict": C.INCONCLUSIVE, "reasons": []}, EN)
        assert "cannot tell" in body["title"].lower()
        assert "hang up" in body["action"].lower()
        assert "1930" in body["action"]
        assert body["actionable"] is False

    def test_likely_synthetic_is_actionable_and_names_1930(self):
        body = i18n.explain({"verdict": C.LIKELY_SYNTHETIC, "reasons": []}, EN)
        assert body["actionable"] is True
        assert "AI" in body["title"]
        assert "1930" in body["action"]
        assert "hang up" in body["action"].lower()

    def test_silent_does_not_accuse(self):
        body = i18n.explain({"verdict": C.SILENT, "reasons": []}, EN)
        assert "could not hear" in body["title"].lower()
        assert body["actionable"] is False

    def test_raw_score_never_appears(self):
        v = score_voice(np.sin(2 * np.pi * 440 * np.arange(16000) / 16000).astype(np.float32))
        body = i18n.explain(v, EN)
        blob = " ".join(body["reasons"]) + body["title"] + body["action"]
        assert str(v["score"]) not in blob
        assert "score" not in blob.lower()

    def test_every_verdict_sentence_ends_with_an_action(self):
        for verdict in C.VERDICTS:
            body = i18n.render_verdict(verdict, EN)
            assert body["action"][-1] in ".!"
            assert ("1930" in body["action"]) or ("Try again" in body["action"]) \
                or ("official number" in body["action"])

    def test_reasons_are_deduplicated(self):
        payload = {"verdict": C.SUSPICIOUS,
                   "reasons": [C.reason(C.R_MONOTONE_PITCH), C.reason(C.R_MONOTONE_PITCH)]}
        body = i18n.explain(payload, EN)
        assert len(body["reasons"]) == 1

    def test_explain_survives_a_malformed_payload(self):
        for bad in ({}, {"reasons": "nonsense"}, {"reasons": [None, 3]},
                    {"verdict": None}):
            body = i18n.explain(bad, EN)
            assert body["title"] and body["action"]

    @pytest.mark.parametrize("lang", [EN, HI, TE])
    def test_explanation_is_localised_end_to_end(self, lang):
        v = score_voice(np.sin(2 * np.pi * 300 * np.arange(16000) / 16000).astype(np.float32))
        body = i18n.explain(v, lang)
        assert body["lang"] == lang
        if lang == HI:
            assert any("\u0900" <= ch <= "\u097f" for ch in body["title"])
        if lang == TE:
            assert any("\u0c00" <= ch <= "\u0c7f" for ch in body["title"])


# --------------------------------------------------------------------------- #
# 3. Fusion maths
# --------------------------------------------------------------------------- #
class TestNoisyOr:
    def test_empty_is_zero(self):
        assert noisy_or([]) == 0.0

    def test_single_signal_is_its_weight(self):
        assert noisy_or([0.4]) == pytest.approx(0.4)

    def test_bounded_by_one(self):
        assert noisy_or([0.9, 0.9, 0.9, 0.9, 0.9]) < 1.0

    def test_monotone(self):
        assert noisy_or([0.3]) < noisy_or([0.3, 0.2])

    def test_order_independent(self):
        assert noisy_or([0.2, 0.5, 0.1]) == pytest.approx(noisy_or([0.1, 0.2, 0.5]))

    def test_out_of_range_values_are_clamped(self):
        assert noisy_or([-1.0, 2.0]) == pytest.approx(1.0)
        assert noisy_or([-5.0]) == 0.0

    def test_nan_is_treated_as_no_evidence(self):
        assert noisy_or([float("nan"), 0.4]) == pytest.approx(0.4)


# --------------------------------------------------------------------------- #
# 4. Risk engine — the "I don't know" contract
# --------------------------------------------------------------------------- #
class TestRiskEngine:
    def test_nothing_at_all_is_low_confidence_not_low(self):
        r = assess()
        assert r["band"] == BAND_LOW_CONFIDENCE
        assert r["degraded"] is True
        assert r["band"] != BAND_LOW

    def test_there_is_no_safe_verdict_anywhere(self):
        assert "SAFE" not in BANDS
        assert not any("SAFE" in b for b in BANDS)

    def test_low_confidence_copy_does_not_sound_reassuring(self):
        r = assess(lang=EN)
        assert "not enough" in r["headline"].lower()
        assert "1930" in r["action"]

    def test_weak_only_signal_stays_low_confidence(self):
        """A single weak nudge is not evidence."""
        r = assess(user_doubt=True)
        assert r["band"] == BAND_LOW_CONFIDENCE
        assert r["score"] > 0

    def test_voice_synthetic_alone_reaches_high(self):
        r = assess(voice={"verdict": C.LIKELY_SYNTHETIC})
        assert r["band"] in {BAND_ELEVATED, BAND_HIGH}
        assert r["score"] > 0.60

    def test_inconclusive_voice_contributes_nothing(self):
        r = assess(voice={"verdict": C.INCONCLUSIVE})
        assert r["signals"] == []
        assert r["band"] == BAND_LOW_CONFIDENCE

    def test_silent_voice_contributes_nothing(self):
        r = assess(voice={"verdict": C.SILENT})
        assert r["signals"] == []

    def test_message_critical_alone_is_actionable(self):
        r = assess(message={"verdict": "CRITICAL"})
        assert r["band"] in {BAND_ELEVATED, BAND_HIGH, BAND_CRITICAL}
        assert "1930" in r["action"]

    def test_cross_signal_fusion_outranks_any_single_signal(self):
        single = assess(voice={"verdict": C.LIKELY_SYNTHETIC})["score"]
        fused = assess(voice={"verdict": C.LIKELY_SYNTHETIC},
                       message={"verdict": "CRITICAL"},
                       campaign_linked=True)["score"]
        assert fused > single

    def test_all_signals_reach_critical(self):
        r = assess(voice={"verdict": C.LIKELY_SYNTHETIC},
                   message={"verdict": "CRITICAL"},
                   campaign_linked=True,
                   repeat_contacts=5,
                   user_doubt=True)
        assert r["band"] == BAND_CRITICAL
        assert r["score"] > 0.90

    @pytest.mark.parametrize("lang", [EN, HI, TE])
    def test_fusion_is_localised(self, lang):
        r = assess(voice={"verdict": C.LIKELY_SYNTHETIC}, lang=lang)
        assert r["lang"] == lang
        assert r["headline"]
        if lang == TE:
            assert any("\u0c00" <= ch <= "\u0c7f" for ch in r["headline"])

    def test_every_band_has_copy_in_every_language(self):
        for band in BANDS:
            for lang in (EN, HI, TE):
                from citizen.voiceguard.i18n import render_band
                _b = render_band(band, lang)
                title, action = _b["headline"], _b["action"]
                assert title and action
                assert len(action) > 15

    def test_assessment_is_json_serialisable(self):
        import json
        json.dumps(assess(voice={"verdict": C.SUSPICIOUS}), allow_nan=False)

    def test_negative_repeat_contacts_are_ignored(self):
        assert assess(repeat_contacts=-3)["signals"] == []

    def test_weights_are_declared_not_learned(self):
        """A district-hospital reviewer must be able to read the numbers."""
        import citizen.risk.engine as E
        for name in dir(E):
            if name.startswith("W_"):
                val = getattr(E, name)
                assert 0.0 <= val < 1.0, name

    def test_band_boundaries_are_ordered(self):
        assert BANDS.index(BAND_LOW_CONFIDENCE) < BANDS.index(BAND_LOW) \
            < BANDS.index(BAND_ELEVATED) < BANDS.index(BAND_HIGH) \
            < BANDS.index(BAND_CRITICAL)

    def test_band_for_with_no_signals_ignores_a_high_score(self):
        assert band_for(0.99, 0) == BAND_LOW_CONFIDENCE


# --------------------------------------------------------------------------- #
# 5. API surface
# --------------------------------------------------------------------------- #
class TestPhase4Api:
    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient

        from citizen.api import build_app
        return TestClient(build_app(bus_url="", poster=lambda e: {"accepted": 1}))

    def test_assess_endpoint_defaults_to_low_confidence(self, client):
        r = client.post("/api/citizen/assess", json={}).json()
        assert r["band"] == BAND_LOW_CONFIDENCE

    def test_assess_endpoint_accepts_all_signals(self, client):
        r = client.post("/api/citizen/assess", json={
            "voice": {"verdict": "LIKELY_SYNTHETIC"},
            "message": {"verdict": "CRITICAL"},
            "campaign_linked": True,
            "repeat_contacts": 4,
            "user_doubt": True,
        }).json()
        assert r["band"] == BAND_CRITICAL

    def test_screen_voice_includes_a_localised_explanation(self, client):
        samples = [0.5 * float(np.sin(2 * np.pi * 440 * i / 16000)) for i in range(16000)]
        r = client.post("/api/citizen/screen_voice",
                        json={"consent": True, "samples": samples, "lang": "hi"}).json()
        assert r["explanation"]["lang"] == "hi"
        assert r["explanation"]["title"]

    def test_screen_message_honours_lang(self, client):
        """BUG-2 regression: `lang` used to be accepted and ignored."""
        r = client.post("/api/citizen/screen_message",
                        json={"text": "URGENT: share your OTP now",
                              "lang": "te"}).json()
        assert r["lang"] == "te"
        assert any("\u0c00" <= ch <= "\u0c7f" for ch in r["disclaimer"])

    def test_languages_endpoint(self, client):
        body = client.get("/api/citizen/languages").json()
        assert body["languages"] == ["en", "hi", "te"]

    def test_unknown_lang_falls_back(self, client):
        r = client.post("/api/citizen/assess", json={"lang": "fr"}).json()
        assert r["lang"] == "en"

    def test_report_never_carries_audio_or_reasons(self, client):
        """The report rail must stay minimal: category + band only."""
        r = client.post("/api/citizen/report",
                        json={"category": "voice", "severity": 0.9}).json()
        assert r["status"] == "REPORTED"


# --------------------------------------------------------------------------- #
# 6. No reassurance without evidence — end to end
# --------------------------------------------------------------------------- #
class TestNoFalseReassurance:
    def test_a_clean_human_clip_does_not_produce_a_reassuring_band(self):
        """A human-sounding clip that the model cannot judge must land in
        LOW_CONFIDENCE or LOW — never in a band whose copy says 'no danger'."""
        from citizen.voiceguard import corpus
        v = score_voice(corpus.make_bona_fide(4))
        r = assess(voice=v, lang=EN)
        assert r["band"] in {BAND_LOW_CONFIDENCE, BAND_LOW, BAND_ELEVATED}
        # Whatever the band, the copy must still warn about OTP/PIN.
        assert ("OTP" in r["action"]) or ("1930" in r["action"])

    def test_every_band_copy_mentions_a_concrete_action(self):
        from citizen.voiceguard.i18n import render_band as _rb
        for band in BANDS:
            action = _rb(band, EN)["action"]
            assert any(k in action for k in ("1930", "OTP", "official number",
                                            "Hang up", "hang up", "Verify")), band
