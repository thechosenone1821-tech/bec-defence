"""Root-level Phase 4 Citizen acceptance checks (deterministic, model-free)."""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from apps.citizen.api import APP_DIR, build_app  # noqa: E402
from apps.citizen import copy as citizen_copy  # noqa: E402
from apps.citizen import features  # noqa: E402


def _client(captured=None):
    return TestClient(build_app(
        bus_url="",
        poster=lambda event: captured.append(event) or {"accepted": 1}
        if captured is not None else {"accepted": 1},
    ))


def test_phase4_checker_passes():
    env = {**dict(os.environ), "OLLAMA_HOST": "http://127.0.0.1:9",
           "EIGENSHIELD_MODEL": "disabled"}
    result = subprocess.run([sys.executable, str(ROOT / "tools/check_phase4_citizen.py")],
                            cwd=ROOT, capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "no AI model invoked" in result.stdout


def test_exactly_one_physical_citizen_service_and_pwa_shell():
    api_paths = {p.resolve() for p in [
        ROOT / "apps/citizen/api.py",
        ROOT / "raksha-code/citizen/api.py",
        ROOT / "raksha-code/apps/citizen/api.py",
    ]}
    assert len(api_paths) == 1
    htmls = {p.resolve() for p in list((ROOT / "apps/citizen").rglob("index.html")) +
             list((ROOT / "raksha-code/citizen/app").rglob("index.html"))}
    manifests = {p.resolve() for p in list((ROOT / "apps/citizen").rglob("manifest.json")) +
                 list((ROOT / "raksha-code/citizen/app").rglob("manifest.json"))}
    assert len(htmls) == 1 and len(manifests) == 1


def test_voiceguard_disabled_and_active_service_loads_no_model_modules():
    env = {**dict(os.environ), "OLLAMA_HOST": "http://127.0.0.1:9",
           "EIGENSHIELD_MODEL": "disabled"}
    probe = subprocess.run([
        sys.executable, "-c",
        "import sys; from pathlib import Path; r=Path.cwd(); "
        "sys.path[:0]=[str(r),str(r/'raksha-code')]; import apps.citizen.api as a; "
        "assert a.VOICEGUARD_ENABLED is False; "
        "assert not any(m.startswith('citizen.voiceguard') or m.startswith('spine.slm_client') "
        "for m in sys.modules); print('ok')",
    ], cwd=ROOT, capture_output=True, text=True, env=env)
    assert probe.returncode == 0, probe.stdout + probe.stderr

    client = _client()
    features_body = client.get("/api/citizen/features").json()
    assert features_body["no_ai_models"] is True
    assert features_body["features"]["voiceguard"] is False
    assert features_body["voiceguard"]["status"] == "not integrated yet"
    assert features_body["voiceguard"]["model_invoked"] is False
    assert features_body["voiceguard_interface"]["enabled"] is False

    screen = client.post("/api/citizen/screen_voice",
                         json={"consent": True, "samples": [0.0] * 600}).json()
    assert screen["status"] == "NOT_INTEGRATED"
    assert screen["verdict"] == "INCONCLUSIVE"
    assert screen["audio_processed"] is False
    assert screen["model_invoked"] is False
    assert "samples" not in screen
    assert "not integrated yet" in screen["explanation"]["title"]


def test_message_risk_report_and_multilingual_copy_work_end_to_end():
    captured = []
    client = _client(captured)
    for lang in ("en", "hi", "te"):
        msg = client.post("/api/citizen/screen_message",
                          json={"text": "URGENT: share your OTP now or account blocked",
                                "lang": lang}).json()
        assert msg["lang"] == lang
        assert msg["explanation"]["lang"] == lang
        assert msg["explanation"]["message_reason_codes"]
        assert "score" not in json.dumps(msg["explanation"], ensure_ascii=False).lower()
        assert "SAFE" not in json.dumps(msg["explanation"], ensure_ascii=False).upper()

        risk = client.post("/api/citizen/assess",
                           json={"message": {"verdict": msg["verdict"]},
                                 "user_doubt": True, "lang": lang}).json()
        assert risk["lang"] == lang
        assert risk["band"] != "SAFE"
        assert risk["helpline"] == "1930"
        assert risk["action"]

        report = client.post("/api/citizen/report",
                             json={"category": "message", "severity": 0.8,
                                   "lang": lang,
                                   "note": "raw PII must not leave phone"}).json()
        assert report["status"] == "REPORTED"
        assert report["lang"] == lang
        assert report["explanation"]["lang"] == lang
        assert "raw PII must not leave phone" not in json.dumps(captured[-1])
        assert captured[-1]["entities"] == {}


def test_voice_tab_runtime_shell_is_honest_and_no_clone_claim():
    client = _client()
    html = client.get("/app/").text
    assert "not integrated yet" in html
    assert 'src="phase4.js"' in html
    js = client.get("/app/phase4.js").text
    assert client.get("/_citizen/phase4.js").text == js
    assert "not integrated yet" in js
    assert "fetch(" not in js and "score_voice" not in js
    manifest = client.get("/app/manifest.json").json()
    assert "not integrated yet" in manifest["description"]
    assert "voice-clone" not in manifest["description"].lower()
    assert "clone detection" not in manifest["description"].lower()
    assert manifest["phase4"]["no_ai_models"] is True


def test_phase4_no_ai_test_policy_is_explicit():
    from tools.run_phase4_pytest import NO_AI_NODE_TESTS, NO_AI_TEST_FILES

    assert len(NO_AI_TEST_FILES) >= 20
    assert all(rel.startswith(("raksha-code/tests/", "tests/"))
               for rel in NO_AI_TEST_FILES)
    assert all((ROOT / rel).is_file() for rel in NO_AI_TEST_FILES)
    assert "tests/test_phase4_citizen.py" not in NO_AI_TEST_FILES
    assert "raksha-code/tests/test_phase4_citizen_compat.py" not in NO_AI_TEST_FILES
    assert "raksha-code/tests/maya_capture.test.js" not in NO_AI_NODE_TESTS
    assert len(NO_AI_NODE_TESTS) == 3


def test_phase4_docs_and_model_free_modules_exist():
    for rel in ("raksha/PHASE4_CITIZEN_CONSOLIDATION.md",
                "raksha/adr/ADR-012-citizen-consolidation.md",
                "apps/citizen/features.py", "apps/citizen/copy.py",
                "apps/citizen/retention.py", "apps/citizen/voiceguard_interface.py",
                "apps/citizen/phase4_shell.py", "packages/contracts/i18n.py",
                "tools/check_phase4_citizen.py"):
        assert (ROOT / rel).is_file(), rel
    assert citizen_copy.CONTRACT_VERSION == "raksha-citizen-i18n-v1"
    assert features.NO_AI_MODELS is True
    tree = ast.parse((ROOT / "packages/contracts/i18n.py").read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.append(node.module)
    assert not any(name.startswith(("apps", "citizen", "voiceguard", "maya")) for name in imports)
