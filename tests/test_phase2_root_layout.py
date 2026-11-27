"""Root-level checks for visible active app separation."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_active_roots_exist():
    for rel in (
        "apps/citizen", "apps/infra/backend", "apps/infra/detectors",
        "packages/contracts", "packages/spine", "packages/governance",
        "packages/ledger", "packages/vigil", "tools",
    ):
        assert (ROOT / rel).is_dir(), rel


def test_compatibility_symlinks_keep_pwa_assets_in_place():
    assert (ROOT / "apps/citizen/app").is_symlink()
    assert (ROOT / "apps/citizen/fixtures").is_symlink()
    assert (ROOT / "raksha-code/apps").is_symlink()
    assert (ROOT / "packages/vigil/model_manifest.json").is_file()
    assert (ROOT / "packages/vigil/weights/cloakpixel_privacynet_384.torchscript.pt").is_file()
