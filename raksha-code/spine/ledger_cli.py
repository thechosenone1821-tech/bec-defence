"""spine.ledger_cli — audit ledger inspection CLI (M1).

    python -m spine.ledger_cli verify [--ledger PATH]   # hash chain + anchor cross-check
    python -m spine.ledger_cli tail [-n 10] [--ledger PATH]
    python -m spine.ledger_cli replay [--ledger PATH]   # print decisions in order

Exit codes: verify ⇒ 0 ok / 2 tampered or unreadable. tail/replay ⇒ 0 always
(empty ledger is empty, not an error).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEDGER = os.path.join(_HERE, "config", "audit_ledger.jsonl")


def main() -> int:
    parser = argparse.ArgumentParser(description="RAKSHA spine ledger CLI")
    parser.add_argument("command", choices=["verify", "tail", "replay"])
    parser.add_argument("--ledger", default=DEFAULT_LEDGER)
    parser.add_argument("-n", type=int, default=10)
    args = parser.parse_args()

    from spine.ledger import AuditLedger
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
