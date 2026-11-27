#!/usr/bin/env python3
"""Run the deterministic Phase 4 pytest subset with no AI models.

The maintainer's Phase 4 instruction is "don't run any AI models". This runner
therefore ignores every test file that would import frozen VoiceGuard/MAYA,
an SLM/Commander client, the spine bus, or exercise the old voice-scoring
endpoint. Phase 5 also ignores the two archived MessageGuard provenance test
trees so pytest finds one active MessageGuard suite. It registers
``tools.phase4_no_ai_plugin`` so the run fails if a forbidden model module
appears in ``sys.modules``.

Usage:

    python tools/run_phase4_pytest.py                  # from repo root
    python ../tools/run_phase4_pytest.py              # from raksha-code/
    python tools/run_phase4_pytest.py --collect-only
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Explicit, auditable skip list. These are legacy VoiceGuard/MAYA, Commander,
# spine-bus or old /screen_voice tests. Frozen test files are never edited.
NO_AI_TEST_FILES = (
    "raksha-code/tests/test_maya_phase1.py",
    "raksha-code/tests/test_maya_phase2.py",
    "raksha-code/tests/test_maya_phase3.py",
    "raksha-code/tests/test_maya_phase4.py",
    "raksha-code/tests/test_maya_phase5.py",
    "raksha-code/tests/test_voiceguard.py",
    "raksha-code/tests/test_part1_citizen_spine.py",
    "raksha-code/tests/test_part1_phase3.py",
    "raksha-code/tests/test_spine_part1_fusion.py",
    "raksha-code/tests/test_spine_part2_explanation.py",
    "raksha-code/tests/test_spine_part3_capture.py",
    "raksha-code/tests/test_messageguard_integration.py",
    "raksha-code/tests/test_citizen_api.py",
    "raksha-code/tests/test_orchestrator.py",
    "raksha-code/tests/test_m1_campaign_flow.py",
    "raksha-code/tests/test_m5_containment.py",
    "raksha-code/tests/test_organs_contract.py",
    "raksha-code/tests/test_organs_phase2_e2e.py",
    "raksha-code/tests/test_organs_phase3_e2e.py",
    "raksha-code/tests/test_part7_spine_dod.py",
    "raksha-code/tests/test_phase7_fleet_ops.py",
    "raksha-code/tests/test_raavan_killchain.py",
)

# Deterministic Node tests; the frozen MAYA capture JS test is skipped.
NO_AI_NODE_TESTS = (
    "raksha-code/tests/panic_family.test.js",
    "raksha-code/tests/queue.test.js",
    "raksha-code/tests/spine_delivery.test.js",
)

# Phase 5 provenance archives: historical tests, not a second active suite.
PROVENANCE_IGNORE_DIRS = (
    "archive/provenance/messageguard-alternative/raksha/tests",
    "archive/provenance/messageguard-snapshot/raksha/tests",
)


def _pytest_command(pytest_args: list[str]) -> list[str]:
    cmd = [sys.executable, "-m", "pytest", "-q",
           "-p", "tools.phase4_no_ai_plugin"]
    for rel in NO_AI_TEST_FILES:
        cmd.extend(["--ignore", str(ROOT / rel)])
    for rel in PROVENANCE_IGNORE_DIRS:
        cmd.extend(["--ignore", str(ROOT / rel)])
    cmd.extend(pytest_args)
    return cmd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 4 deterministic pytest runner (no AI models)")
    parser.add_argument("--cwd", default=str(Path.cwd()),
                        help="working directory for pytest (repo root or raksha-code/)")
    parser.add_argument("--collect-only", action="store_true",
                        help="collect tests without running them")
    parser.add_argument("--print-skips", action="store_true",
                        help="print the explicit skip list and exit")
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER,
                        help="extra pytest arguments after --")
    args = parser.parse_args(argv)

    if args.print_skips:
        print(f"Python test files skipped: {len(NO_AI_TEST_FILES)}")
        for rel in NO_AI_TEST_FILES:
            print("  -", rel)
        print(f"Node test files skipped: 1 (raksha-code/tests/maya_capture.test.js)")
        print(f"Node test files run: {len(NO_AI_NODE_TESTS)}")
        for rel in NO_AI_NODE_TESTS:
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
    env["OLLAMA_HOST"] = "http://127.0.0.1:9"
    env["EIGENSHIELD_MODEL"] = "disabled"
    env["RAKSHA_PHASE4_NO_AI_MODELS"] = "1"
    env["PYTHONPATH"] = os.pathsep.join([
        str(ROOT), str(ROOT / "raksha-code"),
        env.get("PYTHONPATH", ""),
    ]).rstrip(os.pathsep)

    print(f"Phase 4/5 no-AI pytest: skipping {len(NO_AI_TEST_FILES)} model-dependent test files")
    print(f"Phase 5 provenance test dirs ignored: {len(PROVENANCE_IGNORE_DIRS)}")
    result = subprocess.run(_pytest_command(pytest_args), cwd=args.cwd, env=env)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
