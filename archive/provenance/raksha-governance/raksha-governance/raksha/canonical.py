"""Canonical serialisation helpers — Phase 3 shared rule.

Every digest uses ``packages.contracts.canonical``. Governance is a
provenance/reference tree; it no longer owns a second canonical JSON rule.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

try:
    from packages.contracts.canonical import (
        CANONICAL_JSON_RULE, GENESIS_PREV, canonical_bytes as _shared_bytes,
        canonical_hash as _shared_hash,
    )
except ImportError:  # pragma: no cover - standalone historical checkout
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from packages.contracts.canonical import (
        CANONICAL_JSON_RULE, GENESIS_PREV, canonical_bytes as _shared_bytes,
        canonical_hash as _shared_hash,
    )


def canonical_bytes(obj: Any) -> bytes:
    """Serialise to canonical JSON bytes using the one shared rule."""
    return _shared_bytes(obj)


def sha256_hex(data: bytes) -> str:
    """Lowercase hex SHA-256 of data."""
    return hashlib.sha256(data).hexdigest()


def canonical_hash(obj: Any) -> str:
    """SHA-256 hex of the canonical JSON serialisation of obj."""
    return _shared_hash(obj)
