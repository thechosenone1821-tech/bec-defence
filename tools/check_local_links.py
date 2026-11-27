#!/usr/bin/env python3
"""Check every local Markdown link in the active + provenance tree.

Counts all relative/absolute local links in ``*.md`` files, including the
Phase 5 ``archive/provenance/`` documents, and fails if any target is missing.
External http/https, mailto, tel, data and anchor-only links are ignored.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

LINK = re.compile(
    r"!?\[[^\]]*\]\(\s*(<[^>]+>|[^)\s]+)(?:\s+\"[^\"]*\")?\s*\)"
)
SKIP_PARTS = {".git", ".venv", "node_modules", "__pycache__"}
EXTERNAL = ("http://", "https://", "mailto:", "tel:", "data:")


def local_target(raw: str) -> str | None:
    target = raw.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if not target or target.startswith(EXTERNAL) or target.startswith("#"):
        return None
    return target.split("#", 1)[0].split("?", 1)[0]


def resolve(root: pathlib.Path, source: pathlib.Path, target: str) -> pathlib.Path:
    if target.startswith("/"):
        return (root / target.lstrip("/")).resolve()
    return (source.parent / target).resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parents[1]),
                        help="repository root")
    parser.add_argument("--exclude-archive", action="store_true",
                        help="skip archive/provenance Markdown files")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root).resolve()
    count = ok = 0
    broken: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if args.exclude_archive and rel.startswith("archive/provenance/"):
            continue
        for match in LINK.finditer(path.read_text(encoding="utf-8")):
            target = local_target(match.group(1))
            if not target:
                continue
            count += 1
            resolved = resolve(root, path, target)
            if resolved.exists():
                ok += 1
            else:
                broken.append((rel, target))
    if broken:
        for rel, target in broken:
            print(f"BROKEN: {rel}: {target}", file=sys.stderr)
        print(f"FAIL: {ok}/{count} local Markdown links resolve", file=sys.stderr)
        return 1
    print(f"OK: {ok}/{count} local Markdown links resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
