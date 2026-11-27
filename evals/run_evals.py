#!/usr/bin/env python3
"""Phase 9 — the one deterministic eval runner.

    python -m evals.run_evals           # regenerate corpus, results, EVALS.md, ledger
    python -m evals.run_evals --check  # drift check + capability exit gate

The runner measures Citizen, MessageGuard, organs, governance and one end-to-end
sandbox replay. It never loads an AI model, Commander/SLM/Ollama endpoint, frozen
VoiceGuard/MAYA eval, live executor, legacy spine bus or network service. All
published numbers carry fixture / synthetic / sandbox / hand-authored /
real-world UNMEASURED conditions. VoiceGuard evals are deferred to Phase Eleven.
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

from packages.contracts.envelope import sign_event  # noqa: E402  (Phase 3 compatibility export)

from evals import claims, corpus as corpus_mod, gen_evals_md, replay as replay_mod  # noqa: E402
from evals.sections import (  # noqa: E402
    citizen_section, governance_section, messageguard_section, organ_section,
)

CORPUS_PATH = ROOT / "evals" / "corpus.json"
RESULTS_PATH = ROOT / "evals" / "results.json"
LEDGER_PATH = ROOT / "evals" / "claims_ledger.json"
SOURCES_PATH = ROOT / "evals" / "claims_sources.json"
EVALS_PATH = ROOT / "EVALS.md"
POINTER_PATH = ROOT / "raksha" / "MESSAGEGUARD_EVALS.md"
LEGACY_RESULTS_PATH = ROOT / "raksha-code" / "evals" / "messageguard" / "results.json"
CONTRACT = "raksha-unified-evals-v1"


def compute_results() -> dict[str, Any]:
    corpus = corpus_mod.build_corpus()
    sections = {
        "citizen": citizen_section(),
        "messageguard": messageguard_section(),
        "organs": organ_section(),
        "governance": governance_section(),
        "replay": replay_mod.replay(corpus),
    }
    return {
        "contract": CONTRACT,
        "generated_by": "evals/run_evals.py",
        "measurement_policy": {
            "allowed_conditions": list(claims.ALLOWED_CONDITIONS),
            "real_world": "UNMEASURED",
            "voiceguard_evals_included": False,
            "executor_mode": "dry-run only",
            "commander_mode": "disabled",
        },
        "capability_count": len(sections),
        "conditions": corpus["conditions"],
        "source_files": [
            "evals/corpus.py", "evals/replay.py", "evals/sections.py",
            "evals/messageguard.py", "apps/citizen/api.py",
            "apps/infra/detectors/registry.py", "packages/governance/safety.py",
            "packages/spine/runtime.py",
        ],
        "sections": sections,
        "voiceguard": {
            "contract_status": "RESERVED_NOT_INTEGRATED",
            "included_in_runner": False,
            "future_phase": "Eleven",
            "reentry_gate": (
                "Open only when the voice build is ready: frozen assets unchanged, "
                "consent and retention policy, signed envelope validation, honest "
                "synthetic-only measurement labels, deterministic no-AI tests, and "
                "Governor/append-only-ledger compatibility."
            ),
            "frozen_assets_unchanged": True,
        },
    }


def assert_sections(results: dict[str, Any]) -> None:
    sections = results["sections"]
    for name, section in sections.items():
        if section.get("status") != "ok":
            raise RuntimeError(f"capability {name} did not pass: {section.get('status')}")
        condition = str(section.get("condition") or "")
        if not any(label in condition for label in claims.ALLOWED_CONDITIONS):
            raise RuntimeError(f"capability {name} lacks an allowed condition: {condition}")
    replay = sections["replay"]
    if replay["executor_real_action_count"] != 0 or not replay["ledger_valid"]:
        raise RuntimeError("replay did not stay dry-run and ledger-verified")
    if replay["commander_model_invoked"] or replay["voiceguard_included"]:
        raise RuntimeError("replay invoked a model or included VoiceGuard evals")
    if results["voiceguard"]["included_in_runner"] is not False:
        raise RuntimeError("VoiceGuard evals must stay out of the Phase 9 runner")
    if results["measurement_policy"]["real_world"] != "UNMEASURED":
        raise RuntimeError("real-world claims must remain UNMEASURED")


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
                f"generated file is stale: {path.relative_to(ROOT).as_posix()}; rerun make eval"
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
    print("OK: run_evals --check green for Citizen, MessageGuard, organs, governance and replay")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
