#!/usr/bin/env python3
"""Active release integration checker.

Proves one command surface, one eval/claims/drift path, two boot-manifested
apps, active VIGIL weights, deterministic dry-run Infra, the retired-code
purge and the local-link surface. It performs no live containment action.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import (  # noqa: E402
    check_boot_manifest, check_claims_ledger, check_code_purge,
    check_eval_drift, check_local_links, check_no_live_executor,
    check_no_secrets, check_phase3_contracts, check_phase4_citizen,
    check_phase5_messageguard, check_phase678_integration,
    check_vigil_assets, verify_runtime_ledger,
)

CANONICAL = (
    "summary.md", "README.md", "docs/STATUS.md", "docs/README.md", "CHANGELOG.md",
    "EVALS.md", "raksha/PHASE910_UNIFIED_RELEASE.md", "Makefile",
    "requirements.txt", "tools/launch_apps.py", ".github/workflows/ci.yml",
    "evals/run_evals.py", "evals/corpus.py", "evals/replay.py",
    "evals/sections.py", "evals/results.json", "evals/claims_ledger.json",
    "evals/claims_sources.json", "apps/citizen/BOOT_MANIFEST.json",
    "apps/infra/BOOT_MANIFEST.json", "apps/infra/features.py",
    "apps/infra/backend/app.py", "apps/infra/console/console.js",
    "apps/infra/console/index.html", "apps/infra/console/hospital.html",
    "apps/infra/console/hospital.js", "apps/infra/demo/__init__.py",
    "apps/infra/demo/hospital.py", "apps/infra/demo/hospital_topology.json",
    "tools/run_infra_smoke.py", "tools/run_hospital_demo_smoke.py",
    "raksha-code/tests/infra_hospital_demo.test.js",
    "packages/vigil/main.py",
    "packages/vigil/model_manifest.json", "tools/check_code_purge.py",
    "tools/check_vigil_assets.py", "tools/run_vigil_tests.py",
    "tools/run_vigil_smoke.py", "archive/provenance/INTEGRATED.md",
)
RETIRED_TOP_LEVEL = (
    "raksha-enterprise", "raksha-governance", "raksha-messageguard",
    "random project that ew need to integrate",
)
CI_GATES = (
    "run_phase4_pytest", "run_phase4_node_tests", "run_infra_smoke",
    "run_hospital_demo_smoke", "run_vigil_tests",
    "run_vigil_smoke", "check_vigil_assets", "check_code_purge",
    "check_eval_drift", "verify_runtime_ledger", "check_boot_manifest",
    "check_no_secrets", "check_no_live_executor", "check_claims_ledger",
    "check_local_links",
)
MAKE_TARGETS = (
    "install:", "test:", "eval:", "eval-generate:", "run:",
    "infra-smoke:", "hospital-smoke:", "vigil-tests:", "vigil-smoke:",
    "links:", "ci-checks:", "ci:",
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main(argv: list[str] | None = None) -> int:
    try:
        for rel in CANONICAL:
            check((ROOT / rel).is_file(), f"missing canonical active deliverable: {rel}")
        for rel in RETIRED_TOP_LEVEL:
            check(not (ROOT / rel).exists(),
                  f"retired standalone project still outside provenance: {rel}")

        active_evals_docs = [p for p in ROOT.rglob("EVALS.md")
                             if "archive" not in p.relative_to(ROOT).parts]
        check(active_evals_docs == [ROOT / "EVALS.md"],
              f"more than one active EVALS.md: {active_evals_docs}")
        pointers = [p for p in ROOT.rglob("MESSAGEGUARD_EVALS.md")
                    if "archive" not in p.relative_to(ROOT).parts]
        check(pointers == [ROOT / "raksha" / "MESSAGEGUARD_EVALS.md"],
              f"unexpected active MessageGuard pointer set: {pointers}")

        runners = [p for p in ROOT.rglob("run_evals.py")
                   if "archive" not in p.relative_to(ROOT).parts
                   and ".venv" not in p.parts]
        allowed_wrappers = {
            ROOT / "evals" / "run_evals.py",
            ROOT / "raksha-code" / "evals" / "run_evals.py",
            ROOT / "raksha-code" / "evals" / "messageguard" / "run_evals.py",
        }
        check(set(runners) == allowed_wrappers,
              f"unexpected run_evals.py files outside provenance: {runners}")
        for path in runners:
            source = path.read_text(encoding="utf-8")
            if path != ROOT / "evals" / "run_evals.py":
                check("compatibility" in source.lower() or "wrapper" in source.lower(),
                      f"legacy runner is not a thin compatibility wrapper: {path}")
            check("from spine.bus import" not in source,
                  f"legacy live-action bus reintroduced in {path}")

        corpus = json.loads((ROOT / "evals" / "corpus.json").read_text(encoding="utf-8"))
        check(corpus["claim_policy"]["model_backed"] is True,
              "active corpus does not report a model-backed build")
        check(corpus["claim_policy"]["vigil_integrated"] is True,
              "active corpus does not report VIGIL integration")
        check(corpus["replay"]["deterministic_infra"] is True,
              "replay corpus lost deterministic Infra status")
        check(corpus["vigil"]["local_metrics_only"] is True,
              "VIGIL corpus lost its local-metrics-only condition")

        api_doc = (ROOT / "apps" / "citizen" / "api.py").read_text(encoding="utf-8")
        check("492 hand-authored fixtures" not in api_doc,
              "Citizen API still cites a stale fixture headline")
        check("538 hand-authored" in api_doc and "real-world recall and FPR UNMEASURED" in api_doc,
              "Citizen API lacks conditioned canonical MessageGuard scope")
        fixture_readme = json.loads((ROOT / "apps" / "citizen" / "fixtures" / "message_fixtures.json").read_text(encoding="utf-8"))
        check("492 fixtures" not in fixture_readme.get("_readme", ""),
              "legacy smoke-corpus readme still publishes a stale fixture count")

        sources = json.loads((ROOT / "evals" / "claims_sources.json").read_text(encoding="utf-8"))
        check(any("real-world UNMEASURED" in row["condition"] for row in sources["rows"]),
              "claims source rows do not condition real-world claims as UNMEASURED")
        results = json.loads((ROOT / "evals" / "results.json").read_text(encoding="utf-8"))
        check(results["measurement_policy"]["model_backed"] is True,
              "results do not report active VIGIL")
        check(results["measurement_policy"]["real_world"] == "UNMEASURED",
              "results do not condition real-world claims")
        check(results["measurement_policy"]["privacy_efficacy"] == "UNMEASURED",
              "results do not condition privacy efficacy")
        check(all(section["status"] == "ok" for section in results["sections"].values()),
              "an active capability section did not pass")
        check(results["sections"]["vigil"]["model_status"]["is_neural_active"] is True,
              "committed VIGIL results do not report active neural weights")
        check(results["sections"]["replay"]["deterministic"] is True,
              "committed replay is not deterministic")
        infra_section = results["sections"]["infra"]
        check(infra_section["status"] == "ok",
              "committed Infra section did not pass")
        check(infra_section["executor_mode"] == "dry-run",
              "committed Infra section is not dry-run")
        check(infra_section["commander_enabled"] is False,
              "committed Infra section enabled Commander")
        check(infra_section["console_read_only"] is True,
              "committed Infra section is not read-only")
        check(infra_section["hospital_demo_synthetic_organization"] is True,
              "committed Infra section lost the synthetic fake-hospital demo")
        check(infra_section["hospital_demo_attack_steps"] >= 8,
              "committed Infra section lost the functional attack series")
        check(infra_section["hospital_demo_ledger_valid"] is True,
              "committed fake-hospital demo ledger did not verify")
        check(infra_section["hospital_demo_live_runtime_unchanged"] is True,
              "committed fake-hospital demo is not isolated")
        check(infra_section["hospital_demo_real_action_count"] == 0,
              "committed fake-hospital demo reported a real action")

        status = (ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8")
        check("VIGIL active" in status and "UNMEASURED" in status,
              "status page is not honest about the active model")
        check("status, capability and detector cards" in status,
              "status page does not describe completed Infra")
        check("functional fake-hospital attack exercise" in status,
              "status page does not describe the fake-hospital demo")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        check("VIGIL active" in changelog and "UNMEASURED" in changelog,
              "changelog is not honest about the active model")
        check("status, capability and detector cards" in changelog,
              "changelog does not describe completed Infra")
        check("fake-hospital attack exercise" in changelog,
              "changelog does not describe the fake-hospital demo")
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        for gate in CI_GATES:
            check(gate in ci, f"CI workflow misses gate: {gate}")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        for target in MAKE_TARGETS:
            check(target in makefile, f"Makefile misses target: {target}")
        launcher = (ROOT / "tools" / "launch_apps.py").read_text(encoding="utf-8")
        check("exactly two" in launcher and "apps.infra" in launcher and "apps.citizen" in launcher,
              "process launcher does not describe exactly two apps")
        check("third app" in launcher, "launcher does not forbid a third app")
        check("RAKSHA_INFRA_PORT" in launcher and "RAKSHA_CITIZEN_PORT" in launcher,
              "launcher does not support fresh preview port overrides")

        archive = ROOT / "archive" / "provenance"
        for child in sorted(p for p in archive.iterdir() if p.is_dir()):
            check((child / "INTEGRATED.md").is_file(),
                  f"provenance tree lacks INTEGRATED.md: {child.name}")

        gates = (
            check_phase3_contracts.main([]),
            check_phase4_citizen.main([]),
            check_phase5_messageguard.main([]),
            check_phase678_integration.main([]),
            check_vigil_assets.main([]),
            check_code_purge.main([]),
            check_eval_drift.main([]),
            check_claims_ledger.main([]),
            check_boot_manifest.main([]),
            check_no_secrets.main([]),
            check_no_live_executor.main([]),
            verify_runtime_ledger.main([]),
            check_local_links.main([]),
        )
        if any(code != 0 for code in gates):
            return 1
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("OK: active release; two apps, VIGIL neural runtime, completed deterministic Infra, one eval/claims path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
