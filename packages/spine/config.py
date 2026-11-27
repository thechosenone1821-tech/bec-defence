"""Shared pinned config paths for the spine facade."""
from __future__ import annotations

from packages.contracts.config import (
    AUTH_SCOPES,
    BOOT_MANIFEST_PATHS,
    CONFIG_ROOT,
    DEFAULT_BOOT_MANIFEST,
    DEFAULT_LEDGER,
    DEFAULT_POLICY,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TOOL_SCHEMAS,
    DEFAULT_TOPOLOGY,
    PINNED_CONFIG_FILES,
    SPINE_ROOT,
    check_pinned_configs,
)

__all__ = [
    "AUTH_SCOPES", "BOOT_MANIFEST_PATHS", "CONFIG_ROOT", "DEFAULT_BOOT_MANIFEST",
    "DEFAULT_LEDGER", "DEFAULT_POLICY", "DEFAULT_SYSTEM_PROMPT",
    "DEFAULT_TOOL_SCHEMAS", "DEFAULT_TOPOLOGY", "PINNED_CONFIG_FILES",
    "SPINE_ROOT", "check_pinned_configs",
]
