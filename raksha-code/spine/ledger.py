"""SPINE — Append-only SHA-256 hash-chained audit ledger.

Every Governor decision, orchestration bundle, rollback and watchdog event is
appended here. Each entry commits to the previous entry's hash, so any
retroactive edit invalidates the chain (verify() detects it).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, List

try:
    from spine.ledger_anchor import LedgerAnchor
    _ANCHOR_OK = True
except Exception:  # fortress absent: ledger chain still verifies, no side-anchor
    _ANCHOR_OK = False
    LedgerAnchor = None  # type: ignore


class AuditLedger:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.anchor = LedgerAnchor(path + ".anchor") if _ANCHOR_OK else None

    def _read_entries(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        entries = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def append(self, record_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        entries = self._read_entries()
        prev_hash = entries[-1]["hash"] if entries else "GENESIS"
        seq = len(entries)
        entry = {
            "seq": seq,
            "ts": time.time(),
            "record_type": record_type,
            "prev_hash": prev_hash,
            "payload": payload,
        }
        entry["hash"] = self._hash_entry(entry)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":"), default=str) + "\n")
        if self.anchor is not None:
            try:
                self.anchor.pin(seq=seq, head_hash=entry["hash"])
            except Exception:
                pass  # anchor failure must not destroy the record itself
        return entry

    @staticmethod
    def _hash_entry(entry: Dict[str, Any]) -> str:
        body = {k: v for k, v in entry.items() if k != "hash"}
        blob = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(blob.encode()).hexdigest()

    def verify(self) -> Dict[str, Any]:
        base = self._verify_chain()
        if self.anchor is not None and self.anchor.exists():
            cross = self.anchor.verify(base)
            if not cross.get("ok"):
                base = dict(base)
                base["anchor"] = cross
                base["valid"] = False
                base["reason"] = f"ledger anchor mismatch: {cross.get('reason')}"
        return base

    def _verify_chain(self) -> Dict[str, Any]:
        entries = self._read_entries()
        prev = "GENESIS"
        for i, entry in enumerate(entries):
            if entry.get("prev_hash") != prev:
                return {"valid": False, "broken_at_seq": i, "reason": "prev_hash mismatch"}
            if self._hash_entry(entry) != entry.get("hash"):
                return {"valid": False, "broken_at_seq": i, "reason": "entry hash mismatch"}
            prev = entry["hash"]
        return {"valid": True, "entries": len(entries), "head": prev}

    def tail(self, n: int = 10) -> List[Dict[str, Any]]:
        return self._read_entries()[-n:]
