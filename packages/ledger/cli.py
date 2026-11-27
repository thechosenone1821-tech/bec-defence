"""One Phase 3 ledger CLI: python -m packages.ledger.cli verify --ledger PATH."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from packages.contracts.config import DEFAULT_LEDGER

from .ledger import AuditLedger

DEFAULT_LEDGER_PATH = str(Path(__file__).resolve().parents[2] / "raksha-code" / "spine" / "config" / "audit_ledger.jsonl")
# Use the shared pinned path when available; the computed fallback keeps this
# module importable in a minimal checkout.
DEFAULT_LEDGER_PATH = str(DEFAULT_LEDGER or DEFAULT_LEDGER_PATH)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RAKSHA shared ledger CLI")
    parser.add_argument("command", choices=["verify", "tail", "replay"])
    parser.add_argument("--ledger", default=DEFAULT_LEDGER_PATH)
    parser.add_argument("-n", type=int, default=10)
    args = parser.parse_args(argv)

    ledger = AuditLedger(args.ledger)
    if args.command == "verify":
        result = ledger.verify()
        print(json.dumps(result, indent=2))
        return 0 if result.get("valid") else 2

    entries = ledger.tail(args.n if args.command == "tail" else 1_000_000)
    for entry in entries:
        payload = entry.get("payload", {})
        summary = (payload.get("decision") or payload.get("status")
                   or payload.get("tool") or json.dumps(payload)[:80])
        print(f"seq={entry.get('seq')} {entry.get('record_type')}: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
