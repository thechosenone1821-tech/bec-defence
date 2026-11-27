#!/usr/bin/env python3
"""Phase 3 contract checker.

Verifies that the shared contracts are the single source for canonical JSON,
reason/band tables, config pins, auth scopes, sanitizer/entity rules, backend
route mapping, and the reserved VoiceGuard slot. It also pins the no-bypass
import rule for app code.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from packages.contracts import (  # noqa: E402
    AUTH_SCOPES, BACKEND_CONTRACT_VERSION, BACKEND_ROUTES, BOOT_MANIFEST_PATHS,
    CANONICAL_JSON_RULE, CONTRACT_VERSION, FORBIDDEN_APP_BYPASS_ROOTS,
    LEGACY_BANDS, PROFILE_PATHS, REASON_CATALOGUE, VOICEGUARD_CONTRACT_SLOT,
    canonical_bytes, canonical_json, check_pinned_configs, config_pins,
    validate_routes, write_config_pins,
)
from packages.contracts.bands import band  # noqa: E402
from packages.contracts.entities import ENTITY_PATH, ENTITY_PREFIX  # noqa: E402
from packages.contracts.voiceguard import VOICEGUARD_SLOT_STATUS  # noqa: E402


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _import_names(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                yield node.module


def _load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve annotations via sys.modules
    spec.loader.exec_module(module)
    return module


def _frozen_msg_reason_family() -> dict[str, str]:
    """Read the frozen MSG map by AST, without importing VoiceGuard/model code."""
    source = _text("raksha-code/citizen/voiceguard/i18n.py")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "MSG_REASON_FAMILY" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("frozen MSG_REASON_FAMILY assignment missing")


def run_checks() -> list[str]:
    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    # 1. One canonical JSON rule, used by shipped and historical trees.
    check(canonical_json({"b": 1, "a": {"d": 2, "c": [1, 2]}}) == '{"a":{"c":[1,2],"d":2},"b":1}', "canonical JSON rule changed")
    import spine.telemetry_mac as telemetry_mac
    import spine.ledger as spine_ledger
    import sentinel.shields.base_organ as base_organ
    check(telemetry_mac.canonical_bytes is canonical_bytes, "spine telemetry MAC does not use shared canonical_bytes")
    check(base_organ.canonical_bytes is canonical_bytes, "BaseOrgan does not use shared canonical_bytes")
    check(spine_ledger.canonical_hash.__module__ == "packages.contracts.canonical", "spine ledger does not use shared canonical_hash")
    enterprise_events = _load_module("phase3_enterprise_events", "archive/provenance/raksha-enterprise/raksha-enterprise/raksha/events.py")
    governance_canonical = _load_module("phase3_governance_canonical", "archive/provenance/raksha-governance/raksha-governance/raksha/canonical.py")
    check(enterprise_events.canonical({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1}), "enterprise I1 canonical() diverged")
    check(governance_canonical.canonical_bytes({"b": 1, "a": 2}) == canonical_bytes({"a": 2, "b": 1}), "governance canonical_bytes() diverged")

    # 2. One reason catalogue, one band table, one entity rule set.
    import apps.citizen.messageguard.reasons as app_reasons
    import apps.citizen.messageguard.bandmap as app_bandmap
    import apps.citizen.messageguard.scorer as app_scorer
    import spine.sanitizer as spine_sanitizer
    import spine.entity_graph as spine_entity_graph
    frozen_msg_reason_family = _frozen_msg_reason_family()
    check(app_reasons.REASON_CATALOGUE is REASON_CATALOGUE, "Citizen reasons.py is not a re-export of shared catalogue")
    check(app_bandmap.LEGACY_BANDS is LEGACY_BANDS, "Citizen bandmap.py is not a re-export of shared band map")
    check(app_scorer.band is band, "MessageGuard scorer does not use shared band()")
    check(all(code.startswith("MSG-") for code in REASON_CATALOGUE), "non MSG-* code in shared reason catalogue")
    check(frozen_msg_reason_family == {code: entry[0] for code, entry in REASON_CATALOGUE.items()}, "frozen i18n reason families drifted")
    check(spine_sanitizer._ENTITY_PREFIX is ENTITY_PREFIX, "sanitizer does not use shared entity prefixes")
    check(spine_entity_graph.ENTITY_PATH is ENTITY_PATH, "entity graph does not use shared entity path")

    # 3. Config pins, auth scopes and boot manifest.
    pins_report = check_pinned_configs()
    check(pins_report["ok"], f"config pins failed: {pins_report['mismatches']}")
    check(AUTH_SCOPES == ("telemetry:write", "read", "admin"), "auth scopes changed")
    check(BOOT_MANIFEST_PATHS == ("config/policy.yaml", "config/company_topology.json", "tool_schemas.json", "system_prompt.txt"), "boot manifest path list changed")
    import spine.boot_manifest as boot_manifest
    check(list(boot_manifest.DEFAULT_PATHS) == list(BOOT_MANIFEST_PATHS), "boot manifest does not use shared pinned paths")
    check("from packages.contracts.config import AUTH_SCOPES" in _text("archive/provenance/raksha-enterprise/raksha-enterprise/raksha/bus/auth.py"), "enterprise auth scopes not shared")
    check("from packages.ledger.cli import main as _shared_main" in _text("raksha-code/spine/ledger_cli.py"), "legacy ledger CLI does not delegate to shared CLI")

    # 4. One backend contract and one signed-envelope contract exposed by apps.
    check(BACKEND_CONTRACT_VERSION == "raksha-backend-v1", "backend contract version changed")
    check(CONTRACT_VERSION == "raksha-event-v1", "event contract version changed")
    canonical_names = {r.canonical for r in BACKEND_ROUTES}
    check({"health", "ingest", "state", "ledger_verify", "websocket"} <= canonical_names, "backend route catalogue incomplete")
    check(len(PROFILE_PATHS["spine-v2"]) >= 5 and len(PROFILE_PATHS["enterprise-i1"]) >= 6, "backend profiles lost routes")

    class _Route:
        def __init__(self, path: str): self.path = path
    class _App:
        def __init__(self, paths): self.routes = [_Route(p) for p in paths]
    check(validate_routes(_App(PROFILE_PATHS["spine-v2"]), "spine-v2")["ok"], "spine-v2 route validation failed on its own profile")
    check(not validate_routes(_App([]), "spine-v2")["ok"], "spine-v2 route validation accepted an empty app")
    check("from packages.contracts.envelope import (" in _text("apps/citizen/api.py"), "Citizen API does not use shared envelope contract")
    check("from packages.spine.contract import (" in _text("apps/infra/backend/app.py"), "Infra backend does not expose shared contract")

    # 5. No app bypass roots; no VoiceGuard logic in shared contracts.
    for path in sorted((ROOT / "apps").rglob("*.py")):
        for name in _import_names(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
            if any(name == root or name.startswith(root + ".") for root in FORBIDDEN_APP_BYPASS_ROOTS):
                failures.append(f"app bypass import in {path.relative_to(ROOT)}: {name}")
    for path in sorted((ROOT / "packages/contracts").rglob("*.py")):
        for name in _import_names(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
            top = name.split(".", 1)[0]
            if top in {"voiceguard", "maya"} or name.startswith("citizen.voiceguard"):
                failures.append(f"VoiceGuard logic import in shared contract {path.relative_to(ROOT)}: {name}")
    voiceguard_tree = ast.parse(_text("packages/contracts/voiceguard.py"))
    voiceguard_imports = [name for name in _import_names(voiceguard_tree)
                          if name.split(".", 1)[0] not in sys.stdlib_module_names]
    check(not voiceguard_imports, f"VoiceGuard slot imports implementation logic: {voiceguard_imports}")
    check(VOICEGUARD_CONTRACT_SLOT.status == VOICEGUARD_SLOT_STATUS == "RESERVED_NOT_INTEGRATED", "VoiceGuard slot status changed")

    # 6. Delegation markers in shipped compatibility seams.
    markers = {
        "raksha-code/spine/telemetry_mac.py": "from packages.contracts.canonical import (",
        "raksha-code/sentinel/shields/base_organ.py": "from packages.contracts.canonical import",
        "raksha-code/spine/ledger.py": "from packages.contracts.canonical import canonical_hash",
        "raksha-code/spine/sanitizer.py": "from packages.contracts.entities import (",
        "raksha-code/spine/entity_graph.py": "from packages.contracts.entities import ENTITY_PATH",
        "raksha-code/spine/boot_manifest.py": "from packages.contracts.config import BOOT_MANIFEST_PATHS",
        "archive/provenance/raksha-enterprise/raksha-enterprise/raksha/events.py": "from packages.contracts.canonical import canonical_json",
        "archive/provenance/raksha-governance/raksha-governance/raksha/canonical.py": "from packages.contracts.canonical import (",
        "apps/citizen/messageguard/reasons.py": "from packages.contracts.reasons import",
        "apps/citizen/messageguard/bandmap.py": "from packages.contracts.bands import",
        "apps/citizen/messageguard/scorer.py": "from packages.contracts.bands import",
    }
    for rel, marker in markers.items():
        check(marker in _text(rel), f"missing Phase 3 delegation marker in {rel}: {marker}")

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 3 shared contract checker")
    parser.add_argument("--write-pins", action="store_true", help="rewrite packages/contracts/config_pins.json")
    parser.add_argument("--json", action="store_true", help="print failures as JSON")
    args = parser.parse_args(argv)
    if args.write_pins:
        write_config_pins()
        print("OK: wrote packages/contracts/config_pins.json")
    failures = run_checks()
    if failures:
        if args.json:
            print(json.dumps({"ok": False, "failures": failures}, indent=2))
        else:
            print("PHASE 3 CONTRACT CHECK FAILED")
            for failure in failures:
                print("  -", failure)
        return 2
    print("OK: Phase 3 shared contracts pinned and consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
