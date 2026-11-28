"""Compatibility-cwd boundary tests for the active runtime."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from packages.contracts.separation import (  # noqa: E402
    ALLOWED_IMPORT_ROOTS, FORBIDDEN_CROSS_APP_ROOTS, VIGIL_RUNTIME_ROOT,
)
from tools import check_phase3_contracts  # noqa: E402


def test_separation_contract_checker_is_green():
    assert check_phase3_contracts.main([]) == 0


def test_active_boundaries_are_declared():
    assert VIGIL_RUNTIME_ROOT == "packages/vigil"
    assert "packages" in ALLOWED_IMPORT_ROOTS["apps/citizen"]
    assert "apps.infra" in FORBIDDEN_CROSS_APP_ROOTS["citizen"]
    assert "apps.citizen" in FORBIDDEN_CROSS_APP_ROOTS["infra"]


def test_two_apps_are_importable_independently():
    import subprocess

    citizen = subprocess.run(
        [sys.executable, "-c", "import apps.citizen; import sys; assert not any(m.startswith('apps.infra') for m in sys.modules)"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert citizen.returncode == 0, citizen.stdout + citizen.stderr
    infra = subprocess.run(
        [sys.executable, "-c", "import apps.infra; import sys; assert not any(m.startswith('apps.citizen') or m == 'citizen' for m in sys.modules)"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert infra.returncode == 0, infra.stdout + infra.stderr
