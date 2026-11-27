"""Phase 2 boundary tests: separate apps, one shared integration layer."""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "raksha-code") not in sys.path:
    sys.path.insert(0, str(ROOT / "raksha-code"))

from packages.contracts.separation import (  # noqa: E402
    ALLOWED_IMPORT_ROOTS,
    FORBIDDEN_CROSS_APP_ROOTS,
)

THIRD_PARTY_ROOTS = {
    "fastapi", "starlette", "uvicorn", "numpy", "pytest", "pydantic",
    "yaml", "httpx", "websockets",
}


def _import_names(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                yield node.module


def _scope_for(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith("apps/citizen/"):
        return "apps/citizen"
    if rel.startswith("apps/infra/"):
        return "apps/infra"
    if rel.startswith("packages/"):
        return "packages"
    return "other"


def _is_allowed(scope: str, name: str) -> bool:
    allowed = ALLOWED_IMPORT_ROOTS[scope]
    return any(name == root or name.startswith(root + ".") for root in allowed)


def test_no_direct_cross_app_imports():
    violations = []
    for path in sorted((ROOT / "apps").rglob("*.py")) + sorted((ROOT / "packages").rglob("*.py")):
        scope = _scope_for(path)
        if scope == "other":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name in _import_names(tree):
            if not _is_allowed(scope, name):
                # Stdlib and declared third-party dependencies are not owned
                # by the app-boundary contract; only RAKSHA-owned roots are.
                top = name.split(".", 1)[0]
                if top in sys.stdlib_module_names or top in THIRD_PARTY_ROOTS:
                    continue
                violations.append((path.relative_to(ROOT).as_posix(), name))
    assert violations == [], f"boundary violations: {violations}"


def test_forbidden_cross_app_roots_are_declared():
    assert "apps.infra" in FORBIDDEN_CROSS_APP_ROOTS["citizen"]
    assert "citizen" in FORBIDDEN_CROSS_APP_ROOTS["infra"]
    assert "apps.citizen" in FORBIDDEN_CROSS_APP_ROOTS["infra"]


def test_frozen_voiceguard_assets_unchanged():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/check_frozen_assets.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_apps_can_be_imported_independently():
    citizen = subprocess.run(
        [sys.executable, "-c", "import apps.citizen; import sys; assert not any(m.startswith('apps.infra') for m in sys.modules)"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert citizen.returncode == 0, citizen.stdout + citizen.stderr
    infra = subprocess.run(
        [sys.executable, "-c", "import apps.infra; import sys; assert not any(m.startswith('apps.citizen') or m == 'citizen' for m in sys.modules)"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert infra.returncode == 0, infra.stdout + infra.stderr


def test_new_app_entrypoints_import():
    citizen = subprocess.run(
        [sys.executable, "-c", "from apps.citizen import build_app; assert callable(build_app)"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert citizen.returncode == 0, citizen.stdout + citizen.stderr
    infra = subprocess.run(
        [sys.executable, "-c", "from apps.infra import create_app; assert callable(create_app)"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert infra.returncode == 0, infra.stdout + infra.stderr
