#!/usr/bin/env python3
"""Gate: no live executor, legacy bus or Commander client in active code.

VIGIL's CPU inference dependencies are isolated under ``packages/vigil``.
The local VIGIL training script may import teacher-model tooling, but no
Commander/SLM client or live containment path may enter the active runtime.
Infra remains deterministic and dry-run.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ACTIVE_ROOTS = (
    ROOT / "apps", ROOT / "packages", ROOT / "evals",
    ROOT / "tools" / "launch_apps.py", ROOT / "tools" / "check_boot_manifest.py",
    ROOT / "tools" / "verify_runtime_ledger.py", ROOT / "tools" / "check_vigil_assets.py",
    ROOT / "tools" / "run_vigil_smoke.py", ROOT / "tools" / "run_vigil_tests.py",
)
FORBIDDEN_PREFIXES = (
    "spine.bus", "spine.slm_client", "spine.orchestrator", "spine.containment",
    "ollama", "tensorflow",
)
TRAINING_ONLY_PREFIXES = ("transformers", "datasets")
FORBIDDEN_SOURCE = (
    re.compile(r"\bclass\s+LiveExecutor\b"),
    re.compile(r"\bdef\s+execute_live\b"),
    re.compile(r"\bexecuted\s*=\s*True\b"),
    re.compile(r"\breal_action\s*=\s*True\b"),
)
MODEL_RUNTIME_IMPORTS = {"torch", "torchvision", "cv2"}


def _python_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for root in ACTIVE_ROOTS:
        if root.is_file():
            if root.suffix == ".py":
                files.append(root)
        elif root.is_dir():
            files.extend(sorted(p for p in root.rglob("*.py")
                                if "__pycache__" not in p.parts))
    return files


def _import_names(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def main(argv: list[str] | None = None) -> int:
    problems: list[str] = []
    vigil_root = (ROOT / "packages" / "vigil").resolve()
    train_path = (ROOT / "packages" / "vigil" / "train.py").resolve()
    for path in _python_files():
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError as exc:
            problems.append(f"syntax error in {rel}: {exc}")
            continue
        for name in _import_names(tree):
            top = name.split(".", 1)[0]
            if any(name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_PREFIXES):
                problems.append(f"forbidden active import in {rel}: {name}")
            if any(name == prefix or name.startswith(prefix + ".") for prefix in TRAINING_ONLY_PREFIXES):
                if path.resolve() != train_path:
                    problems.append(f"training-only import outside VIGIL train script in {rel}: {name}")
            if top in MODEL_RUNTIME_IMPORTS and vigil_root not in path.resolve().parents:
                problems.append(f"VIGIL runtime import outside packages/vigil in {rel}: {name}")
        for pattern in FORBIDDEN_SOURCE:
            if pattern.search(text):
                problems.append(f"live-executor marker in {rel}: {pattern.pattern}")

    for path in sorted((ROOT / "apps" / "infra").rglob("*.py")):
        for name in _import_names(ast.parse(path.read_text(encoding="utf-8"))):
            if name == "packages.vigil" or name.startswith("packages.vigil."):
                problems.append(f"Infra must not import VIGIL in {path.relative_to(ROOT)}: {name}")

    runtime = (ROOT / "packages" / "spine" / "runtime.py").read_text(encoding="utf-8")
    if "DryRunExecutor" not in runtime or "app.state.model_backed = False" not in runtime:
        problems.append("unified runtime lost its dry-run declaration")
    commander = (ROOT / "packages" / "governance" / "commander.py").read_text(encoding="utf-8")
    if '"enabled": False' not in commander or '"model_invoked": False' not in commander:
        problems.append("Commander card is no longer disabled")

    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print("OK: active code imports no live executor or Commander client; VIGIL runtime isolated in Citizen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
