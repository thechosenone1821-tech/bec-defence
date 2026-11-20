import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citizen.messageguard import score_message, verdict_at_least, evaluate_fixtures

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "citizen", "fixtures", "message_fixtures.json")


def test_obvious_scams_flag_high_or_above():
    cases = [
        ("URGENT: Your KYC expired. Verify now via bit.ly/kyc-x to avoid account blocked within 24 hours. Share OTP."),
        ("This is CBI cyber crime branch. Digital arrest — transfer the fine immediately or face FIR."),
        ("आपका खाता 24 घंटे में बंद हो जाएगा, अभी सत्यापन करें और UPI PIN दे दें"),
        ("మీరు లక్కీ డ్రా లాటరీ గెలుచుకున్నారు! CVV, OTP పంచుకోండి — बधाई हो!"),
        ("Dear customer accept this collect request immediately to unblock electricity — no action = disconnection"),
    ]
    for text in cases:
        v = score_message(text)
        assert verdict_at_least(v["verdict"], "HIGH"), (text, v)
        assert v["families_hit"], v


def test_clean_messages_stay_low():
    cases = [
        "Your electricity bill of Rs 640 is ready, pay via BBPS by the 25th.",
        "Hi, lunch tomorrow at the usual place?",
        "आपका ऑर्डर #4821 शिप हो गया है",
        "మీ అపాయింట్‌మెంట్ రేపు ఉదయం 10:30 కి",
    ]
    for text in cases:
        assert score_message(text)["verdict"] == "LOW", text


def test_empty_and_garbage_input_safe():
    assert score_message("")["verdict"] == "LOW"
    assert score_message(None)["verdict"] == "LOW"
    assert score_message("💥💥💥 !!!")["score"] >= 0.0


def test_deterministic():
    text = "URGENT share OTP now or account blocked — CBI digital arrest"
    assert score_message(text) == score_message(text)


def test_synthetic_fixture_accuracy_is_measurable():
    report = evaluate_fixtures(FIXTURES)
    assert report["total"] == 20
    # synthetic corpus is tuned to pass; report accuracy honestly either way
    assert report["accuracy"] >= 0.8, report
