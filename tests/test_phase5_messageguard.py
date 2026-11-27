"""Root-side Phase 5 single-source MessageGuard tests (deterministic, no AI)."""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CODE_ROOT = ROOT / "raksha-code"
sys.path[:0] = [str(ROOT), str(CODE_ROOT)]

from apps.citizen import copy as citizen_copy  # noqa: E402
from apps.citizen.messageguard import (  # noqa: E402
    ENGINE, FAMILY_WEIGHTS, REASON_CATALOGUE, SUPPORTED_LANGS,
    analyze, detect_language, legacy_confidence, score_message,
    to_legacy_organ_payload, verdict_at_least,
)
from apps.citizen.messageguard import tokens_hinglish  # noqa: E402
from apps.citizen.messageguard.normalize import normalize  # noqa: E402
from packages.contracts import i18n, reasons  # noqa: E402
import tools.check_phase5_messageguard as phase5_checker  # noqa: E402

CORPUS = CODE_ROOT / "citizen" / "fixtures" / "messageguard"
RESULTS = CODE_ROOT / "evals" / "messageguard" / "results.json"
GENERATED = ROOT / "raksha" / "MESSAGEGUARD_EVALS.md"


def _env():
    env = dict(os.environ)
    env.update({
        "OLLAMA_HOST": "http://127.0.0.1:9",
        "EIGENSHIELD_MODEL": "disabled",
        "RAKSHA_PHASE4_NO_AI_MODELS": "1",
    })
    env["PYTHONPATH"] = os.pathsep.join([
        str(ROOT), str(CODE_ROOT), env.get("PYTHONPATH", ""),
    ]).rstrip(os.pathsep)
    return env


def _records():
    rows = []
    for path in sorted(CORPUS.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def test_phase5_checker_passes():
    assert phase5_checker.run() == 0


def test_canonical_interface_and_one_reason_catalogue():
    assert SUPPORTED_LANGS == ("auto", "en", "hi", "te", "hinglish")
    assert "538 hand-authored/in-distribution fixtures" in ENGINE
    assert REASON_CATALOGUE is reasons.REASON_CATALOGUE
    assert set(citizen_copy.MSG_REASON_FAMILY) == set(REASON_CATALOGUE)
    assert i18n.message_reason_codes() == sorted(REASON_CATALOGUE)
    for family, code, row_lang, regexes in tokens_hinglish.PATTERNS:
        assert row_lang == "hinglish"
        assert code in REASON_CATALOGUE
        assert REASON_CATALOGUE[code][0] == family
        assert regexes
    import apps.citizen.messageguard as mg
    assert not hasattr(mg, "assess")
    assert not hasattr(mg, "SignalFamilyScorer")


def test_one_corpus_integrity_and_ported_provenance():
    rows = _records()
    assert len(rows) == 538
    assert len({r["id"] for r in rows}) == 538
    assert len({normalize(r["text"]) for r in rows}) == 538
    assert {r["lang"] for r in rows} == {"en", "hi", "te", "hinglish"}
    assert sum(r["label"] == "scam" for r in rows) == 402
    assert sum(r["label"] == "benign" for r in rows) == 136
    hinglish = [r for r in rows if r["lang"] == "hinglish"]
    assert len(hinglish) == 46
    assert sum(r["label"] == "scam" for r in hinglish) == 30
    assert sum(r["label"] == "benign" for r in hinglish) == 16
    assert all(str(r.get("source", "")).startswith("phase5-port:") for r in hinglish)
    for row in rows:
        assert row["label"] in ("scam", "benign")
        assert set(row.get("families", [])) <= set(FAMILY_WEIGHTS)


def test_hinglish_detection_and_negation_regressions():
    for row in [r for r in _records() if r["lang"] == "hinglish"]:
        result = analyze(row["text"], lang="hinglish")
        if row["label"] == "scam":
            assert verdict_at_least(result["verdict"], "MODERATE"), row["id"]
        else:
            assert result["verdict"] == "LOW", row["id"]
        assert set(row.get("families", [])) <= set(result["families_fired"]), row["id"]
    benign_negations = (
        "Paisa lene ke liye kabhi bhi OTP share mat karo. Aapka txn OTP 551204 hai.",
        "HDFC card se Rs.5,000 txn ke liye OTP 448210. Ise kisi ke sath share na karein.",
    )
    for text in benign_negations:
        assert detect_language(text) == "hinglish"
        assert analyze(text, lang="hinglish")["verdict"] == "LOW"
    assert detect_language("Share your OTP now, else your account will be blocked") == "en"


def test_legacy_adapter_and_citizen_safe_cli():
    text = "Aapka OTP batao warna account band ho jayega"
    result = score_message(text, lang="hinglish")
    assert result["detector_lang"] == "hinglish"
    for mode in ("band", "clamp"):
        value = legacy_confidence(result, mode=mode)
        assert 0.25 <= value <= 0.99
    payload = to_legacy_organ_payload(result).to_dict()
    assert payload["organ"] == "messageguard"
    assert payload["band"] == result["verdict"]
    assert payload["message_lang"] == "hinglish"
    assert payload["reason_codes"]
    assert "score" not in payload and "matched" not in payload

    proc = subprocess.run(
        [sys.executable, "-m", "apps.citizen.messageguard", "--lang", "hinglish",
         "--json", "--legacy", "--citizen-lang", "hi", text],
        cwd=ROOT, env=_env(), capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    blob = json.dumps(data, ensure_ascii=False).lower()
    assert "score" not in blob
    assert "hits" not in data and "reason_details" not in data
    assert "matched" not in blob
    assert "SAFE" not in json.dumps(data)
    assert data["citizen"]["helpline"] == "1930"
    plain = subprocess.run(
        [sys.executable, "-m", "apps.citizen.messageguard", text],
        cwd=ROOT, env=_env(), capture_output=True, text=True,
    )
    assert plain.returncode == 0
    assert "score" not in plain.stdout.lower()
    assert "1930" in plain.stdout
    assert text not in plain.stdout


def test_eval_check_and_generated_document_scope():
    proc = subprocess.run(
        [sys.executable, "evals/messageguard/run_evals.py", "--check"],
        cwd=CODE_ROOT, env=_env(), capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    assert results["corpus"]["scam_total"] == 402
    assert results["corpus"]["benign_total"] == 136
    assert results["measurement_scope"].startswith("hand-authored / in-distribution")
    assert "UNMEASURED" in results["measurement_scope"]
    doc = GENERATED.read_text(encoding="utf-8")
    for needle in ("hand-authored / in-distribution", "UNMEASURED", "Hinglish",
                   "one corpus", "one generated eval document", "538"):
        assert needle in doc
    assert importlib.util.find_spec("raksha.messageguard") is None
