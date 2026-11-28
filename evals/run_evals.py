#!/usr/bin/env python3
"""The one active RAKSHA eval runner.

    python -m evals.run_evals           # regenerate corpus, results, EVALS.md, ledger
    python -m evals.run_evals --check  # drift check + capability exit gate

The runner measures Citizen, completed deterministic Infra, MessageGuard,
organs, governance, VIGIL local artifacts and one sandbox replay. It loads the committed
VIGIL TorchScript model for a status check, never calls a Commander/SLM
endpoint or live executor, and keeps real-world privacy efficacy UNMEASURED.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.contracts.envelope import sign_event  # noqa: E402  (compatibility export)

from evals import claims, corpus as corpus_mod, gen_evals_md, replay as replay_mod  # noqa: E402
from evals.sections import (  # noqa: E402
    citizen_section, governance_section, infra_section, messageguard_section,
    organ_section, vigil_section,
)

CORPUS_PATH = ROOT / "evals" / "corpus.json"
RESULTS_PATH = ROOT / "evals" / "results.json"
LEDGER_PATH = ROOT / "evals" / "claims_ledger.json"
SOURCES_PATH = ROOT / "evals" / "claims_sources.json"
EVALS_PATH = ROOT / "EVALS.md"
POINTER_PATH = ROOT / "raksha" / "MESSAGEGUARD_EVALS.md"
LEGACY_RESULTS_PATH = ROOT / "raksha-code" / "evals" / "messageguard" / "results.json"
CONTRACT = "raksha-active-evals-v2"


def compute_results() -> dict[str, Any]:
    corpus = corpus_mod.build_corpus()
    sections = {
        "citizen": citizen_section(),
        "infra": infra_section(),
        "messageguard": messageguard_section(),
        "organs": organ_section(),
        "governance": governance_section(),
        "replay": replay_mod.replay(corpus),
        "vigil": vigil_section(),
    }
    return {
        "contract": CONTRACT,
        "generated_by": "evals/run_evals.py",
        "measurement_policy": {
            "allowed_conditions": list(claims.ALLOWED_CONDITIONS),
            "real_world": "UNMEASURED",
            "privacy_efficacy": "UNMEASURED",
            "model_backed": True,
            "vigil_integrated": True,
            "executor_mode": "dry-run only",
            "commander_mode": "disabled",
        },
        "capability_count": len(sections),
        "conditions": corpus["conditions"],
        "source_files": [
            "evals/corpus.py", "evals/replay.py", "evals/sections.py",
            "evals/messageguard.py", "apps/citizen/api.py", "apps/citizen/features.py",
            "packages/vigil/main.py", "packages/vigil/config.py", "packages/vigil/model_manifest.json",
            "packages/vigil/privacynet_history.json",
            "apps/infra/features.py", "apps/infra/backend/app.py",
            "apps/infra/console/__init__.py", "apps/infra/console/console.js",
            "apps/infra/console/hospital.html", "apps/infra/console/hospital.js",
            "apps/infra/demo/__init__.py", "apps/infra/demo/hospital.py",
            "apps/infra/demo/hospital_topology.json",
            "apps/infra/BOOT_MANIFEST.json", "apps/infra/detectors/registry.py",
            "packages/governance/safety.py", "packages/spine/runtime.py",
        ],
        "sections": sections,
    }


def assert_sections(results: dict[str, Any]) -> None:
    sections = results["sections"]
    for name, section in sections.items():
        if section.get("status") != "ok":
            raise RuntimeError(f"capability {name} did not pass: {section.get('status')}")
        condition = str(section.get("condition") or "")
        if not any(label in condition for label in claims.ALLOWED_CONDITIONS):
            raise RuntimeError(f"capability {name} lacks an allowed condition: {condition}")
    infra = sections["infra"]
    if (infra["executor_mode"] != "dry-run"
            or infra["commander_enabled"] is not False
            or infra["model_backed"] is not False
            or infra["deterministic"] is not True
            or infra["console_read_only"] is not True
            or infra["admin_override_status_code"] != 403
            or infra["write_query_rejected_status_code"] != 401):
        raise RuntimeError("completed Infra lost its deterministic read-only contract")
    if (infra["hospital_demo_attack_steps"] < 8
            or infra["hospital_demo_step_status_codes_ok"] != infra["hospital_demo_attack_steps"]
            or infra["hospital_demo_synthetic_organization"] is not True
            or infra["hospital_demo_campaign_fused"] is not True
            or infra["hospital_demo_findings"] < 6
            or infra["hospital_demo_quarantine_count"] < 3
            or infra["hospital_demo_decision_count"] < 1
            or infra["hospital_demo_ledger_valid"] is not True
            or infra["hospital_demo_live_runtime_unchanged"] is not True
            or infra["hospital_demo_executor_mode"] != "dry-run"
            or infra["hospital_demo_commander_enabled"] is not False
            or infra["hospital_demo_real_action_count"] != 0):
        raise RuntimeError("functional fake-hospital demo lost its isolated dry-run contract")
    replay = sections["replay"]
    if replay["executor_real_action_count"] != 0 or not replay["ledger_valid"]:
        raise RuntimeError("replay did not stay dry-run and ledger-verified")
    if replay["commander_model_invoked"] or replay["deterministic"] is not True:
        raise RuntimeError("replay invoked Commander inference or lost deterministic Infra")
    vigil = sections["vigil"]
    if vigil["model_status"]["is_neural_active"] is not True:
        raise RuntimeError("active VIGIL neural weights are not loaded")
    if vigil["privacy_efficacy"] != "UNMEASURED":
        raise RuntimeError("VIGIL privacy efficacy must remain UNMEASURED")
    policy = results["measurement_policy"]
    if policy["real_world"] != "UNMEASURED" or policy["privacy_efficacy"] != "UNMEASURED":
        raise RuntimeError("real-world and privacy claims must remain UNMEASURED")
    if policy["model_backed"] is not True or policy["vigil_integrated"] is not True:
        raise RuntimeError("active model-backed VIGIL status is missing")


def _dump(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, indent=2) + "\n"


def expected_files(results: dict[str, Any], corpus: dict[str, Any],
                   sources: dict[str, Any]) -> dict[pathlib.Path, str]:
    return {
        CORPUS_PATH: corpus_mod.canonical_dump(corpus),
        RESULTS_PATH: _dump(results),
        LEDGER_PATH: _dump(claims.build_ledger(results, sources)),
        EVALS_PATH: gen_evals_md.render(results),
        POINTER_PATH: gen_evals_md.render_pointer(results),
        LEGACY_RESULTS_PATH: _dump(results["sections"]["messageguard"]),
    }


def write_outputs(results: dict[str, Any], corpus: dict[str, Any],
                  sources: dict[str, Any]) -> None:
    for path, content in expected_files(results, corpus, sources).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def check_outputs(results: dict[str, Any], corpus: dict[str, Any],
                  sources: dict[str, Any]) -> None:
    for path, expected in expected_files(results, corpus, sources).items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current != expected:
            raise RuntimeError(
                f"generated file is stale: {path.relative_to(ROOT).as_posix()}; "
                "rerun make eval-generate"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify corpus, results, EVALS.md, claims ledger and capability gates")
    args = parser.parse_args(argv)
    try:
        corpus = corpus_mod.build_corpus()
        results = compute_results()
        assert_sections(results)
        sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
        if not args.check:
            write_outputs(results, corpus, sources)
            print("wrote one corpus, one results file, one EVALS.md, one claims ledger")
            return 0
        check_outputs(results, corpus, sources)
        if corpus_mod.main(["--check"]) != 0:
            return 1
        if replay_mod.main(["--check"]) != 0:
            return 1
        if claims.main(["--check"]) != 0:
            return 1
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("OK: active run_evals --check green for Citizen, Infra, MessageGuard, organs, governance, replay and VIGIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
