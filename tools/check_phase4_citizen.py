#!/usr/bin/env python3
"""Phase 4 deterministic Citizen consolidation checker.

No AI model is invoked or imported by this checker. It proves:

* exactly one Citizen service and one physical PWA shell;
* VoiceGuard/MAYA is hard-disabled behind a documented interface;
* app-owned active code does not import frozen VoiceGuard/model modules;
* citizen-facing sentences live in ``apps/citizen/copy.py`` and rendering logic
  lives in ``packages/contracts/i18n.py``;
* the runtime shell says "not integrated yet" and makes no clone-detection claim;
* no raw score, SAFE reassurance, or PII-forwarding invariant is weakened;
* frozen VoiceGuard/MAYA assets remain hash-pinned.
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

ACTIVE = ROOT / "apps/citizen"
ADAPTER = ACTIVE / "legacy_voiceguard.py"
FROZEN_APP = ROOT / "raksha-code/citizen/app"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _import_names(tree: ast.AST) -> Iterable[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module
        elif isinstance(node, ast.ImportFrom) and node.level > 0:
            yield "." * node.level + (node.module or "")


def _call_names(tree: ast.AST) -> Iterable[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                yield f.id
            elif isinstance(f, ast.Attribute):
                yield f.attr


def _py_files(root: Path):
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _unique_physical(paths: Iterable[Path]) -> set[Path]:
    return {p.resolve() for p in paths if p.exists()}


def run_checks() -> list[str]:
    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    # Import app-owned modules only. None may load a frozen VoiceGuard model.
    before = set(sys.modules)
    from apps.citizen import copy as citizen_copy
    from apps.citizen import features
    from apps.citizen import phase4_shell
    from apps.citizen import voiceguard_interface
    from apps.citizen.api import APP_DIR, VOICEGUARD_ENABLED, build_app
    from packages.contracts.i18n import CONTRACT_VERSION, CitizenRenderer
    loaded_frozen = sorted(m for m in set(sys.modules) - before
                           if m.startswith("citizen.voiceguard"))
    check(not loaded_frozen, f"active Citizen imports loaded frozen VoiceGuard modules: {loaded_frozen}")

    # Flags and documented disabled interface.
    check(features.NO_AI_MODELS is True, "NO_AI_MODELS must be True")
    check(features.voiceguard_enabled() is False, "VoiceGuard flag must be disabled")
    check(features.FEATURE_FLAGS["voiceguard"] is False, "voiceguard feature flag must be False")
    check(features.FEATURE_FLAGS["commander_model"] is False, "Commander model flag must be False")
    check(citizen_copy.NO_AI_MODELS is True, "app copy must declare no AI models")
    check(citizen_copy.VOICEGUARD_ENABLED is False, "app copy must freeze VoiceGuard")
    check(VOICEGUARD_ENABLED is False, "Citizen API VoiceGuard flag must be disabled")
    check(voiceguard_interface.VOICEGUARD_INTERFACE_CARD["enabled"] is False,
          "VoiceGuard interface card must be disabled")
    check(voiceguard_interface.VOICEGUARD_INTERFACE_CARD["status"] == "not integrated yet",
          "VoiceGuard interface status must be honest")
    card = voiceguard_interface.VOICEGUARD.status()
    check(card["model_invoked"] is False, "VoiceGuard status must report no model invocation")

    # One service and one physical PWA shell.
    build_apps = _unique_physical([
        *[p for p in (ROOT / "apps/citizen").rglob("api.py")],
        *[p for p in (ROOT / "raksha-code/citizen").rglob("api.py")],
        *[p for p in (ROOT / "raksha-code/apps/citizen").rglob("api.py")],
    ])
    # Every path above is a symlink/alias of the same editable service.
    check(len(build_apps) == 1, f"expected one physical Citizen service, got {sorted(map(str, build_apps))}")
    htmls = _unique_physical(list((ROOT / "apps/citizen").rglob("index.html")) +
                             list(FROZEN_APP.rglob("index.html")))
    manifests = _unique_physical(list((ROOT / "apps/citizen").rglob("manifest.json")) +
                                 list(FROZEN_APP.rglob("manifest.json")))
    check(len(htmls) == 1, f"expected one physical PWA index.html, got {sorted(map(str, htmls))}")
    check(len(manifests) == 1, f"expected one physical PWA manifest.json, got {sorted(map(str, manifests))}")
    check(callable(build_app), "Citizen service build_app missing")

    # Shared renderer owns logic, app owns sentences; no package-to-app import.
    shared_i18n = ROOT / "packages/contracts/i18n.py"
    shared_tree = ast.parse(_text(shared_i18n))
    shared_imports = list(_import_names(shared_tree))
    check(all(not name.startswith(("apps", "citizen", "voiceguard", "maya")) for name in shared_imports),
          f"shared i18n contract imports app/model code: {shared_imports}")
    check("class CitizenRenderer" in _text(shared_i18n), "shared CitizenRenderer missing")
    check("CITIZEN_COPY" in _text(ACTIVE / "copy.py"), "app-owned copy catalogue missing")
    check("from packages.contracts.i18n import" in _text(ACTIVE / "copy.py"),
          "app copy does not use shared renderer contract")
    check(CONTRACT_VERSION == "raksha-citizen-i18n-v1", "unexpected copy contract version")
    check(isinstance(citizen_copy.renderer, CitizenRenderer), "app copy renderer is not shared")

    # Active code must not import frozen VoiceGuard/model roots or call models.
    forbidden_import_prefixes = (
        "citizen.voiceguard", "voiceguard", "maya", "spine.slm_client",
        "spine.orchestrator", "ollama", "transformers", "torch", "tensorflow",
    )
    forbidden_calls = {"score_voice", "MayaModel", "SLMClient", "complete_json",
                       "probability_from_row", "predict", "generate"}
    for path in _py_files(ACTIVE):
        if path == ADAPTER:
            continue  # the single read-only future seam, not the active path
        tree = ast.parse(_text(path), filename=str(path))
        for name in _import_names(tree):
            if any(name == root or name.startswith(root + ".") for root in forbidden_import_prefixes):
                failures.append(f"forbidden model/frozen import in {path.relative_to(ROOT)}: {name}")
            if name.startswith(".legacy_voiceguard") or name == "apps.citizen.legacy_voiceguard":
                failures.append(f"active Citizen code imports frozen adapter in {path.relative_to(ROOT)}: {name}")
        for name in _call_names(tree):
            if name in forbidden_calls:
                failures.append(f"model call in {path.relative_to(ROOT)}: {name}")
    check(ADAPTER.exists(), "future Phase 11 read-only adapter missing")
    check("from citizen.voiceguard" in _text(ADAPTER),
          "read-only adapter no longer points at the frozen seam")

    # Risk engine still delegates sentences to the copy module, not to frozen i18n.
    engine = _text(ACTIVE / "risk/engine.py")
    fusion = _text(ACTIVE / "risk/fusion.py")
    for marker in ("i18n.render_band(", "i18n.render_advisory(",
                   "i18n.render_band_reason(", "i18n.render_reason("):
        check(marker in engine, f"risk engine stopped delegating copy: {marker}")
    check("legacy_voiceguard" not in engine, "risk engine imports frozen VoiceGuard adapter")
    check("legacy_voiceguard" not in fusion, "fusion core imports frozen VoiceGuard adapter")
    for banned in ("_BAND_COPY", "Not enough information to judge",
                   "This looks like a scam attempt", "Judgement-based weighting"):
        check(banned not in engine, f"citizen sentences crept back into risk engine: {banned}")

    # Runtime-only honest shell; frozen files are not edited.
    html = phase4_shell.inject_index_html(APP_DIR)
    manifest = phase4_shell.honest_manifest(APP_DIR)
    js = phase4_shell.PHASE4_SHELL_JS
    check("not integrated yet" in html, "runtime shell does not say not integrated yet")
    check("not integrated yet" in js, "runtime overlay JS does not say not integrated yet")
    check("src=\"phase4.js\"" in html, "runtime shell overlay script missing")
    check("/_citizen/phase4.js" not in html, "runtime shell still uses absolute script path")
    check("not integrated yet" in manifest["description"], "manifest does not say voice is not integrated")
    check("voice-clone" not in manifest["description"].lower(), "manifest still makes a voice-clone claim")
    check("clone detection" not in manifest["description"].lower(), "manifest still makes a clone-detection claim")
    check("AI model" not in manifest["description"], "manifest mentions an AI model")
    check("fetch(" not in js and "score_voice" not in js, "overlay JS tries to call a model or network")
    check("window.RakshaPhase4VoiceStatus" in js, "overlay JS status object missing")
    check("status: \"not integrated yet\"" in js, "overlay JS status missing")

    # App-owned text must not add a clone-detection claim or SAFE reassurance.
    active_text = "\n".join(_text(p) for p in [
        *[p for p in _py_files(ACTIVE) if p != ADAPTER],
        ACTIVE / "README.md",
    ])
    check("clone detection" not in active_text.lower(), "active Citizen text claims clone detection")
    check("voice-clone" not in active_text.lower(), "active Citizen text claims voice-clone detection")
    copy_text = json.dumps(citizen_copy.CITIZEN_COPY, ensure_ascii=False)
    check('"SAFE"' not in copy_text, "citizen copy catalogue introduces a SAFE verdict key")
    check("safe verdict" not in copy_text.lower(), "citizen copy catalogue mentions a SAFE verdict")
    check("SAFE" not in citizen_copy.CITIZEN_COPY["band_copy"], "risk copy includes a SAFE band")
    check("SAFE" not in citizen_copy.CITIZEN_COPY["message_verdict"], "message copy includes a SAFE verdict")
    check("SAFE" not in citizen_copy.CITIZEN_COPY.get("verdicts", {}), "voice copy includes a SAFE verdict")
    check('"SAFE"' not in phase4_shell.PHASE4_SHELL_JS, "runtime shell introduces a SAFE verdict")
    check("1930" in active_text, "1930 helpline copy missing")

    # Invariants and docs.
    cap = features.capability_card()
    inv = cap["invariants"]
    check(all(inv[k] for k in ("no_raw_score_to_citizen", "no_safe_verdict",
                               "no_pii_leaves_phone", "signature_required",
                               "governor_required")), "Phase 4 invariant weakened")
    for rel in ("raksha/PHASE4_CITIZEN_CONSOLIDATION.md",
                "raksha/adr/ADR-012-citizen-consolidation.md",
                "apps/citizen/features.py", "apps/citizen/copy.py",
                "apps/citizen/retention.py", "apps/citizen/voiceguard_interface.py",
                "packages/contracts/i18n.py", "tools/check_phase4_citizen.py",
                "tools/run_phase4_pytest.py", "tools/phase4_no_ai_plugin.py",
                "tools/run_phase4_node_tests.py"):
        check((ROOT / rel).is_file(), f"missing Phase 4 deliverable: {rel}")

    frozen = subprocess.run([sys.executable, str(ROOT / "tools/check_frozen_assets.py")],
                            cwd=ROOT, capture_output=True, text=True)
    check(frozen.returncode == 0, f"frozen assets changed: {frozen.stdout}{frozen.stderr}")

    # Prove import of the active service in a clean process never loads a model.
    probe = subprocess.run([
        sys.executable, "-c",
        "import sys; from pathlib import Path; r=Path.cwd(); "
        "sys.path[:0]=[str(r),str(r/'raksha-code')]; import apps.citizen.api; "
        "assert not any(m.startswith('citizen.voiceguard') or m.startswith('spine.slm_client') "
        "for m in sys.modules); print('ok')",
    ], cwd=ROOT, capture_output=True, text=True,
        env={**dict(__import__('os').environ), "OLLAMA_HOST": "http://127.0.0.1:9",
             "EIGENSHIELD_MODEL": "disabled"})
    check(probe.returncode == 0 and "ok" in probe.stdout,
          f"active service import probe failed: {probe.stdout}{probe.stderr}")

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 4 Citizen consolidation checker")
    parser.add_argument("--json", action="store_true", help="print failures as JSON")
    args = parser.parse_args(argv)
    failures = run_checks()
    if failures:
        if args.json:
            print(json.dumps({"ok": False, "failures": failures}, indent=2))
        else:
            print("PHASE 4 CITIZEN CHECK FAILED")
            for failure in failures:
                print("  -", failure)
        return 2
    print("OK: Phase 4 Citizen consolidation pinned; no AI model invoked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
