"""Phase 3 shared-contract unit/integration checks from the legacy cwd."""
from __future__ import annotations

import ast
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "raksha-code")]

from packages.contracts import (  # noqa: E402
    CONTRACT_VERSION, LEGACY_BANDS, REASON_CATALOGUE, SharedActionGate,
    canonical_json, check_pinned_configs, validate_envelope,
)
from packages.contracts.backend import (  # noqa: E402
    PROFILE_PATHS, validate_routes,
)
from packages.contracts.envelope import (  # noqa: E402
    PROFILE_ENTERPRISE_I1, PROFILE_ORGAN_SEALED, PROFILE_ORGAN_TELEMETRY,
    VerificationState, profile_for, sign_event, verify_signature,
)
from packages.contracts.entities import ENTITY_PATH  # noqa: E402
from packages.ledger.interface import LedgerAdapter, verify_ledger  # noqa: E402
from spine.telemetry_mac import sign_event as legacy_sign_event  # noqa: E402
from sentinel.shields.base_organ import seal_event  # noqa: E402


def _organ_event(event_id: str = "evt_phase3_0001"):
    return {
        "event_id": event_id,
        "timestamp_utc": "2026-11-26T00:00:00Z",
        "ring": "RING_3_ENDPOINT_SILICON",
        "organ": "ENDPOINT_PAGE_CURVE",
        "signal_type": "PARITY_ENTROPY_COLLAPSE",
        "severity": 0.9,
        "entities": {"host_id": "HOST_042"},
        "metrics": {"parity_delta": 0.9},
        "reason": "phase 3 contract probe",
    }


def _load_enterprise_events():
    name = "phase3_enterprise_events_interop"
    if name in sys.modules:
        return sys.modules[name]
    path = ROOT / "archive/provenance/raksha-enterprise/raksha-enterprise/raksha/events.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve annotations via sys.modules
    spec.loader.exec_module(module)
    return module


def _i1_event():
    return {
        "event_id": "EV-I1-1", "ts": "2026-11-26T00:00:00Z",
        "organ": "organ", "campaign_id": "C-1", "case_id": "case-1",
        "leg": "citizen", "severity": 4, "entity": "N-VICTIM-PHONE",
        "summary": "synthetic probe", "payload": {"score": 0.8},
    }


def test_canonical_json_and_config_pins_are_stable():
    assert canonical_json({"b": 1, "a": "✓"}) == '{"a":"\\u2713","b":1}'
    report = check_pinned_configs()
    assert report["ok"] is True, report["mismatches"]
    assert len(report["checked"]) == 5


def test_all_shipped_envelope_profiles_validate_through_one_validator():
    organ = legacy_sign_event(_organ_event())
    sealed = seal_event(_organ_event("evt_phase3_sealed"))
    key = b"phase3-i1-key-0123456789abcdef"
    i1 = sign_event(_i1_event(), key=key)

    assert profile_for(organ) == PROFILE_ORGAN_TELEMETRY
    assert profile_for(sealed) == PROFILE_ORGAN_SEALED
    assert profile_for(i1) == PROFILE_ENTERPRISE_I1

    for raw, key_arg in ((organ, None), (sealed, None), (i1, key)):
        result = validate_envelope(raw, key=key_arg)
        assert result.contract == CONTRACT_VERSION
        assert result.verified and result.actionable and result.governor_required
        assert result.signature["state"] == VerificationState.VALID.value
        assert json.loads(canonical_json(result.to_dict()))["contract"] == CONTRACT_VERSION

    forged = dict(i1)
    forged["severity"] = 1
    assert verify_signature(forged, key=key) is VerificationState.TAMPERED
    assert validate_envelope(forged, key=key).actionable is False
    assert validate_envelope(_organ_event()).state is VerificationState.UNSIGNED
    assert validate_envelope(_organ_event(), require_signature=False).actionable is False

    # The historical enterprise signer/verifier and the shared validator agree.
    enterprise = _load_enterprise_events()
    event = enterprise.Event("EV-P3-INTEROP", "2026-11-26T00:00:00Z", "voiceguard",
                             "C-P3", "case-p3", "citizen", 4, "N-P3-PHONE",
                             "phase3 interop", {"score": 0.9})
    enterprise.sign_event(event, key)
    raw = event.to_dict()
    shared_result = validate_envelope(raw, key=key)
    assert shared_result.profile == PROFILE_ENTERPRISE_I1
    assert shared_result.verified and shared_result.actionable

    unsigned = {k: v for k, v in raw.items() if k not in ("sig", "sig_alg")}
    shared_signed = sign_event(unsigned, key=key, profile=PROFILE_ENTERPRISE_I1)
    rebuilt = enterprise.Event.from_dict(json.loads(json.dumps(shared_signed)))
    assert enterprise.verify_event(rebuilt, key) is enterprise.VerifyState.VALID


