"""Shared backend/envelope contract surface for the spine package."""
from __future__ import annotations

from packages.contracts.backend import (
    BACKEND_CONTRACT_VERSION,
    BACKEND_ROUTES,
    PROFILE_PATHS,
    contract_card,
    validate_routes,
)
from packages.contracts.canonical import CANONICAL_JSON_RULE
from packages.contracts.envelope import CONTRACT_VERSION as EVENT_CONTRACT_VERSION

SPINE_CONTRACT = {
    "backend": BACKEND_CONTRACT_VERSION,
    "event": EVENT_CONTRACT_VERSION,
    "canonical_json": CANONICAL_JSON_RULE,
    "signature_required": True,
    "governor_required": True,
    "append_only_ledger": True,
}

__all__ = [
    "BACKEND_CONTRACT_VERSION", "BACKEND_ROUTES", "PROFILE_PATHS",
    "EVENT_CONTRACT_VERSION", "CANONICAL_JSON_RULE", "SPINE_CONTRACT",
    "contract_card", "validate_routes",
]
