"""Boot manifest — SHA-256 pinning of the security-critical config set.

policy.yaml, tool_schemas.json, system_prompt.txt and company_topology.json
define what "safe" means. If an attacker (or a bad deploy) rewrites any of
them, every downstream check is worthless. The manifest pins their hashes at
an audited boot; verification runs BEFORE the Governor accepts the policy.

Usage:
    python -m fortress.boot_manifest --pin  config/manifest.json   # re-baseline (audited!)
    python -m fortress.boot_manifest --check config/manifest.json   # verify; nonzero exit on tamper

Programmatic:
    from fortress.boot_manifest import verify_or_raise
    verify_or_raise('config/manifest.json')     # raises ConfigIntegrityError on mismatch

If no manifest exists, PolicyEngine runs with integrity "UNVERIFIED" and says
so in status() — it never silently pretends to be pinned.
"""

import argparse
import hashlib
import json
import os
import sys
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_HERE)

DEFAULT_PATHS = [
    "config/policy.yaml",
    "config/company_topology.json",
    "commander/tool_schemas.json",
    "commander/system_prompt.txt",
]


class ConfigIntegrityError(RuntimeError):
    pass


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_manifest(paths: list[str] | None = None, base: str = _PROJECT) -> dict[str, Any]:
    entries = {}
    for rel in paths or DEFAULT_PATHS:
        full = os.path.join(base, rel)
        if not os.path.exists(full):
            raise FileNotFoundError(full)
        entries[rel] = {"sha256": _sha256(full), "bytes": os.path.getsize(full)}
    return {"version": 1, "algorithm": "sha256", "files": entries}


def write_manifest(manifest_path: str, base: str = _PROJECT) -> dict[str, Any]:
    manifest = create_manifest(base=base)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    return manifest


def verify_manifest(manifest_path: str, base: str = _PROJECT) -> dict[str, Any]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    mismatches, checked = [], []
    for rel, expected in manifest.get("files", {}).items():
        full = os.path.join(base, rel)
        if not os.path.exists(full):
            mismatches.append({"path": rel, "reason": "missing"})
            continue
        actual = _sha256(full)
        checked.append(rel)
        if actual != expected.get("sha256"):
            mismatches.append({"path": rel, "reason": "sha256 mismatch",
                               "expected": expected.get("sha256"), "actual": actual})
    return {"ok": not mismatches, "checked": checked, "mismatches": mismatches}


def verify_or_raise(manifest_path: str, base: str = _PROJECT) -> dict[str, Any]:
    result = verify_manifest(manifest_path, base=base)
    if not result["ok"]:
        raise ConfigIntegrityError(f"config integrity check failed: {result['mismatches']}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="FORTRESS config manifest")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pin", metavar="MANIFEST", help="create/rewrite the pinned manifest")
    group.add_argument("--check", metavar="MANIFEST", help="verify against the pinned manifest")
    args = parser.parse_args()

    if args.pin:
        manifest = write_manifest(args.pin)
        print(f"pinned {len(manifest['files'])} file(s) -> {args.pin}")
        for rel in manifest["files"]:
            print(f"  {rel}: {manifest['files'][rel]['sha256'][:16]}…")
        return 0

    result = verify_manifest(args.check)
    if result["ok"]:
        print(f"INTEGRITY OK — {len(result['checked'])} security-critical file(s) verified")
        return 0
    print("INTEGRITY FAILURE — refusing to trust this configuration:")
    for m in result["mismatches"]:
        print(f"  {m['path']}: {m['reason']}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
