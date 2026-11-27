"""Shared append-only evidence-ledger boundary."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_LEGACY_CODE_ROOT = Path(__file__).resolve().parents[2] / "raksha-code"
if str(_LEGACY_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LEGACY_CODE_ROOT))

__all__ = [
    "AuditLedger", "LedgerAdapter", "append_record", "verify_ledger",
    "DEFAULT_LEDGER", "main", "RuntimeLedger", "LEDGER_CONTRACT_VERSION",
]


def __getattr__(name: str) -> Any:
    if name == "AuditLedger":
        from .ledger import AuditLedger
        return AuditLedger
    if name in {"LedgerAdapter", "append_record", "verify_ledger"}:
        from . import interface
        return getattr(interface, name)
    if name == "DEFAULT_LEDGER":
        from packages.contracts.config import DEFAULT_LEDGER
        return DEFAULT_LEDGER
    if name == "main":
        from .cli import main
        return main
    if name in {"RuntimeLedger", "LEDGER_CONTRACT_VERSION"}:
        from . import runtime_ledger
        return getattr(runtime_ledger, name)
    raise AttributeError(name)
