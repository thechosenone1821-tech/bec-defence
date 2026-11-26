"""Scorer math tests: weights, boost, cap, bands, determinism, explainability.

The numbers here are fixed by the Part 3 spec:
    credential 0.45 | authority 0.40 | money_action 0.30 | prize 0.30
    urgency 0.20 | link_grab 0.25
    3+ families => x1.3 boost, capped at 1.0
    bands: <0.20 LOW | <0.45 MODERATE | <0.70 HIGH | >=0.70 CRITICAL
"""

from raksha.messageguard import assess, score, SignalFamilyScorer
from raksha.messageguard.types import Band, band_for


class TestBandBoundaries:
    def test_exact_spec_boundaries(self):
        assert band_for(0.0) is Band.LOW
        assert band_for(0.19) is Band.LOW
        assert band_for(0.20) is Band.MODERATE
        assert band_for(0.44) is Band.MODERATE
        assert band_for(0.45) is Band.HIGH
        assert band_for(0.69) is Band.HIGH
        assert band_for(0.70) is Band.CRITICAL
        assert band_for(1.0) is Band.CRITICAL

    def test_sweep_is_monotone(self):
        order = [Band.LOW, Band.MODERATE, Band.HIGH, Band.CRITICAL]
        last = -1
        for i in range(0, 1001):
            s = i / 1000
            idx = order.index(band_for(s))
            assert idx >= last
            last = idx


class TestWeightsAndBoost:
    def test_single_link_grab_is_moderate(self):
        v = assess("click here to login now")
        assert v.families == ("link_grab",)
        assert v.score == 0.25
        assert v.band is Band.MODERATE
        assert v.boosted is False

    def test_single_urgency_boundary_is_moderate(self):
        v = assess("Your account will be blocked in 24 hours")
        assert v.families == ("urgency",)
        assert v.score == 0.20
        assert v.band is Band.MODERATE

    def test_two_families_no_boost(self):
        # credential 0.45 + urgency 0.20 = 0.65 -> HIGH, no boost
        v = assess("Share the OTP you received, else your account will be blocked")
        assert v.families == ("credential", "urgency")
        assert v.score == 0.65
        assert v.boosted is False
        assert v.band is Band.HIGH

    def test_three_families_boost(self):
        # link 0.25 + urgency 0.20 + link... need 3 distinct families
        # credential 0.45 + urgency 0.20 + link 0.25 = 0.90 -> x1.3 = 1.0 cap
        v = assess("Share the OTP at bit.ly/x9k within 24 hours or account will be blocked")
        assert set(v.families) == {"credential", "urgency", "link_grab"}
        assert v.boosted is True
        assert v.score == 1.0
        assert v.band is Band.CRITICAL

    def test_three_light_families_boost_value(self):
        # urgency 0.20 + link 0.25 + prize 0.30 = 0.75 -> x1.3 = 0.975
        v = assess(
            "You have won the lucky draw. Act now and click the link within 24 hours: bit.ly/p1"
        )
        assert set(v.families) == {"prize", "urgency", "link_grab"}
        assert v.boosted is True
        assert abs(v.score - 0.975) < 1e-9
        assert v.band is Band.CRITICAL

    def test_all_six_families_cap_at_one(self):
        v = assess(
            "Share your OTP with the CBI officer. You are under digital arrest. "
            "Send the bail amount by transfer to this upi. You have won the lottery. "
            "Account will be blocked in 24 hours. Click here: bit.ly/z1"
        )
        assert len(v.families) == 6
        assert v.score == 1.0

    def test_zero_families_is_low(self):
        v = assess("Hello, how are you doing today?")
        assert v.families == ()
        assert v.score == 0.0
        assert v.band is Band.LOW
        assert v.reasons == ()

    def test_family_fires_once_despite_many_matches(self):
        # urgency hits 4 times but the family weight counts once
        v = assess(
            "Account will be blocked in 24 hours. Last warning. Final notice. "
            "Otherwise your services will be disconnected."
        )
        assert v.families == ("urgency",)
        assert v.score == 0.20
        assert v.family_hits["urgency"] >= 3


class TestExplainability:
    def test_every_reason_names_family_and_phrase(self):
        v = assess("CBI officer calling. Pay the verification fee of Rs.5000 to this upi")
        assert v.reasons, "expected reasons"
        for r in v.reasons:
            assert r.family in ("authority", "money_action")
            assert r.matched
            assert r.code.startswith("msg.")

    def test_pair_reason_reports_both_tokens(self):
        v = assess("RBI officer will freeze your account")
        pair_reasons = [r for r in v.reasons if r.trigger == "pair"]
        assert pair_reasons, "expected a pair rule hit"
        assert "+" in pair_reasons[0].matched

    def test_reasons_are_deterministic_and_ordered(self):
        text = "Share your OTP. CBI officer. Processing fee. You have won. Last warning. bit.ly/q1"
        v1 = assess(text)
        v2 = assess(text)
        assert v1 == v2
        assert [r.matched for r in v1.reasons] == [r.matched for r in v2.reasons]


class TestDeterminism:
    def test_same_input_same_verdict(self):
        text = "Digital arrest! Transfer bail money to escrow within 2 hours: bit.ly/bail"
        scorer = SignalFamilyScorer()
        first = scorer.score(text)
        for _ in range(10):
            assert scorer.score(text) == first

    def test_public_aliases(self):
        assert score is assess
        assert isinstance(SignalFamilyScorer(), SignalFamilyScorer)

    def test_empty_and_garbage_input(self):
        for text in ("", "   ", "...", "12345"):
            v = assess(text)
            assert v.band is Band.LOW
            assert v.score == 0.0


class TestGuards:
    def test_genuine_otp_warning_does_not_fire_credential(self):
        v = assess("OTP 448210 for txn of Rs.5,000. DO NOT share with anyone, even bank staff.")
        assert "credential" not in v.families

    def test_genuine_never_share_warning_is_low(self):
        v = assess("Never share your OTP, CVV or PIN with anyone. Bank staff will never ask for them.")
        assert v.band is Band.LOW

    def test_hindi_warning_suppressed(self):
        v = assess("आपके लेनदेन के लिए OTP 448210 है। इसे किसी के साथ शेयर न करें।")
        assert "credential" not in v.families
        assert v.band is Band.LOW

    def test_telugu_warning_suppressed(self):
        v = assess("మీ లావాదేవీకి OTP 551204. దీన్ని ఎవరితో షేర్ చేయవద్దు.")
        assert "credential" not in v.families

    def test_scam_request_still_fires_without_guard(self):
        v = assess("Share the OTP you received with our officer, else the account closes")
        assert "credential" in v.families

    def test_collect_request_acceptance_fires_credential(self):
        v = assess("Approve the collect request to receive your refund within 24 hours")
        assert "credential" in v.families
