"""Phase 7 — append-only in-memory evidence ledger for the active runtime.

Only ``SafetyRuntime._seal`` calls :meth:`RuntimeLedger.append`; API operator
notes are routed through the same seal method. Verification recomputes the
whole canonical hash chain from genesis.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from packages.contracts.canonical import GENESIS_PREV, canonical_hash

LEDGER_CONTRACT_VERSION = "raksha-runtime-ledger-v1"


@dataclass(frozen=True)
class LedgerEntry:
    seq: int
    ts: str
    kind: str
    ref: str
    text: str
    payload: dict[str, Any]
    actor: str
    prev: str
    hash: str

    def body(self) -> dict[str, Any]:
        return {
            "seq": self.seq, "ts": self.ts, "kind": self.kind, "ref": self.ref,
            "text": self.text, "payload": self.payload, "actor": self.actor,
            "prev": self.prev,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.body(), "hash": self.hash}


class RuntimeLedger:
    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []
        self._lock = threading.RLock()

    def append(self, *, kind: str, ref: str, text: str,
               payload: dict[str, Any] | None = None,
               actor: str = "SafetyRuntime") -> dict[str, Any]:
        with self._lock:
            seq = len(self._entries) + 1
            prev = self._entries[-1].hash if self._entries else GENESIS_PREV
            body = {
                "seq": seq, "ts": f"P6-P8-LEDGER-{seq:06d}", "kind": kind,
                "ref": ref, "text": text, "payload": dict(payload or {}),
                "actor": actor, "prev": prev,
            }
            digest = canonical_hash(body)
            entry = LedgerEntry(**body, hash=digest)
            self._entries.append(entry)
            return entry.to_dict()

    def entries(self) -> list[dict[str, Any]]:
        with self._lock:
            return [entry.to_dict() for entry in self._entries]

    def by_kind(self, *kinds: str) -> list[dict[str, Any]]:
        wanted = set(kinds)
        return [entry for entry in self.entries() if entry["kind"] in wanted]

    def head(self) -> dict[str, Any]:
        with self._lock:
            if not self._entries:
                return {"seq": 0, "hash": GENESIS_PREV, "ts": "GENESIS"}
            return self._entries[-1].to_dict()

    def height(self) -> int:
        with self._lock:
            return len(self._entries)

    def verify(self) -> dict[str, Any]:
        with self._lock:
            prev = GENESIS_PREV
            for entry in self._entries:
                body = {k: v for k, v in entry.to_dict().items() if k != "hash"}
                expected = canonical_hash(body)
                if entry.prev != prev or entry.hash != expected:
                    return {"ok": False, "valid": False, "height": len(self._entries),
                            "head": self._entries[-1].hash if self._entries else GENESIS_PREV,
                            "first_bad_seq": entry.seq, "reason": "canonical hash chain mismatch"}
                prev = entry.hash
            return {"ok": True, "valid": True, "height": len(self._entries),
                    "head": prev, "first_bad_seq": None, "reason": "chain intact"}


__all__ = ["LEDGER_CONTRACT_VERSION", "LedgerEntry", "RuntimeLedger"]
