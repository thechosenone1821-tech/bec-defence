#!/usr/bin/env python3
"""Phase 9/10 deterministic integration checker.

Proves one command surface, one eval/claims/drift story, two boot-manifested
apps, CI gates, canonical docs, provenance notes, a frozen phase board and an
explicit future VoiceGuard re-entry gate. It runs no AI model, model-dependent
test, live executor, real containment action or network service.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import (  # noqa: E402
    check_boot_manifest, check_claims_ledger, check_eval_drift,
    check_no_live_executor, check_no_secrets, verify_runtime_ledger,
)

CANONICAL = (
    "summary.md", "README.md", "docs/STATUS.md", "docs/README.md", "CHANGELOG.md",
    "EVALS.md", "raksha/PHASE910_UNIFIED_RELEASE.md", "Makefile",
    "requirements.txt", "tools/launch_apps.py", ".github/workflows/ci.yml",
    "evals/run_evals.py", "evals/corpus.py", "evals/replay.py",
    "evals/results.json", "evals/claims_ledger.json", "evals/claims_sources.json",
    "apps/citizen/BOOT_MANIFEST.json", "apps/infra/BOOT_MANIFEST.json",
    "archive/provenance/INTEGRATED.md",
)
RETIRED_TOP_LEVEL = (
    "raksha-enterprise", "raksha-governance", "raksha-messageguard",
    "random project that ew need to integrate",
)
CI_GATES = (
    "run_phase4_pytest", "run_phase4_node_tests", "check_eval_drift",
    "verify_runtime_ledger", "check_boot_manifest", "check_no_secrets",
    "check_no_live_executor", "check_claims_ledger",
)
MAKE_TARGETS = ("install:", "test:", "eval:", "run:", "ci-checks:", "ci:")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main(argv: list[str] | None = None) -> int:
    try:
        for rel in CANONICAL:
            check((ROOT / rel).is_file(), f"missing canonical Phase 9/10 deliverable: {rel}")
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
                  f"legacy model bus reintroduced in {path}")

        for rel in ("evals/corpus.py", "evals/replay.py", "evals/run_evals.py"):
            source = (ROOT / rel).read_text(encoding="utf-8")
            check("run_maya" not in source, f"frozen MAYA eval leaked into {rel}")
        corpus = json.loads((ROOT / "evals" / "corpus.json").read_text(encoding="utf-8"))
        check(corpus["replay"]["voiceguard_excluded"] is True,
              "VoiceGuard evals are not excluded from the unified corpus")
        api_doc = (ROOT / "apps" / "citizen" / "api.py").read_text(encoding="utf-8")
        check("492 hand-authored fixtures" not in api_doc,
              "Citizen API still cites the stale 492-fixture headline")
        check("538 hand-authored" in api_doc and "real-world recall and FPR UNMEASURED" in api_doc,
              "Citizen API lacks conditioned canonical MessageGuard scope")
        fixture_readme = json.loads((ROOT / "apps" / "citizen" / "fixtures" / "message_fixtures.json").read_text(encoding="utf-8"))
        check("492 fixtures" not in fixture_readme.get("_readme", ""),
              "legacy smoke-corpus readme still publishes the stale 492-fixture count")
        sources = json.loads((ROOT / "evals" / "claims_sources.json").read_text(encoding="utf-8"))
        check(any("real-world UNMEASURED" in row["condition"] for row in sources["rows"]),
              "claims source rows do not condition real-world claims as UNMEASURED")
        results = json.loads((ROOT / "evals" / "results.json").read_text(encoding="utf-8"))
        check(results["voiceguard"]["included_in_runner"] is False,
              "VoiceGuard evals are included in the unified runner")
        check(results["voiceguard"]["future_phase"] == "Eleven",
              "VoiceGuard re-entry is not future Phase Eleven")
        check(all(section["status"] == "ok" for section in results["sections"].values()),
              "a Phase 9 capability section did not pass")

        status = (ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8")
        check("FROZEN" in status and "VoiceGuard re-entry gate" in status,
              "status board is not frozen with a VoiceGuard re-entry gate")
        roadmap = (ROOT / "raksha" / "COMBINED_SYSTEM_ROADMAP.md").read_text(encoding="utf-8")
        check("FROZEN" in roadmap and "Phase Eleven" in roadmap,
              "combined roadmap is not frozen with a future Phase Eleven gate")
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

        archive = ROOT / "archive" / "provenance"
        for child in sorted(p for p in archive.iterdir() if p.is_dir()):
            check((child / "INTEGRATED.md").is_file(),
                  f"provenance tree lacks INTEGRATED.md: {child.name}")

        if check_eval_drift.main([]) != 0:
            return 1
        if check_claims_ledger.main([]) != 0:
            return 1
        if check_boot_manifest.main([]) != 0:
            return 1
        if check_no_secrets.main([]) != 0:
            return 1
        if check_no_live_executor.main([]) != 0:
            return 1
        if verify_runtime_ledger.main([]) != 0:
            return 1
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("OK: Phase 9-10 unified release; two apps, one eval/claims/drift path, frozen board")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
