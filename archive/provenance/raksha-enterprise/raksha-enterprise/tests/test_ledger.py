"""Ledger: append-only hash chain, tamper detection, CLI."""

from __future__ import annotations

import json
import sqlite3

import pytest

from raksha.ledger import GENESIS_PREV, LedgerStore, entry_hash, verify_chain
from raksha.ledger.cli import main as cli_main


@pytest.fixture
def store(tmp_path) -> LedgerStore:
    return LedgerStore(tmp_path / "ledger.db")


def test_genesis_links_to_zeroes(store: LedgerStore) -> None:
    head = store.head()
    assert head["seq"] == 0 and head["prev"] == GENESIS_PREV
    assert store.height() == 1


def test_append_and_verify_roundtrip(store: LedgerStore) -> None:
    for i in range(5):
        block = store.append("containment", f"OP-{i}", f"containment ALLOWED: test {i}", {"i": i})
        assert block["seq"] == i + 1
    report = store.verify()
    assert report.ok and report.height == 6
    assert report.head == store.head()["hash"]


def test_prev_links_to_parent(store: LedgerStore) -> None:
    first = store.append("detection", "FUSE-1", "fused", {})
    second = store.append("refusal", "ICU-1", "refused", {})
    assert second["prev"] == first["hash"]


def test_tamper_is_detected_at_exact_block(store: LedgerStore, tmp_path) -> None:
    for i in range(4):
        store.append("containment", f"OP-{i}", f"containment ALLOWED: test {i}", {"i": i})
    # mutate a sealed block directly in SQLite — the chain must catch it
    raw = sqlite3.connect(tmp_path / "ledger.db")
    raw.execute("UPDATE blocks SET text = text || ' ALTERED' WHERE seq = 2")
    raw.commit()
    raw.close()
    report = store.verify()
    assert not report.ok
    assert report.first_bad_seq == 2
    assert "hash mismatch" in report.reason


def test_reorder_is_detected(store: LedgerStore) -> None:
    store.append("detection", "A", "a", {})
    store.append("detection", "B", "b", {})
    entries = store.entries()
    entries[1], entries[2] = entries[2], entries[1]  # swap blocks 1 and 2
    report = verify_chain(entries)
    assert not report.ok


def test_entry_hash_excludes_hash_field() -> None:
    entry = {"seq": 1, "ts": "t", "kind": "k", "ref": "r", "text": "x", "payload": {}, "prev": "p"}
    h1 = entry_hash(entry)
    h2 = entry_hash({**entry, "hash": "forged"})
    assert h1 == h2


def test_cli_verify_exit_codes(tmp_path) -> None:
    db = str(tmp_path / "ledger.db")
    assert cli_main(["verify", "--db", db]) == 0
    store = LedgerStore(db)
    store.append("refusal", "X", "refused", {})
    assert cli_main(["verify", "--db", db]) == 0
    assert cli_main(["append", "--db", db, "--kind", "ops-note", "--ref", "T-1",
                     "--text", "operator note", "--payload-json", json.dumps({"a": 1})]) == 0
    assert LedgerStore(db).height() == 3
