#!/usr/bin/env python3
"""Phase 10 CI gate: no committed secrets or credential files outside provenance."""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache",
              "archive", "build", "dist", "out", "target", ".next", ".cache"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".webp",
                 ".mp3", ".wav", ".ogg", ".opus", ".flac", ".m4a", ".zip",
                 ".pdf", ".sha256"}
BAD_NAMES = {".env", "id_rsa", "id_dsa", "credentials.json", "secrets.json"}
BAD_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|DSA|PRIVATE) KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret[_-]?key|password)\s*[:=]\s*['\"][A-Za-z0-9/+_-]{16,}['\"]"),
)


def main(argv: list[str] | None = None) -> int:
    problems: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT).as_posix()
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.name in BAD_NAMES or path.suffix.lower() in BAD_SUFFIXES:
            problems.append(f"credential-shaped file: {rel}")
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in PATTERNS:
            if pattern.search(text):
                problems.append(f"secret-shaped content in {rel}: {pattern.pattern}")
                break
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print("OK: no secrets or credential files in active sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
