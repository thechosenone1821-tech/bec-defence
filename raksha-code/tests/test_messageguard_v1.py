"""Unit tests for the MessageGuard deterministic scorer.

Run:  cd raksha-code && python -m pytest tests/test_messageguard_v1.py -q

Pure stdlib; no network, no fixtures needed — these pin down the
scoring contract (weights, boost, bands, legacy band map, negation
guards, three-script coverage, determinism).
"""

import unittest

from citizen import messageguard
from citizen.messageguard import bandmap
from citizen.messageguard.normalize import normalize
from citizen.messageguard.scorer import analyze, band


class TestDeterminism(unittest.TestCase):
    def test_same_input_same_output(self):
        text = "You have won Rs 25,00,000 in KBC lucky draw. Click bit.ly/x9 to claim now."
        a = analyze(text)
        b = analyze(text)
        self.assertEqual(a, b)

    def test_reason_order_stable(self):
        text = "CBI digital arrest! Share your OTP now, else arrest warrant today."
        self.assertEqual(analyze(text)["reasons"], analyze(text)["reasons"])


class TestBands(unittest.TestCase):
    def test_band_edges(self):
        self.assertEqual(band(0.19), "LOW")
        self.assertEqual(band(0.20), "MODERATE")
        self.assertEqual(band(0.44), "MODERATE")
        self.assertEqual(band(0.45), "HIGH")
        self.assertEqual(band(0.69), "HIGH")
        self.assertEqual(band(0.70), "CRITICAL")
        self.assertEqual(band(1.0), "CRITICAL")


class TestScoring(unittest.TestCase):
    def test_single_weak_family_is_low_or_moderate(self):
        r = analyze("Payment window closes tonight, act now.")
        self.assertEqual(r["families_fired"], ["urgency"])
        self.assertEqual(r["score"], 0.20)
        self.assertIn(r["verdict"], ("LOW", "MODERATE"))

    def test_two_families_no_boost(self):
        # prize (0.30) + urgency (0.20) = 0.50, no boost (needs >=3)
        r = analyze("You have won Rs 25,00,000 in the KBC lucky draw. Claim by tonight.")
        self.assertEqual(r["families_fired"], ["prize", "urgency"])
        self.assertFalse(r["boost_applied"])
        self.assertEqual(r["score"], 0.50)

    def test_three_family_boost(self):
        # prize .30 + money .30 + urgency .20 = .80 raw; x1.3 = 1.04 -> cap 1.0
        r = analyze(
            "You have won Rs 25,00,000 in the KBC lucky draw. "
            "Send Rs 8,500 processing fee within 24 hours."
        )
        self.assertTrue(r["boost_applied"])
        self.assertEqual(r["score"], 1.0)
        self.assertEqual(r["verdict"], "CRITICAL")

    def test_score_never_exceeds_one(self):
        r = analyze(
            "Digital arrest! Share OTP, CVV and enter UPI PIN to receive the money. "
            "Send Rs 50,000 bail now via bit.ly/x, click here, verify now, else arrest tonight."
        )
        self.assertLessEqual(r["score"], 1.0)

    def test_families_weights_match_spec(self):
        self.assertEqual(
            messageguard.FAMILY_WEIGHTS,
            {
                "credential": 0.45,
                "authority": 0.40,
                "money_action": 0.30,
                "prize": 0.30,
                "urgency": 0.20,
                "link_grab": 0.25,
            },
        )


class TestReasonsNameFamily(unittest.TestCase):
    def test_every_reason_carries_family_and_catalogue_code(self):
        r = analyze("Share your OTP to unblock the account immediately.")
        self.assertTrue(r["reasons"])
        for reason in r["reasons"]:
            self.assertIn("family", reason)
            self.assertIn(reason["code"], messageguard.REASON_CATALOGUE)
            family, _ = messageguard.REASON_CATALOGUE[reason["code"]]
            self.assertEqual(family, reason["family"])


