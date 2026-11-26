"""Integration tests for the standalone Part 3 MessageGuard work.

These pin the seams that unit tests of the scorer alone cannot see: the
Citizen API payload contract, the shared reason-code presentation layer, the
committed measurement, and compatibility with the original M3 smoke corpus.
"""

import json
import pathlib
import sys

from fastapi.testclient import TestClient

CODE_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT))

from citizen.messageguard import (  # noqa: E402
    FAMILY_WEIGHTS,
    LEGACY_BANDS,
    REASON_CATALOGUE,
    VERDICT_ORDER,
    analyze,
    evaluate_fixtures,
    score_message,
)
from citizen.messageguard.reasons import REASON_CATALOGUE as RAW_CATALOGUE  # noqa: E402
from citizen.voiceguard import i18n  # noqa: E402
from evals.messageguard.run_evals import compute_results  # noqa: E402

LEGACY_FIXTURES = CODE_ROOT / "citizen" / "fixtures" / "message_fixtures.json"
V1_FIXTURES = CODE_ROOT / "citizen" / "fixtures" / "messageguard"
RESULTS = CODE_ROOT / "evals" / "messageguard" / "results.json"


def _load_corpus():
    records = []
    for path in sorted(V1_FIXTURES.glob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            records.extend(json.loads(line) for line in fh if line.strip())
    return records


def test_score_message_preserves_citizen_payload_contract():
    for text in (None, "", "URGENT: share your OTP now or account blocked"):
        result = score_message(text)
        for key in ("verdict", "score", "hits", "families_hit", "reasons", "engine"):
            assert key in result
        assert result["verdict"] in VERDICT_ORDER
        assert 0.0 <= result["score"] <= 1.0
        assert result["engine"].startswith("messageguard-rules-v1")
        assert result["legacy_band"] in LEGACY_BANDS.values()
        assert result["families_hit"] == result["families_fired"]
        assert set(result["hits"]) == set(result["families_hit"])
    assert score_message(None)["verdict"] == "LOW"
    assert score_message("💥💥💥 !!!")["score"] >= 0.0


def test_score_message_reason_details_are_catalogue_backed():
    result = score_message(
        "CBI digital arrest! Share your OTP now, else arrest warrant today."
    )
    assert result["reason_details"]
    assert result["reason_codes"]
    for reason in result["reason_details"]:
        assert reason["code"] in REASON_CATALOGUE
        assert REASON_CATALOGUE[reason["code"]][0] == reason["family"]
        assert reason["matched"]
        assert reason["pattern_lang"] in ("en", "hi", "te", "any")


def test_detector_language_filter_is_explicit_and_safe():
    text = "CBI digital arrest! Share your OTP now, else arrest warrant today."
    assert score_message(text, lang="en")["detector_lang"] == "en"
    # Unknown language falls back to all scripts rather than silently missing
    # a Hindi or Telugu scam because a caller asked for French explanations.
    assert score_message(text, lang="fr")["detector_lang"] == "auto"


def test_hindi_negation_guard_does_not_eat_verification_word():
    """Regression: bare `न करें` matched the tail of `सत्यापन करें`."""
    result = analyze(
        "प्रिय ग्राहक, आपका खाता 24 घंटे में बंद हो जाएगा। अभी kyc सत्यापन करें "
        "और अपना UPI PIN सबमिट करें।"
    )
    assert "credential" in result["families_fired"]
    assert "link_grab" in result["families_fired"]
    assert result["verdict"] in ("HIGH", "CRITICAL")


def test_telugu_upi_pin_and_verification_compatibility_rows_fire():
    result = analyze(
        "ప్రియ వినియోగదారుడు, మీ ఖాతా 24 గంటల్లో నిలిపివేయబడుతుంది. వెంటనే "
        "kyc ధృవీకరణ చేసి మీ UPI పిన్ ఇవ్వండి."
    )
    assert "credential" in result["families_fired"]
    assert "link_grab" in result["families_fired"]
    assert result["verdict"] in ("HIGH", "CRITICAL")


def test_legacy_m3_smoke_corpus_still_passes():
    report = evaluate_fixtures(LEGACY_FIXTURES)
    assert report["total"] == 20
    assert report["passed"] == 20
    assert report["accuracy"] >= 0.8


def test_v1_corpus_integrity():
    records = _load_corpus()
    assert len(records) == 492
    assert len({r["id"] for r in records}) == 492
    assert len({r["text"] for r in records}) == 492
    assert sum(r["label"] == "scam" for r in records) == 372
    assert sum(r["label"] == "benign" for r in records) == 120
    assert {r["lang"] for r in records} == {"en", "hi", "te"}
    for record in records:
        assert record["label"] in ("scam", "benign")
        assert set(record.get("families", [])) <= set(FAMILY_WEIGHTS)


def test_committed_messageguard_results_reproduce_exactly():
    committed = json.loads(RESULTS.read_text(encoding="utf-8"))
    assert compute_results() == committed
    assert committed["corpus"]["scam_total"] == 372
    assert committed["corpus"]["benign_total"] == 120
    assert committed["overall"]["accuracy_moderate"] == 0.9654
    assert committed["overall"]["fpr_moderate"] == 0.1167
    report = evaluate_fixtures(V1_FIXTURES)
    assert report["total"] == 492
    assert report["passed"] == 475


def test_reason_catalogue_and_i18n_stay_in_sync():
    expected = {code: entry[0] for code, entry in RAW_CATALOGUE.items()}
    assert i18n.MSG_REASON_FAMILY == expected
    assert i18n.message_reason_codes() == sorted(expected)
    for lang in ("en", "hi", "te"):
        for code in expected:
            sentence = i18n.render_message_reason(code, lang)
            assert sentence
            assert code not in sentence
            assert "{" not in sentence
            if lang == "hi":
                assert any("\u0900" <= ch <= "\u097f" for ch in sentence), code
            if lang == "te":
                assert any("\u0c00" <= ch <= "\u0c7f" for ch in sentence), code


def test_explanation_renders_reason_codes_not_diagnostics():
    result = score_message("Share your OTP now, else your account will be blocked")
    for lang in ("en", "hi", "te"):
        body = i18n.explain_message(result, lang)
        assert body["message_reason_codes"]
        assert all(code in REASON_CATALOGUE for code in body["message_reason_codes"])
        blob = json.dumps(body, ensure_ascii=False).lower()
        assert "score" not in blob
        assert "signal(s)" not in blob
        assert str(result["score"]) not in blob
        assert all(":" not in sentence for sentence in body["reasons"])


def test_citizen_api_serves_integrated_scorer():
    from citizen.api import build_app

    client = TestClient(build_app(bus_url="", poster=lambda e: {"accepted": 1}))
    health = client.get("/api/citizen/health").json()
    assert "messageguard-rules-v1" in health["engine"]

    response = client.post(
        "/api/citizen/screen_message",
        json={"text": "URGENT: CBI digital arrest — transfer fine immediately",
              "lang": "te"},
    ).json()
    assert response["engine"].startswith("messageguard-rules-v1")
    assert response["detector_lang"] == "auto"  # copy language != scam language
    assert response["lang"] == "te"
    assert response["verdict"] in ("HIGH", "CRITICAL")
    assert response["explanation"]["message_reason_codes"]
    assert "score" not in json.dumps(response["explanation"], ensure_ascii=False).lower()
