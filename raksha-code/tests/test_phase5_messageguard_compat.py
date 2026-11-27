"""Legacy-cwd Phase 5 compatibility tests (deterministic, no AI models)."""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CODE_ROOT = ROOT / "raksha-code"
sys.path[:0] = [str(ROOT), str(CODE_ROOT)]

import citizen.messageguard as mg  # noqa: E402
from tools import run_phase4_pytest  # noqa: E402

CANONICAL_INIT = ROOT / "apps" / "citizen" / "messageguard" / "__init__.py"
ARCHIVE = ROOT / "archive" / "provenance"


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


def test_compat_import_resolves_to_canonical():
    assert pathlib.Path(mg.__file__).resolve() == CANONICAL_INIT.resolve()
    spec = importlib.util.find_spec("citizen.messageguard")
    assert spec is not None
    assert pathlib.Path(spec.origin).resolve() == CANONICAL_INIT.resolve()
    assert mg.SUPPORTED_LANGS == ("auto", "en", "hi", "te", "hinglish")
    assert "538 hand-authored/in-distribution fixtures" in mg.ENGINE
    assert not hasattr(mg, "assess")
    assert not hasattr(mg, "SignalFamilyScorer")


def test_no_second_scorer_importable_from_legacy_cwd():
    # A clean subprocess avoids cross-test sys.path pollution from model-dependent
    # frozen tests that add raksha-code/evals to sys.path when the entire legacy
    # suite is run outside the canonical no-AI runner.
    proc = subprocess.run(
        [sys.executable, "-c",
         "import importlib.util; "
         "assert importlib.util.find_spec('raksha.messageguard') is None; "
         "assert importlib.util.find_spec('messageguard') is None"],
        cwd=CODE_ROOT, env=_env(), capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_detect_language_and_explicit_hinglish_mode():
    assert mg.detect_language("Share your OTP now, else your account will be blocked") == "en"
    assert mg.detect_language("आपका OTP बताइए, वरना खाता बंद हो जाएगा") == "hi"
    assert mg.detect_language("మీ OTP చెప్పండి, లేదంటే ఖాతా బ్లాక్ అవుతుంది") == "te"
    assert mg.detect_language("Aapka OTP batao warna account band ho jayega") == "hinglish"
    result = mg.analyze("Yeh collect request approve karo warna payment cancel",
                        lang="hinglish")
    assert result["score"] >= 0.20
    assert "credential" in result["families_fired"]
    assert "urgency" in result["families_fired"]


def test_legacy_organ_payload_from_compat_result():
    result = mg.score_message("Aapka OTP batao warna account band ho jayega",
                              lang="hinglish")
    for mode in ("band", "clamp"):
        assert 0.25 <= mg.legacy_confidence(result, mode=mode) <= 0.99
    payload = mg.to_legacy_organ_payload(result).to_dict()
    assert payload["organ"] == "messageguard"
    assert payload["band"] == result["verdict"]
    assert payload["message_lang"] == "hinglish"
    assert all(code in mg.REASON_CATALOGUE for code in payload["reason_codes"])
    assert "score" not in payload and "matched" not in payload


def test_cli_compat_module_help_and_sanitized_json():
    help_proc = subprocess.run(
        [sys.executable, "-m", "citizen.messageguard", "--help"],
        cwd=CODE_ROOT, env=_env(), capture_output=True, text=True,
    )
    assert help_proc.returncode == 0
    assert "--lang" in help_proc.stdout and "--citizen-lang" in help_proc.stdout
    proc = subprocess.run(
        [sys.executable, "-m", "citizen.messageguard", "--json", "--lang", "hinglish",
         "Aapka OTP batao warna account band ho jayega"],
        cwd=CODE_ROOT, env=_env(), capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    blob = json.dumps(data, ensure_ascii=False).lower()
    assert "score" not in blob
    assert "hits" not in data and "reason_details" not in data
    assert data["detector_lang"] == "hinglish"
    assert data["citizen"]["helpline"] == "1930"


def test_eval_check_and_provenance_ignores_from_legacy_cwd():
    proc = subprocess.run(
        [sys.executable, "evals/messageguard/run_evals.py", "--check"],
        cwd=CODE_ROOT, env=_env(), capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (ARCHIVE / "README.md").is_file()
    assert (ARCHIVE / "conftest.py").is_file()
    assert (ARCHIVE / "messageguard-alternative" / "PROVENANCE.md").is_file()
    assert (ARCHIVE / "messageguard-snapshot" / "PROVENANCE.md").is_file()
    assert len(run_phase4_pytest.PROVENANCE_IGNORE_DIRS) == 2
    assert all("archive/provenance/" in rel
               for rel in run_phase4_pytest.PROVENANCE_IGNORE_DIRS)
    assert len(run_phase4_pytest.NO_AI_TEST_FILES) == 22
