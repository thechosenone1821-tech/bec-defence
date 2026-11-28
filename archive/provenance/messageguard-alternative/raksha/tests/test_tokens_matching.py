"""Token matcher tests: per-family canaries in all three scripts, boundary
checks, normalization, shortener regex, obfuscation gaps."""

from raksha.messageguard import assess
from raksha.messageguard.tokens import iter_phrase_hits, normalize

import pytest


class TestCredentialCanaries:
    @pytest.mark.parametrize(
        "text,lang",
        [
            ("Send your OTP to the verification officer", "en"),
            ("अपना ओटीपी बताइए, वरना खाता बंद हो जाएगा", "hi"),
            ("अपना OTP बताइए", "hi"),
            ("మీ ఓటీపీ చెప్పండి", "te"),
            ("OTP batao jaldi", "hinglish"),
        ],
    )
    def test_request_phrases_fire(self, text, lang):
        v = assess(text, lang=lang)
        assert "credential" in v.families

    def test_mention_alone_does_not_fire(self):
        assert "credential" not in assess("Your OTP is 4521, valid for 10 minutes").families


class TestAuthorityCanaries:
    @pytest.mark.parametrize(
        "text,lang",
        [
            ("You are under digital arrest", "en"),
            ("आप डिजिटल अरेस्ट में हैं", "hi"),
            ("మీరు డిజిటల్ అరెస్ట్‌లో ఉన్నారు", "te"),
            ("CBI officer R. Verma speaking", "en"),
            ("सीबीआई अधिकारी बोल रहे हैं", "hi"),
        ],
    )
    def test_impersonation_fires(self, text, lang):
        v = assess(text, lang=lang)
        assert "authority" in v.families

    def test_rbi_guidelines_does_not_fire(self):
        v = assess("As per RBI guidelines, update KYC at your branch.")
        assert "authority" not in v.families

    def test_entity_role_pair_fires(self):
        assert "authority" in assess("The police team will visit you today").families


class TestMoneyActionCanaries:
    @pytest.mark.parametrize(
        "text,lang",
        [
            ("Pay the processing fee of Rs.2,499", "en"),
            ("₹12,000 प्रोसेसिंग फीस भरें", "hi"),
            ("₹2,499 ప్రాసెసింగ్ ఫీజు కట్టండి", "te"),
            ("paisa bhejo is number par", "hinglish"),
        ],
    )
    def test_fee_phrases_fire(self, text, lang):
        v = assess(text, lang=lang)
        assert "money_action" in v.families

    def test_bail_phrases_fire(self):
        assert "money_action" in assess("Bail amount of Rs.25,000 must be transferred").families

    def test_plain_debit_alert_does_not_fire(self):
        v = assess("Rs.1,250 debited from A/c XX4412 for UPI/TEXMI TRADERS")
        assert "money_action" not in v.families


class TestPrizeCanaries:
    @pytest.mark.parametrize(
        "text,lang",
        [
            ("You have won the Jio Lucky Draw of Rs.25,00,000", "en"),
            ("आपने व्हाट्सएप लकी ड्रॉ में ₹15,000 जीते हैं", "hi"),
            ("మీరు వాట్సాప్ లక్కీ డ్రాలో ₹15,000 గెలిచారు", "te"),
            ("KBC lottery winner 2026", "hinglish"),
        ],
    )
    def test_prize_phrases_fire(self, text, lang):
        v = assess(text, lang=lang)
        assert "prize" in v.families

    def test_loan_congratulations_does_not_fire_prize(self):
        v = assess("Congratulations! Your loan of Rs.80,000 is sanctioned")
        assert "prize" not in v.families


class TestUrgencyCanaries:
    @pytest.mark.parametrize(
        "text,lang",
        [
            ("Your account will be blocked within 24 hours", "en"),
            ("अंतिम चेतावनी: आज रात बिजली काट दी जाएगी", "hi"),
            ("చివరి హెచ్చరిక: 24 గంటల్లో కనెక్షన్ తెగించబడుతుంది", "te"),
            ("Aakhri chetavni, warna account band ho jayega", "hinglish"),
        ],
    )
    def test_urgency_phrases_fire(self, text, lang):
        v = assess(text, lang=lang)
        assert "urgency" in v.families


class TestLinkGrabCanaries:
    @pytest.mark.parametrize(
        "url",
        [
            "bit.ly/kyc9",
            "tinyurl.com/icici-kyc",
            "cutt.ly/bescom-pay",
            "rbikyc-update.xyz",
            "tiny.cc/pay1",
        ],
    )
    def test_shorteners_and_scam_tlds_fire(self, url):
        v = assess(f"Verify now: {url}")
        assert "link_grab" in v.families

    def test_official_domain_does_not_fire(self):
        v = assess("Visit www.tsspdcl.co.in/rec8821 for your receipt")
        assert "link_grab" not in v.families

    def test_t_co_not_matched_inside_other_domains(self):
        v = assess("Track: www.bluedart.com/t88123")
        assert "link_grab" not in v.families

    def test_plain_word_online_not_matched(self):
        v = assess("Shop online this weekend for great deals")
        assert "link_grab" not in v.families


class TestBoundariesAndNormalization:
    def test_word_boundary_blocks_substring(self):
        # "pin" must not match inside "spine"
        v = assess("The spine of the book was broken")
        assert v.band.value == "LOW"

    def test_case_and_whitespace_insensitive(self):
        a = assess("SHARE YOUR OTP")
        b = assess("share your   otp")
        assert (a.score, a.band, a.families) == (b.score, b.band, b.families)

    def test_zero_width_characters_stripped(self):
        a = assess("share your OT\u200cP with us")
        b = assess("share your OTP with us")
        assert (a.score, a.band, a.families) == (b.score, b.band, b.families)

    def test_phrase_hits_are_word_bounded(self):
        norm = normalize("share your OTP and PIN")
        hits = iter_phrase_hits(norm, ("otp", "pin", "ot"))
        matched = {h[2] for h in hits}
        assert "otp" in matched and "pin" in matched
        assert "ot" not in matched  # prefix of OTP must not match

    def test_spaced_out_otp_is_a_documented_gap(self):
        v = assess("S e n d y o u r O T P t o 9 0 0 0 0 1 2 3 4 5")
        assert v.band.value == "LOW"  # known failure mode, must stay stated
