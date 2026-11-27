# Ledger package

Phase 3 reconciles the shipped JSONL hash chain, governance reference chain and
enterprise SQLite/WAL chain behind one `append / verify` adapter in
`interface.py`. `cli.py` is the one CLI; the legacy `spine.ledger_cli` module
delegates to it.

```bash
python -m packages.ledger.cli verify --ledger PATH
python -m spine.ledger_cli verify --ledger PATH   # compatibility wrapper
```

Full historical chain consolidation remains a later phase; no app writes the
ledger directly. See
[`../../raksha/PHASE3_CONTRACT_SPINE.md`](../../raksha/PHASE3_CONTRACT_SPINE.md)
and [`../../raksha/PHASE4_CITIZEN_CONSOLIDATION.md`](../../raksha/PHASE4_CITIZEN_CONSOLIDATION.md).
