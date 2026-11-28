"""Active packaging tests: one command surface, active VIGIL, dry-run Infra."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from tools import (  # noqa: E402
    check_boot_manifest, check_code_purge, check_no_live_executor,
    check_phase910_integration, check_vigil_assets, verify_runtime_ledger,
)


def test_active_integration_checker_is_green():
    assert check_phase910_integration.main([]) == 0


def test_boot_manifests_report_mixed_runtime():
    assert check_boot_manifest.main([]) == 0
    citizen = json.loads((ROOT / "apps/citizen/BOOT_MANIFEST.json").read_text(encoding="utf-8"))
    infra = json.loads((ROOT / "apps/infra/BOOT_MANIFEST.json").read_text(encoding="utf-8"))
    assert citizen["model_backed"] is True and citizen["vigil_integrated"] is True
    assert infra["model_backed"] is False and infra["deterministic"] is True


def test_active_weight_and_purge_gates_are_green():
    assert check_vigil_assets.main([]) == 0
    assert check_code_purge.main([]) == 0
    assert check_no_live_executor.main([]) == 0
    assert verify_runtime_ledger.main([]) == 0
