#!/usr/bin/env python3
"""Verify the active VIGIL TorchScript weights against the committed manifest."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.vigil.config import DEFAULT_WEIGHTS_CANDIDATES  # noqa: E402

MANIFEST = ROOT / "packages" / "vigil" / "model_manifest.json"
WEIGHTS_DIR = ROOT / "packages" / "vigil" / "weights"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        active = manifest["active_deployment_model"]
        artifacts = manifest["artifacts"]
        for entry in artifacts.values():
            path = WEIGHTS_DIR / entry["filename"]
            if not path.is_file():
                raise RuntimeError(f"missing weight file: {path.relative_to(ROOT)}")
            actual_hash = "sha256:" + sha256(path)
            if actual_hash != entry["sha256"]:
                raise RuntimeError(f"hash mismatch: {entry['filename']}")
            if path.stat().st_size != entry["size_bytes"]:
                raise RuntimeError(f"size mismatch: {entry['filename']}")
        active_entry = artifacts["torchscript_deployment_model"]
        if active["filename"] != active_entry["filename"]:
            raise RuntimeError("active deployment manifest does not point at TorchScript weights")
        if DEFAULT_WEIGHTS_CANDIDATES[0].name != active_entry["filename"]:
            raise RuntimeError("runtime candidate order no longer prefers TorchScript weights")
        stale_pins = sorted((ROOT / "tools").glob("*.sha256"))
        if stale_pins:
            raise RuntimeError(f"hash-pin files remain: {[p.name for p in stale_pins]}")
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("OK: VIGIL TorchScript weights verified; active manifest consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
