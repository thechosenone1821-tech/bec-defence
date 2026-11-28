"""Phase 3 — one config-pin set, auth-scope list and default shared paths."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SPINE_ROOT = REPO_ROOT / "raksha-code" / "spine"
CONFIG_ROOT = SPINE_ROOT / "config"

DEFAULT_POLICY = CONFIG_ROOT / "policy.yaml"
DEFAULT_TOPOLOGY = CONFIG_ROOT / "company_topology.json"
DEFAULT_TOOL_SCHEMAS = SPINE_ROOT / "tool_schemas.json"
DEFAULT_SYSTEM_PROMPT = SPINE_ROOT / "system_prompt.txt"
DEFAULT_BOOT_MANIFEST = CONFIG_ROOT / "manifest.json"
DEFAULT_LEDGER = CONFIG_ROOT / "audit_ledger.jsonl"
PIN_MANIFEST = Path(__file__).resolve().parent / "config_pins.json"

BOOT_MANIFEST_PATHS = (
    "config/policy.yaml",
    "config/company_topology.json",
    "tool_schemas.json",
    "system_prompt.txt",
)
PINNED_CONFIG_FILES = BOOT_MANIFEST_PATHS + ("config/manifest.json",)

AUTH_SCOPES = ("telemetry:write", "read", "admin")
BUS_KEY_ENV = "EIGENSHIELD_BUS_KEY"
RPC_KEY_ENV = "EIGENSHIELD_RPC_SECRET"
SENSOR_KEY_ENV = "RAKSHA_SENSOR_KEY"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config_pins() -> dict[str, Any]:
    """Compute the source-controlled Phase 3 config-pin manifest."""
    from .canonical import CANONICAL_JSON_RULE

    files: dict[str, Any] = {}
    for rel in PINNED_CONFIG_FILES:
        path = SPINE_ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(path)
        files[rel] = {"sha256": _sha256(path), "bytes": path.stat().st_size}
    return {
        "contract": "raksha-config-pins-v1",
        "version": 1,
        "algorithm": "sha256",
        "canonical_json_rule": CANONICAL_JSON_RULE,
        "base": "raksha-code/spine",
        "files": files,
    }


def write_config_pins() -> dict[str, Any]:
    pins = config_pins()
    PIN_MANIFEST.write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return pins


def check_pinned_configs() -> dict[str, Any]:
    """Compare live config hashes with the committed pin manifest and boot manifest."""
    if not PIN_MANIFEST.is_file():
        return {"ok": False, "checked": [], "mismatches": [{"path": str(PIN_MANIFEST), "reason": "missing pin manifest"}]}
    expected = json.loads(PIN_MANIFEST.read_text(encoding="utf-8"))
    actual = config_pins()
    mismatches: list[dict[str, Any]] = []
    checked: list[str] = []
    for rel in PINNED_CONFIG_FILES:
        checked.append(rel)
        if expected.get("files", {}).get(rel) != actual["files"].get(rel):
            mismatches.append({"path": rel, "reason": "pin mismatch", "expected": expected.get("files", {}).get(rel), "actual": actual["files"].get(rel)})
    try:
        from spine.boot_manifest import verify_manifest
        boot = verify_manifest(str(DEFAULT_BOOT_MANIFEST), base=str(SPINE_ROOT))
        if not boot.get("ok"):
            mismatches.append({"path": "config/manifest.json", "reason": "boot manifest mismatch", "detail": boot})
    except Exception as exc:
        mismatches.append({"path": "config/manifest.json", "reason": f"boot manifest unavailable: {exc}"})
    return {"ok": not mismatches, "checked": checked, "mismatches": mismatches, "boot_manifest": boot if "boot" in locals() else None}


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Phase 3 config pin checker")
    parser.add_argument("--write", "--write-pins", dest="write", action="store_true",
                        help="rewrite packages/contracts/config_pins.json")
    args = parser.parse_args(argv)
    if args.write:
        write_config_pins()
        print(f"OK: wrote {PIN_MANIFEST.relative_to(REPO_ROOT)}")
        return 0
    report = check_pinned_configs()
    if not report["ok"]:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
        return 2
    print(f"OK: {len(report['checked'])} shared config pins unchanged.")
    return 0


__all__ = [
    "REPO_ROOT", "SPINE_ROOT", "CONFIG_ROOT", "DEFAULT_POLICY", "DEFAULT_TOPOLOGY",
    "DEFAULT_TOOL_SCHEMAS", "DEFAULT_SYSTEM_PROMPT", "DEFAULT_BOOT_MANIFEST",
    "DEFAULT_LEDGER", "PIN_MANIFEST", "BOOT_MANIFEST_PATHS", "PINNED_CONFIG_FILES",
    "AUTH_SCOPES", "BUS_KEY_ENV", "RPC_KEY_ENV", "SENSOR_KEY_ENV", "config_pins",
    "write_config_pins", "check_pinned_configs", "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
