#!/usr/bin/env python3
"""The one active RAKSHA corpus generator.

Replay and eval fixtures are produced from committed hand-authored rows, the one
Infra detector registry and sandbox topology. VIGIL local metrics are read from
the committed model manifest and training history; real-world privacy efficacy
is never inferred from those artifacts.
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

from apps.infra.detectors.registry import ORGAN_FIXTURES, ORGAN_SPECS  # noqa: E402
from packages.contracts.config import DEFAULT_TOPOLOGY  # noqa: E402

CORPUS_PATH = ROOT / "evals" / "corpus.json"
MESSAGEGUARD_FIXTURES = ROOT / "raksha-code" / "citizen" / "fixtures" / "messageguard"
CONDITIONS = {
    "messageguard": "hand-authored / in-distribution; real-world UNMEASURED",
    "citizen": "fixture / sandbox",
    "organs": "synthetic / sandbox",
    "governance": "sandbox",
    "replay": "sandbox",
    "vigil": "local training / fixture; real-world UNMEASURED",
}
REPLAY_CASE = "CASE-P9-REPLAY"
REPLAY_CAMPAIGN = "C-P9-REPLAY"


def _raw(event_id: str, organ: str, payload: dict[str, Any], *, leg: str = "infra",
         severity: int = 4, entity: str = "HOST_EVAL_07") -> dict[str, Any]:
    return {
        "event_id": event_id,
        "ts": "2026-11-26T09:00:00Z",
        "organ": organ,
        "campaign_id": REPLAY_CAMPAIGN,
        "case_id": REPLAY_CASE,
        "leg": leg,
        "severity": severity,
        "entity": entity,
        "summary": f"active replay fixture {event_id}",
        "payload": dict(payload),
    }


def _replay_steps() -> list[dict[str, Any]]:
    """One sandbox campaign derived from the one active Infra organ registry."""
    steps: list[dict[str, Any]] = []
    for index, spec in enumerate(ORGAN_SPECS, start=1):
        leg = "citizen" if index == 1 else "infra"
        entity = "N-VICTIM-PHONE" if leg == "citizen" else f"HOST_EVAL_{index:02d}"
        steps.append({
            "id": f"R{index:02d}",
            "stage": "initial_access" if index == 1 else ("impact" if index > 5 else "execution"),
            "kind": "signed_finding",
            "expected": "finding",
            "raw": _raw(f"EV-P9-{index:02d}", spec.name,
                        ORGAN_FIXTURES[spec.name]["firing"], leg=leg,
                        entity=entity),
        })
    steps.append({
        "id": "R-BENIGN", "stage": "defense_evasion", "kind": "signed_no_detection",
        "expected": "no_detection",
        "raw": _raw("EV-P9-BENIGN", "bragg_fft_firewall",
                    ORGAN_FIXTURES["bragg_fft_firewall"]["silent"], severity=2,
                    entity="HOST_EVAL_BENIGN"),
    })
    steps.append({
        "id": "R-MISSING", "stage": "defense_evasion", "kind": "signed_no_detection",
        "expected": "no_detection",
        "raw": _raw("EV-P9-MISSING", "page_curve_trap",
                    ORGAN_FIXTURES["page_curve_trap"]["missing"], severity=2,
                    entity="HOST_EVAL_MISSING"),
    })
    for event_id, kind in (
        ("EV-P9-UNSIGNED", "unsigned"),
        ("EV-P9-TAMPERED", "tampered"),
        ("EV-P9-FORGED", "forged"),
        ("EV-P9-UNKNOWN", "unknown_organ"),
    ):
        organ = "unknown_organ" if kind == "unknown_organ" else "page_curve_trap"
        steps.append({
            "id": f"R-{kind.upper()}", "stage": "defense_evasion", "kind": kind,
            "expected": "quarantined",
            "raw": _raw(event_id, organ,
                        ORGAN_FIXTURES["page_curve_trap"]["firing"], severity=4),
        })
    return steps


def build_corpus() -> dict[str, Any]:
    fixture_files = sorted(p.name for p in MESSAGEGUARD_FIXTURES.glob("*.jsonl"))
    organ_cases = {
        spec.name: {
            bundle: dict(ORGAN_FIXTURES[spec.name][bundle])
            for bundle in ("firing", "silent", "missing")
        }
        for spec in ORGAN_SPECS
    }
    return {
        "contract": "raksha-unified-corpus-v2",
        "generated_by": "evals/corpus.py",
        "conditions": CONDITIONS,
        "claim_policy": {
            "real_world": "UNMEASURED",
            "model_backed": True,
            "vigil_integrated": True,
            "real_world_privacy_efficacy": "UNMEASURED",
            "allowed_conditions": ["fixture", "synthetic", "sandbox", "local training",
                                   "hand-authored", "real-world UNMEASURED"],
        },
        "messageguard": {
            "condition": CONDITIONS["messageguard"],
            "source": "raksha-code/citizen/fixtures/messageguard/*.jsonl",
            "fixture_files": fixture_files,
            "scorer": "apps/citizen/messageguard",
        },
        "citizen": {
            "condition": CONDITIONS["citizen"],
            "source": "apps/citizen/api.py",
            "cases": ["health", "features", "manifest", "root_redirect",
                      "vigil_dashboard", "vigil_overview", "vigil_static"],
            "model_backed": True,
            "vigil_integrated": True,
        },
        "organs": {
            "condition": CONDITIONS["organs"],
            "source": "apps/infra/detectors/registry.py",
            "registry_count": 1,
            "organ_cases": organ_cases,
        },
        "governance": {
            "condition": CONDITIONS["governance"],
            "source": "packages/governance/safety.py",
            "topology": DEFAULT_TOPOLOGY.resolve().relative_to(ROOT).as_posix(),
            "blast_cap": 3,
            "executor": "DryRunExecutor-v1",
            "crown_cuts": "impossible_by_construction",
        },
        "replay": {
            "condition": CONDITIONS["replay"],
            "source": "evals/replay.py",
            "campaign_id": REPLAY_CAMPAIGN,
            "case_id": REPLAY_CASE,
            "steps": _replay_steps(),
            "deterministic_infra": True,
            "executor_mode": "dry-run only",
            "live_executor_called": False,
        },
        "vigil": {
            "condition": CONDITIONS["vigil"],
            "sources": [
                "packages/vigil/model_manifest.json",
                "packages/vigil/privacynet_history.json",
                "packages/vigil/models/privacy_net.py",
            ],
            "local_metrics_only": True,
            "privacy_efficacy": "UNMEASURED",
            "claims_not_made": ["deepfake prevention", "modern face-recognition defeat",
                                "anonymity guarantee"],
        },
    }


def canonical_dump(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify the committed corpus.json is current")
    args = parser.parse_args(argv)
    expected = canonical_dump(build_corpus())
    current = CORPUS_PATH.read_text(encoding="utf-8") if CORPUS_PATH.exists() else ""
    if args.check:
        if current != expected:
            print("FAIL: evals/corpus.json is stale; rerun make eval-generate", file=sys.stderr)
            return 1
        print("OK: one active corpus generator is current")
        return 0
    CORPUS_PATH.write_text(expected, encoding="utf-8")
    print(f"wrote {CORPUS_PATH.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
