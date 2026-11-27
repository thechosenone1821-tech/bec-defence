"""Root-level checks for visible app separation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase2_roots_exist():
    for rel in (
        "apps/citizen", "apps/infra/backend", "apps/infra/detectors",
        "packages/contracts", "packages/spine", "packages/governance",
        "packages/ledger", "tools",
    ):
        assert (ROOT / rel).is_dir(), rel


def test_compatibility_symlinks_keep_frozen_assets_in_place():
    assert (ROOT / "apps/citizen/app").is_symlink()
    assert (ROOT / "apps/citizen/fixtures").is_symlink()
    assert (ROOT / "raksha-code/citizen/voiceguard/FROZEN.md").is_file()
    assert (ROOT / "raksha-code/apps").is_symlink()
    assert (ROOT / "raksha-code/packages").is_symlink()
    assert (ROOT / "raksha-code/citizen/api.py").is_symlink()
    assert (ROOT / "raksha-code/citizen/messageguard").is_symlink()
    assert (ROOT / "raksha-code/citizen/risk").is_symlink()
