"""Phase 10 deterministic packaging tests — no AI, no live executor, no third app."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from tools import (  # noqa: E402
    check_boot_manifest, check_frozen_assets, check_no_live_executor,
    check_no_secrets, check_phase910_integration, verify_runtime_ledger,
)


def test_phase910_integration_checker_is_green():
    assert check_phase910_integration.main([]) == 0


def test_exactly_two_apps_and_boot_manifests():
    assert check_boot_manifest.main([]) == 0
    apps = sorted(p.name for p in (ROOT / "apps").iterdir()
                  if p.is_dir() and p.name != "__pycache__")
    assert apps == ["citizen", "infra"]
    for app in apps:
        manifest = json.loads((ROOT / "apps" / app / "BOOT_MANIFEST.json").read_text())
        assert manifest["app"] == app
        assert manifest["app_count"] == 2
        assert manifest["no_ai_models"] is True
        assert manifest["voiceguard_integrated"] is False


def test_no_secrets_no_live_executor_and_ledger_verify():
    assert check_no_secrets.main([]) == 0
    assert check_no_live_executor.main([]) == 0
    assert verify_runtime_ledger.main([]) == 0
    assert check_frozen_assets.main() == 0


def test_one_command_surface_and_ci_gates():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("install:", "test:", "eval:", "run:", "ci-checks:", "ci:"):
        assert target in makefile
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for gate in (
        "run_phase4_pytest", "run_phase4_node_tests", "check_eval_drift",
        "verify_runtime_ledger", "check_boot_manifest", "check_no_secrets",
        "check_no_live_executor", "check_claims_ledger",
    ):
        assert gate in ci
    launcher = (ROOT / "tools" / "launch_apps.py").read_text(encoding="utf-8")
    assert "apps.infra" in launcher and "apps.citizen" in launcher
    assert "third app" in launcher


def test_canonical_docs_archive_and_frozen_board():
    for rel in (
        "summary.md", "README.md", "docs/STATUS.md", "docs/README.md", "CHANGELOG.md",
        "EVALS.md", "raksha/PHASE910_UNIFIED_RELEASE.md",
        "archive/provenance/INTEGRATED.md",
    ):
        assert (ROOT / rel).is_file(), rel
    status = (ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8")
    assert "FROZEN" in status
    assert "VoiceGuard re-entry gate" in status
    assert "Phase Eleven" in status
    roadmap = (ROOT / "raksha" / "COMBINED_SYSTEM_ROADMAP.md").read_text(encoding="utf-8")
    assert "FROZEN" in roadmap
    assert "Phase Eleven" in roadmap
    archive = ROOT / "archive" / "provenance"
    for child in sorted(p for p in archive.iterdir() if p.is_dir()):
        assert (child / "INTEGRATED.md").is_file(), child.name
