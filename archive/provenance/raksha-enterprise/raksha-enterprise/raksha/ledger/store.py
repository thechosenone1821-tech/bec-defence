"""SQLite-backed append-only ledger (Part 7 owns durability; this implements it).

The ledger is append-only at the API level: there is no update or delete path.
Each block stores the full canonical payload so `verify` can recompute the
chain from disk. A single lock serializes writers; reads are concurrent-safe.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time

from .chain import ChainReport, entry_hash, genesis, verify_chain

_SCHEMA = """
CREATE TABLE IF NOT EXISTS blocks (
    seq     INTEGER PRIMARY KEY,
    ts      TEXT NOT NULL,
    kind    TEXT NOT NULL,
    ref     TEXT NOT NULL,
    text    TEXT NOT NULL,
    payload TEXT NOT NULL,
    prev    TEXT NOT NULL,
    hash    TEXT NOT NULL
);
"""


class LedgerStore:
    def __init__(self, path) -> None:  # noqa: ANN001 — Path or ":memory:"
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute(_SCHEMA)
            self._conn.commit()
            if self.height() == 0:
                self._insert(genesis(self._now()))

    @staticmethod
    def _now() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _insert(self, entry: dict) -> dict:
        self._conn.execute(
            "INSERT INTO blocks (seq, ts, kind, ref, text, payload, prev, hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (entry["seq"], entry["ts"], entry["kind"], entry["ref"], entry["text"],
             json.dumps(entry["payload"], sort_keys=True), entry["prev"], entry["hash"]),
        )
        self._conn.commit()
        return dict(entry)

    # -- writes --------------------------------------------------------------
    def append(self, kind: str, ref: str, text: str, payload: dict | None = None) -> dict:
        with self._lock:
            tail = self.head()
            entry = {
                "seq": tail["seq"] + 1,
                "ts": self._now(),
                "kind": kind,
                "ref": ref,
                "text": text,
                "payload": payload or {},
                "prev": tail["hash"],
            }
            entry["hash"] = entry_hash(entry)
            return self._insert(entry)

    # -- reads ---------------------------------------------------------------
    def height(self) -> int:
        row = self._conn.execute("SELECT COALESCE(MAX(seq), -1) AS m FROM blocks").fetchone()
        return int(row["m"]) + 1

    def head(self) -> dict:
        row = self._conn.execute(
            "SELECT * FROM blocks ORDER BY seq DESC LIMIT 1").fetchone()
        return self._row_to_entry(row)

    def entries(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM blocks ORDER BY seq ASC").fetchall()
        return [self._row_to_entry(r) for r in rows]

    def by_kind(self, *kinds: str) -> list[dict]:
        rows = self._conn.execute(
            f"SELECT * FROM blocks WHERE kind IN ({','.join('?' * len(kinds))}) ORDER BY seq ASC",
            kinds,
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    @staticmethod
    def _row_to_entry(row: sqlite3.Row | None) -> dict:
        entry = dict(row)
        entry["payload"] = json.loads(entry["payload"])
        return entry

    def verify(self) -> ChainReport:
        return verify_chain(self.entries())
