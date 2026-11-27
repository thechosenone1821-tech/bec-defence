#!/usr/bin/env python3
"""Phase 10 CI gate: no live executor, model or legacy bus imports in active code."""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ACTIVE_ROOTS = (
    ROOT / "apps", ROOT / "packages", ROOT / "evals",
    ROOT / "tools" / "launch_apps.py", ROOT / "tools" / "check_boot_manifest.py",
    ROOT / "tools" / "verify_runtime_ledger.py",
)
PARKED_ADAPTER = ROOT / "apps" / "citizen" / "legacy_voiceguard.py"
FORBIDDEN_PREFIXES = (
    "spine.bus", "spine.slm_client", "spine.orchestrator", "spine.containment",
    "citizen.voiceguard", "voiceguard", "maya", "run_maya",
    "ollama", "transformers", "torch", "tensorflow",
)
FORBIDDEN_SOURCE = (
    re.compile(r"\bclass\s+LiveExecutor\b"),
    re.compile(r"\bdef\s+execute_live\b"),
    re.compile(r"\bexecuted\s*=\s*True\b"),
    re.compile(r"\breal_action\s*=\s*True\b"),
)


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
    for path in _python_files():
        if path == PARKED_ADAPTER:
            # Explicitly parked, read-only future Phase 11 adapter; it is never
            # imported by the active Citizen API (enforced by Phase 4 checker).
            continue
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError as exc:
            problems.append(f"syntax error in {rel}: {exc}")
            continue
        for name in _import_names(tree):
            if any(name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_PREFIXES):
                problems.append(f"forbidden active import in {rel}: {name}")
        for pattern in FORBIDDEN_SOURCE:
            if pattern.search(text):
                problems.append(f"live-executor marker in {rel}: {pattern.pattern}")

    runtime = (ROOT / "packages" / "spine" / "runtime.py").read_text(encoding="utf-8")
    if "DryRunExecutor" not in runtime or "app.state.no_ai_models = True" not in runtime:
        problems.append("unified runtime lost its dry-run/no-AI declaration")
    commander = (ROOT / "packages" / "governance" / "commander.py").read_text(encoding="utf-8")
    if '"enabled": False' not in commander or '"model_invoked": False' not in commander:
        problems.append("Commander card is no longer disabled")

    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print("OK: active code imports no live executor, model, Commander endpoint or legacy bus")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