class TestNegationGuard(unittest.TestCase):
    def test_genuine_otp_delivery_stays_clean(self):
        r = analyze("Your SBI OTP is 483920. Do not share it with anyone.")
        self.assertEqual(r["score"], 0)
        self.assertEqual(r["families_fired"], [])

    def test_never_share_variant(self):
        r = analyze("Never share your CVV. HDFC Bank.")
        self.assertEqual(r["score"], 0)

    def test_hindi_negation(self):
        r = analyze("OTP किसी को नहीं बताएं। SBI")
        self.assertEqual(r["score"], 0)

    def test_telugu_negation(self):
        r = analyze("మీ OTP షేర్ చేయవద్దు. బ్యాంక్ ఆఫీసర్లు అడగరు.")
        self.assertEqual(r["score"], 0)

    def test_scam_request_still_fires(self):
        r = analyze("Your account is blocked. Share the OTP with our agent now.")
        self.assertIn("credential", r["families_fired"])


class TestThreeScripts(unittest.TestCase):
    def test_english_digital_arrest(self):
        r = analyze("CBI officer: digital arrest ordered against you. Pay Rs 2,00,000 bail now.")
        self.assertIn("authority", r["families_fired"])
        self.assertIn("money_action", r["families_fired"])

    def test_hindi_digital_arrest(self):
        r = analyze("सीबीआई टीम: आप डिजिटल अरेस्ट में हैं, जमानत के लिए ₹2,00,000 भेजें तुरंत।")
        self.assertIn("authority", r["families_fired"])
        self.assertIn("money_action", r["families_fired"])

    def test_telugu_digital_arrest(self):
        r = analyze("సీబీఐ ఆఫీసర్: మీ పై కేసు నమోదు, డిజిటల్ అరెస్ట్, జామీను ₹2,00,000 పంపండి వెంటనే.")
        self.assertIn("authority", r["families_fired"])
        self.assertIn("money_action", r["families_fired"])

    def test_obfuscated_otp_partially_mitigated(self):
        r = analyze("Share your O T P with the verification agent now.")
        self.assertIn("credential", r["families_fired"])

    def test_normalize_strips_zero_width(self):
        self.assertEqual(normalize("sha\u200bre your otp"), normalize("share your otp"))


class TestLegacyBandMap(unittest.TestCase):
    def test_mapping_and_bounds(self):
        self.assertEqual(bandmap.to_legacy_band("LOW"), 0.25)
        self.assertEqual(bandmap.to_legacy_band("MODERATE"), 0.50)
        self.assertEqual(bandmap.to_legacy_band("HIGH"), 0.75)
        self.assertEqual(bandmap.to_legacy_band("CRITICAL"), 0.99)
        for verdict in ("LOW", "MODERATE", "HIGH", "CRITICAL"):
            value = bandmap.to_legacy_band(verdict)
            self.assertGreaterEqual(value, 0.25)
            self.assertLessEqual(value, 0.99)

    def test_unknown_verdict_raises(self):
        with self.assertRaises(ValueError):
            bandmap.to_legacy_band("BANANA")

    def test_analyze_includes_legacy_band(self):
        r = analyze("You have won Rs 10,00,000 KBC prize. Send fee now.")
        self.assertIn("legacy_band", r)
        self.assertGreaterEqual(r["legacy_band"], 0.25)
        self.assertLessEqual(r["legacy_band"], 0.99)


class TestOfflineDesign(unittest.TestCase):
    def test_no_network_imports_in_module_source(self):
        # The detector must run offline: its source never references
        # network client modules.
        import pathlib

        pkg_dir = pathlib.Path(messageguard.__file__).parent
        banned = ("requests", "urllib", "socket", "http.client", "smtplib", "httpx")
        for src in pkg_dir.glob("*.py"):
            text = src.read_text(encoding="utf-8")
            for token in banned:
                self.assertNotIn(f"import {token}", text)
                self.assertNotIn(f"from {token}", text)


if __name__ == "__main__":
    unittest.main()
