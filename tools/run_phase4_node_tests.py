#!/usr/bin/env python3
"""Run the active browser tests."""
from __future__ import annotations

import subprocess
from pathlib import Path

from run_phase4_pytest import ACTIVE_NODE_TESTS, ROOT


def main() -> int:
    cmd = ["node", "--test"] + [str(ROOT / rel) for rel in ACTIVE_NODE_TESTS]
    print(f"Active browser tests: {len(ACTIVE_NODE_TESTS)} files")
    return subprocess.run(cmd, cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
