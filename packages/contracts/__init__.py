"""Shared contracts for the separate-but-integrated monorepo."""
from __future__ import annotations

from .separation import (
    ALLOWED_IMPORT_ROOTS,
    APP_NAMES,
    FORBIDDEN_APP_BYPASS_ROOTS,
    FORBIDDEN_CROSS_APP_ROOTS,
    FORBIDDEN_LIVE_EXECUTOR_ROOTS,
    LEGACY_IMPORT_ROOTS,
    VIGIL_RUNTIME_ROOT,
)
from .canonical import (
    CANONICAL_JSON_RULE, canonical_bytes, canonical_entry_hash, canonical_hash,
    canonical_json,
)
from .bands import (
    BAND_EDGES, LEGACY_BANDS, LEGACY_MAX, LEGACY_MIN, VERDICT_ORDER, band,
    to_legacy_band, verdict_at_least,
)
from .reasons import REASON_CATALOGUE, reason_for
from .config import (
    AUTH_SCOPES, BOOT_MANIFEST_PATHS, DEFAULT_LEDGER, DEFAULT_POLICY,
    DEFAULT_TOPOLOGY, PINNED_CONFIG_FILES, check_pinned_configs, config_pins,
    write_config_pins,
)
from .backend import (
    BACKEND_CONTRACT_VERSION, BACKEND_ROUTES, PROFILE_PATHS, contract_card,
    validate_routes,
)
from .envelope import (
    CONTRACT_VERSION, CanonicalEnvelope, EnvelopeValidationError,
    PROFILE_ENTERPRISE_I1, PROFILE_ORGAN_SEALED, PROFILE_ORGAN_TELEMETRY,
    VerificationState, profile_for, require_valid_signature, sign_event,
    validate_envelope, verify_event, verify_signature,
)
from .guard import GateDecision, SharedActionGate, evaluate_governed_action

__all__ = [
    "ALLOWED_IMPORT_ROOTS", "APP_NAMES", "FORBIDDEN_APP_BYPASS_ROOTS",
    "FORBIDDEN_CROSS_APP_ROOTS", "FORBIDDEN_LIVE_EXECUTOR_ROOTS",
    "LEGACY_IMPORT_ROOTS", "VIGIL_RUNTIME_ROOT", "CANONICAL_JSON_RULE",
    "canonical_bytes", "canonical_entry_hash", "canonical_hash",
    "canonical_json", "BAND_EDGES", "LEGACY_BANDS", "LEGACY_MAX",
    "LEGACY_MIN", "VERDICT_ORDER", "band", "to_legacy_band",
    "verdict_at_least", "REASON_CATALOGUE", "reason_for", "AUTH_SCOPES",
    "BOOT_MANIFEST_PATHS", "DEFAULT_LEDGER", "DEFAULT_POLICY", "DEFAULT_TOPOLOGY",
    "PINNED_CONFIG_FILES", "check_pinned_configs", "config_pins",
    "write_config_pins", "BACKEND_CONTRACT_VERSION", "BACKEND_ROUTES",
    "PROFILE_PATHS", "contract_card", "validate_routes", "CONTRACT_VERSION",
    "CanonicalEnvelope", "EnvelopeValidationError", "PROFILE_ENTERPRISE_I1",
    "PROFILE_ORGAN_SEALED", "PROFILE_ORGAN_TELEMETRY", "VerificationState",
    "profile_for", "require_valid_signature", "sign_event", "validate_envelope",
    "verify_event", "verify_signature", "GateDecision", "SharedActionGate",
    "evaluate_governed_action",
]
