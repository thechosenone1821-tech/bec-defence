#!/usr/bin/env python3
"""Phase 6–8 deterministic integration checker.

Proves one detector registry, one quarantine-before-detection contract, one
deterministic Governor/planner/executor/ledger path, one unified app/WS surface,
sealed-before-broadcast decisions, read-only console and no AI model imports.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from fastapi.testclient import TestClient  # noqa: E402

from apps.infra.backend.app import create_app  # noqa: E402
from apps.infra.console import console_card, console_html, console_js  # noqa: E402
from apps.infra.detectors import (  # noqa: E402
    ORGAN_FIXTURES, ORGAN_SPECS, detect, detector_card, known_organs,
)
from packages.contracts.config import DEFAULT_TOPOLOGY  # noqa: E402
from packages.contracts.envelope import sign_event  # noqa: E402
from packages.contracts.backend import validate_routes  # noqa: E402
from packages.governance.commander import commander_card  # noqa: E402
from packages.governance.safety import (  # noqa: E402
    PLANNER_ID, DryRunExecutor, ExhaustivePlanner, Governor, Proposal,
    Topology, UnsafeProposal, safety_card,
)
from packages.ledger.runtime_ledger import RuntimeLedger  # noqa: E402

SENSOR_KEY = b"phase678-checker-key"
ADMIN = "checker-admin"
SENSOR = "checker-sensor"
OBSERVER = "checker-observer"
CONSOLE = "checker-console"

ACTIVE_FILES = (
    "apps/infra/backend/app.py",
    "apps/infra/detectors/__init__.py",
    "apps/infra/detectors/registry.py",
    "apps/infra/console/__init__.py",
    "packages/spine/runtime.py",
    "packages/spine/bus.py",
    "packages/spine/__init__.py",
    "packages/governance/safety.py",
    "packages/governance/commander.py",
    "packages/ledger/runtime_ledger.py",
)
FORBIDDEN_IMPORT_PREFIXES = (
    "spine.bus", "spine.slm_client", "spine.orchestrator",
    "citizen.voiceguard", "voiceguard", "maya", "ollama", "transformers",
    "torch", "tensorflow",
)


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _import_names(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def _raw(event_id="CHK-1", organ="page_curve_trap", payload=None, leg="infra"):
    return {
        "event_id": event_id, "ts": "2026-11-26T09:00:00Z", "organ": organ,
        "campaign_id": "C-CHK", "case_id": "CASE-CHK", "leg": leg,
        "severity": 5, "entity": "HOST_APP_SRV_07", "summary": "checker event",
        "payload": payload or {"parity_break": 1},
    }


def _tokens():
    return [
        (ADMIN, "admin", ("admin", "read", "telemetry:write")),
        (SENSOR, "sensor", ("telemetry:write",)),
        (OBSERVER, "observer", ("read",)),
        (CONSOLE, "console", ("read",)),
    ]


def _client(seed_demo: bool = False, **overrides):
    params = dict(sensor_key=SENSOR_KEY, token_records=_tokens(),
                  console_token=CONSOLE, topology_path=str(DEFAULT_TOPOLOGY),
                  seed_demo=seed_demo, rate_limit_epm=600, blast_cap=3)
    params.update(overrides)
    app = create_app(**params)
    return TestClient(app), app


def run_checks() -> list[str]:
    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    # -- Phase 6: one registry, fixtures, quarantine before detection -------
    card = detector_card()
    check(len(ORGAN_SPECS) == len(ORGANS := {s.name: s for s in ORGAN_SPECS}) == 8,
          "Phase 6 registry does not contain exactly 8 organs")
    check(len(known_organs()) == len(ORGAN_FIXTURES) == 8,
          "Phase 6 organ names or fixtures are not one-to-one")
    check(card["registry_count"] == 1 and card["detection_contract"] == "detect(event) -> DetectionResult",
          "Phase 6 detection contract is not singular")
    check(card["frozen_voiceguard_integrated"] is False,
          "frozen Citizen VoiceGuard must remain unintegrated")
    check("ORGANS =" not in _text("apps/infra/detectors/__init__.py"),
          "Phase 6 compatibility facade declares a second registry")
    for spec in ORGAN_SPECS:
        bundle = ORGAN_FIXTURES[spec.name]
        check(set(bundle) == {"firing", "silent", "missing"},
              f"{spec.name} lacks firing/silent/missing fixtures")
        firing = detect(sign_event(_raw("F-" + spec.name, spec.name, bundle["firing"]),
                                   key=SENSOR_KEY), key=SENSOR_KEY)
        silent = detect(sign_event(_raw("S-" + spec.name, spec.name, bundle["silent"]),
                                   key=SENSOR_KEY), key=SENSOR_KEY)
        missing = detect(sign_event(_raw("M-" + spec.name, spec.name, bundle["missing"]),
                                    key=SENSOR_KEY), key=SENSOR_KEY)
        check(firing.status == "finding" and firing.finding is not None,
              f"{spec.name} firing fixture did not produce a finding")
        check(silent.status == "no_detection" and silent.finding is None,
              f"{spec.name} silent fixture produced a false accusation")
        check(missing.status == "no_detection" and missing.finding is None,
              f"{spec.name} missing-feature fixture produced a false accusation")
    unsigned = detect(_raw("U1"), key=SENSOR_KEY)
    tampered = sign_event(_raw("T1"), key=SENSOR_KEY)
    tampered["severity"] = 1
    forged = sign_event(_raw("F1"), key=b"wrong-key")
    unknown = detect(sign_event(_raw("X1", "not_an_organ"), key=SENSOR_KEY),
                     key=SENSOR_KEY)
    quarantined = [unsigned, detect(tampered, key=SENSOR_KEY),
                   detect(forged, key=SENSOR_KEY), unknown]
    check(all(r.status == "quarantined" and r.finding is None for r in quarantined),
          "unsigned/tampered/forged/unknown event reached detection")
    check({r.state for r in quarantined} == {"unsigned", "tampered", "unknown_organ"},
          "quarantine states are not first-class")

    # -- Phase 7: one planner, Governor, executor, ledger ------------------
    topology = Topology.from_path(DEFAULT_TOPOLOGY)
    try:
        Proposal(campaign_id="C-BAD", action="node_quarantine",
                 entity="HOST_ICU_MONITOR_01",
                 assets_severed=("HOST_ICU_MONITOR_01",), edges_cut=(),
                 blast_radius=("HOST_ICU_MONITOR_01",), detail="illegal",
                 fallback_proposal_id=None, planner_id=PLANNER_ID,
                 crown_assets=topology.crown_assets,
                 crown_gateway_edges=topology.crown_gateway_edges)
        check(False, "crown/Tier-0 Proposal was constructible")
    except UnsafeProposal:
        pass
    planner = ExhaustivePlanner(topology)
    campaign = {"campaign_id": "C-P7", "case_id": "CASE-P7",
                "legs": ["citizen", "infra"], "organs": ["page_curve_trap"]}
    proposals = planner.proposals_for(campaign)
    check(len(proposals) >= len(topology.legal_edges()) + 2 * len(topology.legal_hosts()),
          "planner is not exhaustive over legal edges/hosts/fallbacks")
    check(all(not any(topology.is_crown(a) for a in p.assets_severed)
              and not set(p.edges_cut) & set(topology.crown_gateway_edges)
              for p in proposals),
          "planner emitted a crown asset or gateway cut")
    governor = Governor(blast_cap=3)
    decisions = [governor.decide(p) for p in proposals]
    check(any(d.verdict == "ALLOWED" for d in decisions),
          "Governor produced no dry-run allowance")
    check(any(d.verdict == "REFUSED" for d in decisions),
          "Governor produced no first-class refusal")
    check(not hasattr(governor, "override"), "Governor has an override method")
    receipt = DryRunExecutor().execute(decisions[0])
    check(receipt["executed"] is False and receipt["real_action"] is False,
          "dry-run executor claims a real action")
    check(safety_card()["crown_cuts"] == "impossible_by_construction",
          "safety card weakens the crown lock")
    commander = commander_card()
    check(commander["enabled"] is False and commander["model_invoked"] is False
          and commander["fallback_only"] is True,
          "optional Commander is not disabled/fallback-only")
    ledger = RuntimeLedger()
    ledger.append(kind="probe", ref="R1", text="probe", payload={"ok": True})
    check(ledger.verify()["ok"] is True, "runtime ledger hash chain failed")

    runtime_text = _text("packages/spine/runtime.py")
    check(runtime_text.count("self.ledger.append(") == 1,
          "more than one ledger write path in the active runtime")
    check("decision is already sealed. Only now is it broadcast." in runtime_text,
          "decision seal-before-broadcast marker missing")
    check(not any(name == "spine.bus" or name.startswith("spine.bus.")
                  for rel in ACTIVE_FILES
                  for name in _import_names(ast.parse(_text(rel), filename=rel))),
          "active Phase 6–8 code imports the legacy spine bus")
    check("from .runtime import create_app" in _text("packages/spine/__init__.py"),
          "packages.spine create_app does not delegate to the unified runtime")
    check("from .runtime import create_app as _create_runtime_app" in _text("packages/spine/bus.py"),
          "packages.spine.bus is not a compatibility facade")
    check("from packages.spine.contract import (" in _text("apps/infra/backend/app.py"),
          "Infra app lost the Phase 3 shared-contract marker")
    check("create_runtime_app(" in _text("apps/infra/backend/app.py")
          and "FastAPI(" not in _text("apps/infra/backend/app.py"),
          "Infra app is not a thin facade over one runtime app factory")

    runtime_tree = ast.parse(runtime_text, filename="packages/spine/runtime.py")
    ws_functions = []
    for node in ast.walk(runtime_tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = [d for d in node.decorator_list
                          if isinstance(d, ast.Call)
                          and isinstance(d.func, ast.Attribute)
                          and d.func.attr == "websocket"]
            if decorators:
                ws_functions.append((node, decorators))
    check(len(ws_functions) == 1, "more than one WebSocket stream implementation")
    check(len(ws_functions[0][1]) == 2 if ws_functions else False,
          "canonical /v1 and legacy /ws paths are not the same one stream")

    # -- Phase 8: routes, auth, quarantine, sealed decisions, console ------
    empty_client, empty_app = _client(seed_demo=False)
    check(validate_routes(empty_app, "spine-v2")["ok"], "spine-v2 route profile is incomplete")
    check(validate_routes(empty_app, "enterprise-i1")["ok"], "enterprise-i1 route profile is incomplete")
    check(empty_client.get("/healthz").status_code == 200, "health route failed")
    root = empty_client.get("/", follow_redirects=False)
    check(root.status_code == 307 and root.headers.get("location") == "/app/console",
          "preview root does not redirect to the read-only console")
    check(empty_client.get("/v1/state").status_code == 401, "missing token was accepted")
    check(empty_client.get("/v1/state",
                           headers={"Authorization": "Bearer " + SENSOR}).status_code == 403,
          "write-scope token was allowed to read")
    read = {"Authorization": "Bearer " + OBSERVER}
    write = {"Authorization": "Bearer " + SENSOR}
    ok = empty_client.post("/v1/telemetry", json=sign_event(_raw(), key=SENSOR_KEY),
                           headers=write)
    check(ok.status_code == 200 and ok.json()["detections"], "signed telemetry did not detect")
    unsigned_api = empty_client.post("/v1/telemetry", json=_raw("API-U"), headers=write)
    check(unsigned_api.json()["quarantined"] is True and not unsigned_api.json()["detections"],
          "API quarantined unsigned event was detected as real")
    check(empty_client.get("/v1/quarantine", headers=read).json()["count"] == 1,
          "quarantine API did not preserve the unsigned event")
    check("counters" in empty_client.get("/v1/metrics", headers=read).json(),
          "metrics endpoint did not expose counters")

    demo_client, demo_app = _client(seed_demo=True)
    runtime = demo_app.state.runtime
    state = demo_client.get("/v1/state", headers={"Authorization": "Bearer " + CONSOLE}).json()
    check({"detection", "proposal", "decision", "ledger", "quarantine"}
          <= {entry["stage"] for entry in state["timeline"]},
          "console state does not show detection → proposal → decision → ledger")
    check(any(entry["kind"] == "refusal" for entry in state["timeline"]),
          "refusals are not visible in the campaign sequence")
    decisions_payload = demo_client.get("/v1/decisions", headers=read).json()
    check({"containment", "refusal"} <= {d["kind"] for d in decisions_payload["decisions"]},
          "refusals are not first-class ledger decision records")
    check(demo_client.get("/v1/ledger/verify", headers=read).json()["ok"],
          "demo ledger chain is invalid")
    check(demo_client.post("/v1/decisions/P-anything/override",
                           headers={"Authorization": "Bearer " + ADMIN}).status_code == 403,
          "admin override became possible")
    for item in runtime.hub.history():
        if item["kind"] == "decision":
            seq = item["data"]["ledger_seq"]
            check(any(entry["stage"] == "ledger" and entry["ledger_seq"] == seq
                      and entry["step"] < item["step"] for entry in runtime.timeline),
                  f"decision {seq} was broadcast before it was sealed")

    html = console_html()
    served_js = console_js(CONSOLE)
    static_js = _text("apps/infra/console/console.js")
    check('src="console.js"' in html and "read-only" in html.lower(),
          "console HTML is not a read-only page with relative JS")
    check("__RAKSHA_READ_TOKEN__" in static_js and "__RAKSHA_READ_TOKEN__" not in served_js,
          "console token placeholder was not injected by the backend")
    for banned in ("POST", "override", "localhost", ADMIN, SENSOR):
        check(banned not in static_js,
              f"console source contains mutating/unsafe marker {banned!r}")
    check("/v1/state" in static_js and "/v1/telemetry/stream" in static_js,
          "console does not read unified state/WS endpoints")
    check(console_card()["read_only"] is True
          and console_card()["mutating_routes"] == [],
          "console capability card is not read-only")

    # -- No AI / unchanged frozen assets / prior gates --------------------
    for rel in ACTIVE_FILES:
        for name in _import_names(ast.parse(_text(rel), filename=rel)):
            check(not any(name == prefix or name.startswith(prefix + ".")
                          for prefix in FORBIDDEN_IMPORT_PREFIXES),
                  f"forbidden model/legacy import in {rel}: {name}")
    probe_code = (
        "import sys; from pathlib import Path; r=Path.cwd(); "
        "sys.path[:0]=[str(r),str(r/'raksha-code')]; import apps.infra.backend.app; "
        "banned=('spine.bus','spine.slm_client','spine.orchestrator',"
        "'citizen.voiceguard','voiceguard','maya','ollama','transformers','torch','tensorflow'); "
        "loaded=[m for m in sys.modules if any(m==p or m.startswith(p+'.') for p in banned)]; "
        "assert not loaded, loaded; print('ok')"
    )
    probe = subprocess.run([sys.executable, "-c", probe_code], cwd=ROOT,
                           capture_output=True, text=True,
                           env={**dict(os.environ), "OLLAMA_HOST": "http://127.0.0.1:9",
                                "EIGENSHIELD_MODEL": "disabled"})
    check(probe.returncode == 0 and "ok" in probe.stdout,
          f"clean app import loaded AI/legacy modules: {probe.stdout}{probe.stderr}")
    for checker_rel in ("tools/check_phase3_contracts.py",
                        "tools/check_phase4_citizen.py",
                        "tools/check_phase5_messageguard.py",
                        "tools/check_frozen_assets.py"):
        result = subprocess.run([sys.executable, str(ROOT / checker_rel)],
                                cwd=ROOT, capture_output=True, text=True)
        check(result.returncode == 0,
              f"{checker_rel} failed: {result.stdout[-500:]}{result.stderr[-500:]}")
    for rel in ("raksha/PHASE678_UNIFIED_INTEGRATION.md",
                "raksha/adr/ADR-014-phase6-8-unified-integration.md",
                "apps/infra/console/README.md",
                "tools/check_phase678_integration.py",
                "tests/test_phase678_integration.py"):
        check((ROOT / rel).is_file(), f"missing Phase 6–8 deliverable: {rel}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 6–8 integration checker")
    parser.add_argument("--json", action="store_true", help="print failures as JSON")
    args = parser.parse_args(argv)
    failures = run_checks()
    if failures:
        if args.json:
            print(json.dumps({"ok": False, "failures": failures}, indent=2))
        else:
            print("PHASE 6-8 INTEGRATION CHECK FAILED")
            for failure in failures:
                print("  -", failure)
        return 2
    print("OK: Phase 6-8 unified integration; 8 organs, one safety/ledger path, one backend/WS/console; no AI models loaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
