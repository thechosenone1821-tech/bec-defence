"""SQLite persistence for raw telemetry and detections.

The ledger is deliberately a separate database: it is the durable, tamper-evident
record; this store is the operational cache that powers queries and the eval
harness. WAL mode keeps readers and the ingest writer concurrency-safe.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id    TEXT PRIMARY KEY,
    ts          TEXT NOT NULL,
    organ       TEXT NOT NULL,
    campaign_id TEXT NOT NULL DEFAULT '',
    case_id     TEXT NOT NULL DEFAULT '',
    leg         TEXT NOT NULL,
    severity    INTEGER NOT NULL,
    entity      TEXT NOT NULL,
    summary     TEXT NOT NULL,
    payload     TEXT NOT NULL,
    sig_alg     TEXT,
    sig         TEXT,
    verified    INTEGER NOT NULL,
    reason      TEXT NOT NULL DEFAULT '',
    received_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_campaign ON events (campaign_id);
CREATE INDEX IF NOT EXISTS ix_events_verified ON events (verified);
CREATE TABLE IF NOT EXISTS detections (
    event_id    TEXT NOT NULL,
    organ       TEXT NOT NULL,
    rule_id     TEXT NOT NULL,
    campaign_id TEXT NOT NULL DEFAULT '',
    case_id     TEXT NOT NULL DEFAULT '',
    leg         TEXT NOT NULL,
    entity      TEXT NOT NULL,
    severity    INTEGER NOT NULL,
    summary     TEXT NOT NULL,
    recorded_at REAL NOT NULL,
    PRIMARY KEY (event_id, organ)
);
"""


class EventStore:
    def __init__(self, path) -> None:  # noqa: ANN001 — Path or ":memory:"
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def save_event(self, event, verified: bool) -> None:  # noqa: ANN001 — events.Event
        raw = event.to_dict()
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO events (event_id, ts, organ, campaign_id, case_id, leg, "
                "severity, entity, summary, payload, sig_alg, sig, verified, reason, received_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (event.event_id, event.ts, event.organ, event.campaign_id, event.case_id,
                 event.leg, event.severity, event.entity, event.summary,
                 json.dumps(raw.get("payload", {}), sort_keys=True),
                 raw.get("sig_alg"), raw.get("sig"), int(verified), "", time.time()),
            )
            self._conn.commit()

    def save_detection(self, detection: dict) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO detections (event_id, organ, rule_id, campaign_id, case_id, "
                "leg, entity, severity, summary, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (detection["event_id"], detection["organ"], detection["rule_id"],
                 detection["campaign_id"], detection["case_id"], detection["leg"],
                 detection["entity"], detection["severity"], detection["summary"], time.time()),
            )
            self._conn.commit()

    def counts(self) -> dict[str, int]:
        with self._lock:
            events = self._conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
            verified = self._conn.execute(
                "SELECT COUNT(*) AS n FROM events WHERE verified = 1").fetchone()["n"]
            detections = self._conn.execute("SELECT COUNT(*) AS n FROM detections").fetchone()["n"]
        return {"events": events, "verified": verified, "detections": detections}

    def list_quarantined(self, limit: int = 200) -> list[dict]:
        """Tampered or unsigned events. Kept for forensics; never actionable."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT event_id, ts, organ, entity, sig, verified, received_at "
                "FROM events WHERE verified = 0 ORDER BY received_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{
            "event_id": r["event_id"], "ts": r["ts"], "organ": r["organ"],
            "entity": r["entity"], "has_signature": bool(r["sig"]), "verified": False,
            "reason": ("signature mismatch — altered after signing" if r["sig"]
                       else "no signature — unverified source"),
        } for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
