#!/usr/bin/env python3
"""Phase 10 CI gate: verify the active runtime ledger and shared ledger CLI."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from packages.ledger.runtime_ledger import RuntimeLedger  # noqa: E402
from spine.ledger import AuditLedger  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    runtime = RuntimeLedger()
    for index in range(3):
        runtime.append(kind="sandbox-check", ref=f"LEDGER-{index}",
                       text="deterministic CI verification entry",
                       payload={"index": index}, actor="ci")
    result = runtime.verify()
    if not result.get("valid") or result.get("height") != 3:
        print(f"FAIL: runtime ledger did not verify: {result}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = pathlib.Path(tmp) / "audit.jsonl"
        audit = AuditLedger(str(ledger_path))
        audit.append("ci-verify", {"status": "OK"})
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ROOT), str(ROOT / "raksha-code"), env.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        proc = subprocess.run(
            [sys.executable, "-m", "packages.ledger.cli", "verify",
             "--ledger", str(ledger_path)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        if proc.returncode != 0:
            print(f"FAIL: shared ledger CLI verify failed: {proc.stdout}{proc.stderr}",
                  file=sys.stderr)
            return 1
        report = json.loads(proc.stdout)
        if not report.get("valid"):
            print(f"FAIL: shared ledger CLI reported invalid chain: {report}", file=sys.stderr)
            return 1
    print("OK: runtime ledger hash chain and shared ledger CLI verify")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
