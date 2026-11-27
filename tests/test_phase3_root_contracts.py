"""Root-level Phase 3 acceptance checks."""
from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from apps.citizen.api import build_app as build_citizen_app  # noqa: E402
from apps.infra.backend.app import create_app as create_infra_app  # noqa: E402
from packages.contracts import (  # noqa: E402
    BACKEND_CONTRACT_VERSION, CONTRACT_VERSION, DEFAULT_POLICY,
    DEFAULT_TOPOLOGY, validate_envelope,
)
from packages.contracts.canonical import CANONICAL_JSON_RULE  # noqa: E402
from packages.contracts.envelope import sign_event  # noqa: E402
from raavan.killchain import build_campaign  # noqa: E402


def test_phase3_contract_checker_passes():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/check_phase3_contracts.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "pinned and consistent" in result.stdout


def test_citizen_and_infra_expose_the_same_contract():
    citizen = TestClient(build_citizen_app(bus_url="", poster=lambda e: {"accepted": 1}))
    citizen_contract = citizen.get("/api/citizen/health").json()["contract"]
    assert citizen_contract["event"] == CONTRACT_VERSION
    assert citizen_contract["canonical_json"] == CANONICAL_JSON_RULE
    assert citizen_contract["signature_required"] is True
    assert citizen_contract["governor_required"] is True

    with tempfile.TemporaryDirectory() as tmp:
        policy = Path(tmp) / "policy.yaml"
        shutil.copy(DEFAULT_POLICY, policy)
        infra = TestClient(create_infra_app(policy_path=str(policy), topology_path=str(DEFAULT_TOPOLOGY)))
        health = infra.get("/app/health").json()
        card = infra.get("/app/contract").json()
        assert health["contract"]["event"] == CONTRACT_VERSION
        assert health["contract"]["canonical_json"] == CANONICAL_JSON_RULE
        assert card["contract"] == BACKEND_CONTRACT_VERSION
        assert card["event_contract"] == CONTRACT_VERSION
        assert card["canonical_json"] == CANONICAL_JSON_RULE
        assert card["route_check"]["ok"] is True, card["route_check"]
        assert card["ledger_cli"] == "python -m packages.ledger.cli verify"


def test_citizen_raavan_and_eval_signers_validate_identically():
    captured: list[dict] = []
    citizen = TestClient(build_citizen_app(bus_url="", poster=lambda e: captured.append(e) or {"accepted": 1}))
    report = citizen.post("/api/citizen/report", json={"category": "message", "severity": 0.8}).json()
    assert report["status"] == "REPORTED"
    citizen_event = captured[0]

    import evals.run_evals as infra_evals
    eval_event = infra_evals.sign_event({
        "event_id": "evt_eval_phase3", "timestamp_utc": "2026-11-26T00:00:00Z",
        "ring": "RING_1_PERIMETER_IDENTITY", "organ": "EVAL_HARNESS",
        "signal_type": "EVAL_PROBE", "severity": 0.7,
    })
    raavan_event = sign_event(dict(build_campaign()[0]))

    results = [validate_envelope(event).to_dict() for event in (citizen_event, raavan_event, eval_event)]
    assert {r["contract"] for r in results} == {CONTRACT_VERSION}
    assert {r["profile"] for r in results} == {"organ-telemetry-v1"}
    assert all(r["verified"] and r["actionable"] for r in results)
    assert all(r["governor_required"] and r["signature_required"] for r in results)
    assert all(r["signature"]["algorithm"] == "HMAC-SHA256" for r in results)
    assert infra_evals.sign_event is sign_event


def test_one_ledger_cli_verifies_one_chain_from_both_entrypoints():
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Path(tmp) / "audit.jsonl"
        from spine.ledger import AuditLedger
        AuditLedger(str(ledger)).append("phase3_contract_probe", {"status": "OK"})
        shared = subprocess.run(
            [sys.executable, "-m", "packages.ledger.cli", "verify", "--ledger", str(ledger)],
            cwd=ROOT, capture_output=True, text=True,
        )
        legacy = subprocess.run(
            [sys.executable, "-m", "spine.ledger_cli", "verify", "--ledger", str(ledger)],
            cwd=ROOT / "raksha-code", capture_output=True, text=True,
        )
        assert shared.returncode == 0, shared.stdout + shared.stderr
        assert legacy.returncode == 0, legacy.stdout + legacy.stderr
        shared_report = json.loads(shared.stdout)
        assert shared_report == json.loads(legacy.stdout)
        assert shared_report["valid"] is True
        assert shared_report["entries"] == 1


def test_shared_contract_slot_reserves_voiceguard_without_importing_it():
    source = (ROOT / "packages/contracts/voiceguard.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.append(node.module)
    assert not any(name.startswith(("citizen.voiceguard", "voiceguard", "maya")) for name in imported)
    assert "RESERVED_NOT_INTEGRATED" in source


def test_phase3_docs_and_pin_manifest_exist():
    assert (ROOT / "raksha/PHASE3_CONTRACT_SPINE.md").is_file()
    assert (ROOT / "raksha/adr/ADR-011-unified-contracts.md").is_file()
    assert (ROOT / "packages/contracts/config_pins.json").is_file()
    assert (ROOT / "tools/check_phase3_contracts.py").is_file()
