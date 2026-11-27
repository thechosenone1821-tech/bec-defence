"""Part 1 contract tests: reason catalogue + citizen i18n completeness."""

import pytest

from raksha.messageguard import assess
from raksha.reasons import (
    BAND_ADVICE,
    BAND_LABELS,
    FAMILY_LABELS,
    LANGS,
    REASON_TEMPLATES,
    ReasonCode,
    display_lang,
    reason_text,
)

ALL_CODES = list(ReasonCode)
ALL_BANDS = ("LOW", "MODERATE", "HIGH", "CRITICAL")
ALL_FAMILIES = ("credential", "authority", "money_action", "prize", "urgency", "link_grab")


class TestReasonCatalogue:
    def test_one_code_per_signal_family(self):
        codes = {c.value for c in ALL_CODES}
        assert len(codes) == 6
        assert all(c.startswith("msg.") for c in codes)

    @pytest.mark.parametrize("lang", LANGS)
    def test_every_code_has_template_in_every_language(self, lang):
        for code in ALL_CODES:
            assert code in REASON_TEMPLATES
            assert lang in REASON_TEMPLATES[code]
            assert "{phrase}" in REASON_TEMPLATES[code][lang]

    def test_reason_text_interpolates_phrase(self):
        text = reason_text(ReasonCode.MSG_CREDENTIAL_REQUEST, "en", phrase="share your otp")
        assert "share your otp" in text
        assert "{phrase}" not in text

    def test_reason_text_hindi_and_telugu_non_empty(self):
        for lang in ("hi", "te"):
            for code in ALL_CODES:
                assert len(reason_text(code, lang, phrase="x")) > 10

    def test_unknown_lang_falls_back_to_english(self):
        assert reason_text(ReasonCode.MSG_PRIZE_CLAIM, "fr", phrase="x") == reason_text(
            ReasonCode.MSG_PRIZE_CLAIM, "en", phrase="x"
        )

    def test_missing_phrase_uses_placeholder_dash(self):
        assert "-" in reason_text(ReasonCode.MSG_MONEY_ACTION, "en")


class TestCitizenI18n:
    @pytest.mark.parametrize("lang", LANGS)
    def test_band_labels_complete(self, lang):
        for band in ALL_BANDS:
            assert BAND_LABELS[band][lang]

    @pytest.mark.parametrize("lang", LANGS)
    def test_band_advice_complete(self, lang):
        for band in ALL_BANDS:
            advice = BAND_ADVICE[band][lang]
            assert len(advice) > 20

    @pytest.mark.parametrize("lang", LANGS)
    def test_family_labels_complete(self, lang):
        for family in ALL_FAMILIES:
            assert FAMILY_LABELS[family][lang]

    def test_display_lang_maps_hinglish_to_hindi(self):
        assert display_lang("hinglish") == "hi"
        assert display_lang("te") == "te"
        assert display_lang("xx") == "en"


class TestVerdictCitizenIntegration:
    def test_verdict_citizen_uses_contract(self):
        from raksha.messageguard import assess

        v = assess("Share the OTP with our officer, else your account will be blocked")
        out = v.citizen("hi")
        assert out["lang"] == "hi"
        assert out["band_label"] == BAND_LABELS[v.band.value]["hi"]
        assert out["advice"] == BAND_ADVICE[v.band.value]["hi"]
        assert out["reasons"]
        for line in out["reasons"]:
            assert isinstance(line, str) and line

    def test_hinglish_verdict_shown_in_hindi(self):
        v = assess("OTP batao jaldi, warna account block ho jayega")
        assert v.citizen("hinglish")["lang"] == "hi"

    def test_verdict_to_dict_shape(self):
        v = assess("You have won the lucky draw, pay the processing fee")
        d = v.to_dict()
        for key in ("lang", "score", "band", "families", "boosted", "family_hits", "reasons"):
            assert key in d
        assert d["band"] in ALL_BANDS
