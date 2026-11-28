"""Language detection tests (script majority)."""

import pytest

from raksha.messageguard.detect import detect_language


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Your account will be blocked today", "en"),
        ("Hello, how are you?", "en"),
        ("आपका खाता आज ब्लॉक हो जाएगा", "hi"),
        ("आपका OTP बताइए, वरना खाता बंद", "hi"),
        ("మీ ఖాతా ఈ రోజే బ్లాక్ అవుతుంది", "te"),
        ("మీ OTP చెప్పండి వెంటనే", "te"),
        ("OTP batao jaldi warna account band", "en"),
        ("", "en"),
        ("12345", "en"),
    ],
)
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_detection_agrees_with_corpus_script_tags():
    """Every corpus row tagged hi/te must actually detect as hi/te."""
    from raksha.evals.run_evals import load_corpus

    for row in load_corpus():
        if row["lang"] in ("hi", "te"):
            assert detect_language(row["text"]) == row["lang"], row["id"]
