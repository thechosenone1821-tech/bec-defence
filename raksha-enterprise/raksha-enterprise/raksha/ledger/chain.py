"""Ledger hash-chain primitives (pure functions, fully unit-testable).

Entry canonical form: JSON object without the `hash` field, keys sorted,
compact separators — the same canonicalization as the telemetry envelope.
Genesis links to 64 zeroes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..events import canonical

GENESIS_PREV = "0" * 64


@dataclass(slots=True)
class ChainReport:
    height: int
    ok: bool
    head: str
    first_bad_seq: int | None
    reason: str


def entry_hash(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def genesis(ts: str) -> dict:
    entry = {
        "seq": 0, "ts": ts, "kind": "genesis", "ref": "-",
        "text": "ledger genesis block", "payload": {}, "prev": GENESIS_PREV,
    }
    entry["hash"] = entry_hash(entry)
    return entry


def verify_chain(entries: list[dict]) -> ChainReport:
    """Recompute the whole chain; report the first bad block, if any.
    height is the block COUNT (genesis included), matching LedgerStore.height()."""
    if not entries:
        return ChainReport(0, False, "", None, "ledger is empty")
    prev = GENESIS_PREV
    for entry in entries:
        if entry["prev"] != prev:
            return ChainReport(len(entries), False, prev, entry["seq"],
                               f"block #{entry['seq']} prev-hash does not link to its parent")
        if entry_hash(entry) != entry["hash"]:
            return ChainReport(len(entries), False, prev, entry["seq"],
                               f"block #{entry['seq']} hash mismatch — content altered after sealing")
        prev = entry["hash"]
    return ChainReport(len(entries), True, prev, None, "chain intact")
