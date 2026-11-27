"""Tamper-evident evidence ledger (reference implementation).

Every decision the Governor reaches -- ALLOW, DENY, ESCALATE, forced
reverts, internal failures -- is appended to this hash chain before the
caller sees the outcome. Delete or edit one entry in the middle and
`verify()` names the first broken sequence number.

This is the Part-1 reference implementation: in-memory, single process,
JSONL export for hand-off. Part 2 of the governance build replaces it with
the durable, independently verifiable ledger of the spine (dual write,
periodic anchor, replay tooling) behind the same interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .canonical import canonical_hash

GENESIS_PREV = "0" * 64


@dataclass
class LedgerEntry:
    seq: int
    ts: float
    actor: str          # "governor" or "watchdog"
    tool: str
    action_digest: str
    status: str         # ALLOW / DENY / ESCALATE
    reason: str
    detail: str
    prev_hash: str
    entry_hash: str


def _payload(entry_hash_less: dict) -> str:
    return canonical_hash(entry_hash_less)


class HashChainLedger:
    def __init__(self, sink_path: Optional[str] = None) -> None:
        self.entries: List[LedgerEntry] = []
        self._sink_path = sink_path
        if sink_path:
            import os

            parent = os.path.dirname(sink_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

    def append(
        self,
        ts: float,
        actor: str,
        tool: str,
        action_digest: str,
        status: str,
        reason: str,
        detail: str,
    ) -> LedgerEntry:
        seq = len(self.entries)
        prev_hash = self.entries[-1].entry_hash if self.entries else GENESIS_PREV
        payload = {
            "seq": seq,
            "ts": ts,
            "actor": actor,
            "tool": tool,
            "action_digest": action_digest,
            "status": status,
            "reason": reason,
            "detail": detail,
            "prev_hash": prev_hash,
        }
        entry = LedgerEntry(entry_hash=_payload(payload), **payload)
        self.entries.append(entry)
        if self._sink_path:
            with open(self._sink_path, "a", encoding="utf-8") as fh:
                fh.write(self.to_jsonl_line(entry) + "\n")
        return entry

    def verify(self) -> Tuple[bool, Optional[int]]:
        """Replay the whole chain. Returns (ok, first_bad_seq | None)."""
        prev = GENESIS_PREV
        for entry in self.entries:
            payload = {
                "seq": entry.seq,
                "ts": entry.ts,
                "actor": entry.actor,
                "tool": entry.tool,
                "action_digest": entry.action_digest,
                "status": entry.status,
                "reason": entry.reason,
                "detail": entry.detail,
                "prev_hash": entry.prev_hash,
            }
            if entry.prev_hash != prev or entry.entry_hash != _payload(payload):
                return False, entry.seq
            prev = entry.entry_hash
        return True, None

    def to_jsonl_line(self, e: LedgerEntry) -> str:
        import json

        return json.dumps(
            {
                "seq": e.seq,
                "ts": e.ts,
                "actor": e.actor,
                "tool": e.tool,
                "action_digest": e.action_digest,
                "status": e.status,
                "reason": e.reason,
                "detail": e.detail,
                "prev_hash": e.prev_hash,
                "entry_hash": e.entry_hash,
            },
            sort_keys=True,
        )

    def to_jsonl(self) -> str:
        lines = [self.to_jsonl_line(e) for e in self.entries]
        return "\n".join(lines)

    def tail(self, n: int = 5) -> List[LedgerEntry]:
        return self.entries[-n:]

    def __len__(self) -> int:
        return len(self.entries)
