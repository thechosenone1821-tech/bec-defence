"""Shared spine facade — Phase 3 contract boundary over legacy runtime."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_LEGACY_CODE_ROOT = Path(__file__).resolve().parents[2] / "raksha-code"
if str(_LEGACY_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LEGACY_CODE_ROOT))

__all__ = [
    "create_app", "sign_event", "verify_event", "validate_envelope",
    "verify_signature", "SeenEventCache", "canonical_bytes", "canonical_json",
    "CANONICAL_JSON_RULE", "sanitize_event", "sanitize_batch", "EntityGraph",
    "DEFAULT_POLICY", "DEFAULT_TOPOLOGY", "DEFAULT_LEDGER", "AUTH_SCOPES",
    "BACKEND_CONTRACT_VERSION", "SPINE_CONTRACT", "contract_card",
    "validate_routes", "check_pinned_configs",
]


def __getattr__(name: str) -> Any:
    if name == "create_app":
        from .runtime import create_app
        return create_app
    if name in {"sign_event", "verify_event", "verify_signature", "SeenEventCache", "validate_envelope"}:
        from . import telemetry_mac
        return getattr(telemetry_mac, name)
    if name in {"canonical_bytes", "canonical_json", "CANONICAL_JSON_RULE"}:
        from packages.contracts import canonical
        return getattr(canonical, name)
    if name in {"sanitize_event", "sanitize_batch"}:
        from . import sanitizer
        return getattr(sanitizer, name)
    if name == "EntityGraph":
        from .entity_graph import EntityGraph
        return EntityGraph
    if name in {"DEFAULT_POLICY", "DEFAULT_TOPOLOGY", "DEFAULT_LEDGER", "AUTH_SCOPES", "check_pinned_configs"}:
        from . import config
        return getattr(config, name)
    if name in {"BACKEND_CONTRACT_VERSION", "SPINE_CONTRACT", "contract_card", "validate_routes"}:
        from . import contract
        return getattr(contract, name)
    raise AttributeError(name)
