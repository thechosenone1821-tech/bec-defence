"""Phase 3 — one canonical JSON rule for RAKSHA.

Legacy spine telemetry, enterprise I1 envelopes, governance ledger digests and
Phase 3 shared contracts all delegate to this module. The rule is deliberately
byte-exact: sorted keys, compact separators, ASCII-safe JSON, and ``default=str``
for legacy values already present in shipped events.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

CANONICAL_JSON_RULE = (
    "json.dumps(obj, sort_keys=True, separators=(',', ':'), "
    "ensure_ascii=True, default=str)"
)
GENESIS_PREV = "0" * 64


def canonical_json(obj: Any) -> str:
    """Return the byte-exact canonical JSON string shared by all components."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def canonical_bytes(obj: Any) -> bytes:
    return canonical_json(obj).encode("utf-8")


def canonical_hash(obj: Any) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def canonical_entry_hash(entry: dict[str, Any], hash_field: str = "hash") -> str:
    """Hash a ledger entry without its own hash field."""
    body = {k: v for k, v in entry.items() if k != hash_field}
    return canonical_hash(body)


__all__ = [
    "CANONICAL_JSON_RULE", "GENESIS_PREV", "canonical_json", "canonical_bytes",
    "canonical_hash", "canonical_entry_hash",
]