def _frozen_msg_reason_family():
    path = ROOT / "raksha-code/citizen/voiceguard/i18n.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "MSG_REASON_FAMILY" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("frozen MSG_REASON_FAMILY assignment missing")


def test_reason_band_and_entity_tables_are_single_source():
    import apps.citizen.messageguard.reasons as app_reasons
    import apps.citizen.messageguard.bandmap as app_bandmap
    import apps.citizen.messageguard.scorer as app_scorer
    from packages.contracts.bands import band
    from packages.contracts.reasons import REASON_CATALOGUE as SHARED_REASONS

    assert app_reasons.REASON_CATALOGUE is REASON_CATALOGUE is SHARED_REASONS
    assert app_bandmap.LEGACY_BANDS is LEGACY_BANDS
    assert app_scorer.band is band
    assert _frozen_msg_reason_family() == {code: entry[0] for code, entry in REASON_CATALOGUE.items()}
    assert len(REASON_CATALOGUE) == 29
    assert ENTITY_PATH == ("session_id", "user_id", "host_id", "vlan_id", "service_id")


def test_backend_contract_maps_both_profiles():
    class Route:
        def __init__(self, path): self.path = path
    class App:
        def __init__(self, paths): self.routes = [Route(p) for p in paths]

    assert validate_routes(App(PROFILE_PATHS["spine-v2"]), "spine-v2")["ok"] is True
    assert validate_routes(App(PROFILE_PATHS["enterprise-i1"]), "enterprise-i1")["ok"] is True
    assert validate_routes(App([]), "enterprise-i1")["missing"]


def test_shared_action_gate_blocks_unsigned_and_governor_refusals():
    calls = {"executor": 0}

    def executor(tool, args):
        calls["executor"] += 1
        return {"status": "DRY_RUN_OK", "tool": tool, "dry_run": True}

    class Governor:
        def __init__(self, decision): self.decision = decision; self.calls = 0
        def evaluate(self, action, context=None):
            self.calls += 1
            return {"decision": self.decision, "reasons": []}

    action = {"tool": "drop_bec_cluster", "args": {"cluster_id": "c1", "ttl_seconds": 60}}
    unsigned = SharedActionGate(Governor("APPROVED"), executor).submit(_organ_event(), action)
    assert unsigned.allowed is False
    assert unsigned.reason.startswith("signature_not_valid")
    assert calls["executor"] == 0

    blocked_governor = Governor("BLOCKED")
    blocked = SharedActionGate(blocked_governor, executor).submit(legacy_sign_event(_organ_event()), action)
    assert blocked.allowed is False
    assert blocked.reason == "governor_refused:BLOCKED"
    assert blocked_governor.calls == 1
    assert calls["executor"] == 0

    approved = SharedActionGate(Governor("APPROVED"), executor).submit(legacy_sign_event(_organ_event("evt_phase3_approved")), action)
    assert approved.allowed is True
    assert approved.executor_result["dry_run"] is True
    assert calls["executor"] == 1


def test_one_ledger_append_verify_interface_normalises_three_backends():
    class SpineBackend:
        def __init__(self): self.rows = []
        def append(self, record_type, payload):
            self.rows.append((record_type, payload)); return {"seq": len(self.rows)}
        def verify(self): return {"valid": True, "entries": len(self.rows), "head": "GENESIS"}

    class EnterpriseBackend:
        def append(self, *, kind, ref, text, payload): return {"kind": kind, "ref": ref}
        def verify(self):
            @dataclass
            class Report:
                ok: bool = True
                height: int = 1
                head: str = "abc"
                reason: str = "chain intact"
            return Report()

    class GovernanceBackend:
        def append(self, **kwargs): return kwargs
        def verify(self): return (True, None)

    for backend, profile in ((SpineBackend(), "spine-v2"), (EnterpriseBackend(), "enterprise-i1"), (GovernanceBackend(), "governance-v1")):
        adapter = LedgerAdapter(backend, profile=profile)
        adapter.append("phase3", {"status": "OK"})
        out = adapter.verify()
        assert out["valid"] is True and out["ok"] is True
        assert verify_ledger(backend, profile=profile).ok is True
