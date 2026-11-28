"""Root-level active shared-contract acceptance checks."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from packages.contracts import (  # noqa: E402
    ALLOWED_IMPORT_ROOTS, FORBIDDEN_CROSS_APP_ROOTS, PINNED_CONFIG_FILES,
    VIGIL_RUNTIME_ROOT, check_pinned_configs, contract_card,
)
from tools import check_phase3_contracts  # noqa: E402


def test_shared_contract_checker_is_green():
    assert check_phase3_contracts.main([]) == 0


def test_config_pins_and_separation_contract_are_active():
    pins = check_pinned_configs()
    assert pins["ok"] is True
    assert len(pins["checked"]) == len(PINNED_CONFIG_FILES) == 5
    assert VIGIL_RUNTIME_ROOT == "packages/vigil"
    assert "packages" in ALLOWED_IMPORT_ROOTS["apps/citizen"]
    assert "apps.citizen" in FORBIDDEN_CROSS_APP_ROOTS["infra"]
    card = contract_card()
    assert card["contract"] == "raksha-backend-v1"
    assert "profiles" in card and "routes" in card
