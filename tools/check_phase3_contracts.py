#!/usr/bin/env python3
"""Active shared-contract checker.

Verifies config pins, the separation contract, the VIGIL runtime root and the
canonical backend route card. It imports no app or model runtime.
"""
from __future__ import annotations

import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from packages.contracts import (  # noqa: E402
    ALLOWED_IMPORT_ROOTS, FORBIDDEN_CROSS_APP_ROOTS, PINNED_CONFIG_FILES,
    VIGIL_RUNTIME_ROOT, check_pinned_configs, contract_card,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main(argv: list[str] | None = None) -> int:
    try:
        pins: dict[str, Any] = check_pinned_configs()
        check(pins.get("ok") is True, f"config pins did not verify: {pins.get('mismatches')}")
        check(len(pins.get("checked", [])) == len(PINNED_CONFIG_FILES) == 5,
              "shared config pin set changed")
        check(VIGIL_RUNTIME_ROOT == "packages/vigil", "VIGIL runtime root changed")
        check("packages" in ALLOWED_IMPORT_ROOTS["apps/citizen"],
              "Citizen cannot import the shared package layer")
        check("apps.citizen" in FORBIDDEN_CROSS_APP_ROOTS["infra"],
              "Infra cross-app boundary was weakened")
        check("apps.infra" in FORBIDDEN_CROSS_APP_ROOTS["citizen"],
              "Citizen cross-app boundary was weakened")
        card = contract_card()
        check(card["contract"] == "raksha-backend-v1", "backend route card changed")
        check("profiles" in card and "routes" in card, "backend route card is incomplete")
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("OK: active shared contracts, config pins and separation boundaries verify")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
