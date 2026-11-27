#!/usr/bin/env python3
"""Run deterministic Phase 4 Node tests, skipping frozen MAYA capture tests."""
from __future__ import annotations

import subprocess
from pathlib import Path

from run_phase4_pytest import NO_AI_NODE_TESTS, ROOT


def main() -> int:
    cmd = ["node", "--test"] + [str(ROOT / rel) for rel in NO_AI_NODE_TESTS]
    print(f"Phase 4 no-AI Node tests: {len(NO_AI_NODE_TESTS)} files; MAYA capture test skipped")
    return subprocess.run(cmd, cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
