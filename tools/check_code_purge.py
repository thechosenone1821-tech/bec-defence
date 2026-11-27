#!/usr/bin/env python3
"""Prove the retired voice-scorer code and identifiers are gone.

The gate scans every source-controlled text file (including Markdown paths)
for retired module names, route names, scenario identifiers and policy pins.
It deliberately skips its own pattern table. Binary weights and caches are
ignored. Historical prose may mention that code was retired; executable and
generated data may not retain its identifiers.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".git", ".venv", "node_modules", "__pycache__", ".pytest_cache",
    ".cache", ".mypy_cache", ".ruff_cache", "build", "dist", "out",
    "target", "coverage",
}
SKIP_SUFFIXES = {".pt", ".pth", ".pyc", ".png", ".jpg", ".jpeg", ".gif",
                 ".webp", ".ico", ".woff", ".woff2", ".zip", ".gz", ".bin"}
TEXT_SUFFIXES = {
    ".py", ".js", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".txt", ".html", ".css", ".sh", ".lock", ".xml", ".svg", ".md",
}
NAMELESS = {"Makefile", "Dockerfile", "LICENSE"}
RETIRED_NAME = re.compile(
    r"voiceguard|\bmaya\b|run_maya|audio[_-]?screen|audio[_-]?capture|"
    r"frozen_assets|phase4_no_ai|legacy_voiceguard|voiceguard_interface|"
    r"check_frozen_assets",
    re.I,
)
RETIRED_CONTENT = (
    re.compile(r"voiceguard", re.I),
    re.compile(r"\bmaya\b", re.I),
    re.compile(r"run_maya", re.I),
    re.compile(r"audio[_-]?screen", re.I),
    re.compile(r"audio[_-]?capture", re.I),
    re.compile(r"AS-SYNTH", re.I),
    re.compile(r"synth_score|caller_reputation", re.I),
    re.compile(r"CITIZEN_REPORT_VOICE", re.I),
    re.compile(r"voice[-_ ]clone", re.I),
    re.compile(r"frozen_assets\.sha256", re.I),
    re.compile(r"frozen[_-]?audio", re.I),
    re.compile(r"no[_-]?ai[_-]?models?", re.I),
    re.compile(r"NO_AI_TEST_FILES", re.I),
    re.compile(r"RAKSHA_PHASE4_NO_AI_MODELS", re.I),
    re.compile(r"phase4_no_ai_plugin", re.I),
    re.compile(r"check_frozen_assets", re.I),
    re.compile(r"run_audio_eval", re.I),
    re.compile(r"screen_voice", re.I),
    re.compile(r"audio_screen_integrated", re.I),
    re.compile(r"RESERVED_NOT_INTEGRATED", re.I),
    re.compile(r"future phase eleven|phase eleven", re.I),
    re.compile(r"FROZEN\.md", re.I),
    re.compile(r"frozen assets|frozen board", re.I),
)


def _candidate_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in NAMELESS:
            continue
        files.append(path)
    return sorted(files)


def main(argv: list[str] | None = None) -> int:
    problems: list[str] = []
    checked = 0
    own = pathlib.Path(__file__).resolve()
    for path in _candidate_files():
        rel = path.relative_to(ROOT).as_posix()
        if RETIRED_NAME.search(rel):
            problems.append(f"retired path remains: {rel}")
        if path.resolve() == own or path.suffix.lower() == ".md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        checked += 1
        for pattern in RETIRED_CONTENT:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                problems.append(f"retired identifier in {rel}:{line}: {match.group(0)!r}")

    stale_pins = sorted((ROOT / "tools").glob("*.sha256"))
    if stale_pins:
        problems.append(f"hash-pin files remain: {[p.name for p in stale_pins]}")
    residue = ROOT / "VIGIL" / "VIGIL" / "README.md"
    if residue.exists():
        problems.append("upload residue README remains under VIGIL/VIGIL")

    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        print(f"FAIL: retired-code purge incomplete; scanned {checked} text files", file=sys.stderr)
        return 1
    print(f"OK: retired voice-scorer code purged; scanned {checked} text files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
