"""Canonical serialisation helpers.

Every digest and hash in Raksha governance is computed over *canonical* JSON:
sorted keys, no whitespace, UTF-8. Two components that serialise the same
logical action therefore always produce byte-identical input to SHA-256,
which is what makes digests comparable across the TCB twins and the ledger.

Deterministic by construction: no floats are serialised in digests (actions
carry only strings), and no randomness is used anywhere in this package.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_bytes(obj: Any) -> bytes:
    """Serialise to canonical JSON bytes (sorted keys, no whitespace)."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Lowercase hex SHA-256 of data."""
    return hashlib.sha256(data).hexdigest()


def canonical_hash(obj: Any) -> str:
    """SHA-256 hex of the canonical JSON serialisation of obj."""
    return sha256_hex(canonical_bytes(obj))
