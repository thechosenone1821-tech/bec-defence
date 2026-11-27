#!/usr/bin/env python3
"""Check every local Markdown link in the active + provenance tree.

Links to code paths deleted in this working tree are resolved from git's
name-status and count as documented removals, so historical Markdown can stay
unchanged. External http/https, mailto, tel, data and anchor-only links are
ignored.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
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


def _removed_paths(root: pathlib.Path) -> set[str]:
    """Return repository-relative paths deleted or renamed away from HEAD."""
    removed: set[str] = set()
    commands = (
        ["git", "diff", "--name-status", "HEAD", "--"],
        ["git", "status", "--porcelain=v1", "--untracked-files=no"],
    )
    for cmd in commands:
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if proc.returncode != 0:
            continue
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            status = parts[0].strip() if parts else ""
            if status.startswith("D") and len(parts) >= 2:
                target = parts[1].strip()
            elif status.startswith("R") and len(parts) >= 3:
                target = parts[1].strip()
            else:
                target = ""
            if target:
                removed.add(target)
                parent = pathlib.PurePosixPath(target).parent.as_posix()
                while parent and parent != ".":
                    removed.add(parent)
                    parent = pathlib.PurePosixPath(parent).parent.as_posix()
            elif status.startswith("R") and " -> " in line:
                removed.add(line.split(" -> ", 1)[0][3:].strip())
    return removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parents[1]),
                        help="repository root")
    parser.add_argument("--exclude-archive", action="store_true",
                        help="skip archive/provenance Markdown files")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root).resolve()
    removed = _removed_paths(root)
    count = ok = documented = 0
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
                continue
            try:
                resolved_rel = resolved.relative_to(root).as_posix()
            except ValueError:
                resolved_rel = ""
            if resolved_rel in removed or any(resolved_rel.startswith(item + "/") for item in removed if item):
                ok += 1
                documented += 1
            else:
                broken.append((rel, target))
    if broken:
        for rel, target in broken:
            print(f"BROKEN: {rel}: {target}", file=sys.stderr)
        print(f"FAIL: {ok}/{count} local Markdown links resolve", file=sys.stderr)
        return 1
    print(f"OK: {ok}/{count} local Markdown links resolve")
    if documented:
        print(f"OK: {documented} links point at code paths removed in this working tree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
