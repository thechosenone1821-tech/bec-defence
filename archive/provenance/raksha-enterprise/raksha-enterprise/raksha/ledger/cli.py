"""Ledger CLI — `python -m raksha.ledger.cli {verify,append,tail,export}`."""

from __future__ import annotations

import argparse
import json
import sys

from .store import LedgerStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="raksha-ledger", description="Project Raksha ledger operations")
    sub = parser.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default="./data/ledger.db", help="ledger database path")

    p_verify = sub.add_parser("verify", parents=[common], help="recompute the whole hash chain")
    p_append = sub.add_parser("append", parents=[common], help="append an operator block (kind/ref/text required)")
    p_append.add_argument("--kind", required=True, help="e.g. containment | refusal | ops-note")
    p_append.add_argument("--ref", required=True)
    p_append.add_argument("--text", required=True)
    p_append.add_argument("--payload-json", default="{}")
    p_tail = sub.add_parser("tail", parents=[common], help="show the last N blocks")
    p_tail.add_argument("-n", type=int, default=5)
    p_export = sub.add_parser("export", parents=[common], help="export the whole chain as JSON lines")
    p_export.add_argument("--out", default="-", help="'-' for stdout")

    args = parser.parse_args(argv)
    store = LedgerStore(args.db)

    if args.cmd == "verify":
        report = store.verify()
        print(json.dumps({
            "ok": report.ok, "height": report.height, "head": report.head[:16],
            "first_bad_seq": report.first_bad_seq, "reason": report.reason,
        }, indent=2))
        return 0 if report.ok else 1

    if args.cmd == "append":
        try:
            payload = json.loads(args.payload_json)
        except json.JSONDecodeError as exc:
            print(f"invalid --payload-json: {exc}", file=sys.stderr)
            return 2
        block = store.append(kind=args.kind, ref=args.ref, text=args.text, payload=payload)
        print(json.dumps(block, indent=2, sort_keys=True))
        return 0

    if args.cmd == "tail":
        entries = store.entries()[-args.n:]
        print(json.dumps(entries, indent=2, sort_keys=True))
        return 0

    if args.cmd == "export":
        lines = [json.dumps(e, sort_keys=True) for e in store.entries()]
        if args.out == "-":
            print("\n".join(lines))
        else:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
