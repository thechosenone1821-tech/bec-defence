#!/usr/bin/env python3
"""Verify VoiceGuard/MAYA assets were not edited or moved by Phase 2."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tools" / "frozen_assets.sha256"
FROZEN_DIRS = (
    ROOT / "raksha-code" / "citizen" / "voiceguard",
    ROOT / "raksha-code" / "citizen" / "app",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    expected = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, rel = line.split("  ", 1)
        expected[rel] = digest

    current = {}
    for directory in FROZEN_DIRS:
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            rel = path.relative_to(ROOT).as_posix()
            current[rel] = sha256(path)
    for rel in (
        "raksha-code/evals/run_maya.py",
        "MAYA_BUILD.md",
        "VOICEGUARD_ROADMAP.md",
        "specs/02_citizen_voiceguard.md",
    ):
        path = ROOT / rel
        if path.is_file():
            current[rel] = sha256(path)

    missing = sorted(set(expected) - set(current))
    added = sorted(set(current) - set(expected))
    changed = sorted(rel for rel in expected.keys() & current.keys()
                     if expected[rel] != current[rel])
    if missing or added or changed:
        print("FROZEN ASSET CHECK FAILED")
        for label, rows in (("missing", missing), ("added", added), ("changed", changed)):
            if rows:
                print(f"  {label}:")
                for row in rows:
                    print(f"    {row}")
        return 1
    print(f"OK: {len(expected)} VoiceGuard/MAYA assets unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
