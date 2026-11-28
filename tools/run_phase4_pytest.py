#!/usr/bin/env python3
"""Run the active pytest suite with the VIGIL runtime import policy."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ACTIVE_PYTEST_PATHS = (
    "tests",
    "raksha-code/tests",
    "packages/vigil/tests",
)
ACTIVE_NODE_TESTS = (
    "raksha-code/tests/panic_family.test.js",
    "raksha-code/tests/queue.test.js",
    "raksha-code/tests/spine_delivery.test.js",
    "raksha-code/tests/infra_hospital_demo.test.js",
)
PROVENANCE_IGNORE_DIRS = (
    "archive/provenance/messageguard-alternative/raksha/tests",
    "archive/provenance/messageguard-snapshot/raksha/tests",
)


def _pytest_command(pytest_args: list[str], cwd: Path) -> list[str]:
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "tools.vigil_runtime_plugin"]
    for rel in PROVENANCE_IGNORE_DIRS:
        cmd.extend(["--ignore", str(ROOT / rel)])
    if cwd.resolve() == ROOT.resolve():
        cmd.extend(ACTIVE_PYTEST_PATHS)
    else:
        cmd.append("tests")
    cmd.extend(pytest_args)
    return cmd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Active runtime pytest runner")
    parser.add_argument("--cwd", default=str(Path.cwd()))
    parser.add_argument("--collect-only", action="store_true")
    parser.add_argument("--print-skips", action="store_true")
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    if args.print_skips:
        print(f"Active pytest paths: {len(ACTIVE_PYTEST_PATHS)}")
        for rel in ACTIVE_PYTEST_PATHS:
            print("  +", rel)
        print(f"Browser test files: {len(ACTIVE_NODE_TESTS)}")
        for rel in ACTIVE_NODE_TESTS:
            print("  +", rel)
        print(f"Archived provenance test dirs ignored: {len(PROVENANCE_IGNORE_DIRS)}")
        for rel in PROVENANCE_IGNORE_DIRS:
            print("  -", rel)
        return 0

    pytest_args = list(args.pytest_args)
    if pytest_args and pytest_args[0] == "--":
        pytest_args = pytest_args[1:]
    if args.collect_only:
        pytest_args.insert(0, "--collect-only")

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([
        str(ROOT), str(ROOT / "raksha-code"), env.get("PYTHONPATH", ""),
    ]).rstrip(os.pathsep)

    cwd = Path(args.cwd)
    print(f"Active runtime pytest: {len(ACTIVE_PYTEST_PATHS)} root paths; {len(PROVENANCE_IGNORE_DIRS)} archived dirs ignored")
    result = subprocess.run(_pytest_command(pytest_args, cwd), cwd=cwd, env=env)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
