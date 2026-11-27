"""Functional fake-hospital attack exercise for the Infra app.

This is a real deterministic simulation, not a static storyboard. Every step
produces a signed or deliberately invalid event, passes it through the active
detector contract, Governor, append-only ledger and DryRunExecutor, and records
the result for the UI. It uses a synthetic hospital topology. No real patient
data, host, network traffic, Commander inference or live containment action is
involved.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apps.infra.detectors.registry import ORGAN_FIXTURES, detect as detect_event
from packages.contracts.config import DEFAULT_POLICY
from packages.contracts.envelope import sign_event
from packages.governance.safety import Topology
from packages.spine.runtime import SafetyRuntime, TokenStore

HOSPITAL_TOPOLOGY_PATH = Path(__file__).with_name("hospital_topology.json")
HOSPITAL_SENSOR_KEY = b"aster-memorial-synthetic-sensor-key"
HOSPITAL_CONTRACT = "raksha-fake-hospital-demo-v1"
HOSPITAL_ORGANIZATION = {
    "name": "Aster Memorial Hospital",
    "kind": "fake_hospital",
    "data": "synthetic",
    "network": "simulated",
    "topology_file": "apps/infra/demo/hospital_topology.json",
}
HOSPITAL_CAMPAIGN_ID = "C-HOSP-ATTACK-DEMO"
HOSPITAL_CASE_ID = "CASE-HOSP-ATTACK-DEMO"

CLAIMS_NOT_MADE = (
    "real hospital data",
    "real patient records",
    "real attack traffic",
    "real containment action",
    "Commander inference",
    "production SLA",
)


@dataclass(frozen=True)
class AttackStep:
    id: str
    title: str
    phase: str
    actor: str
    technique: str
    target: str
    entity: str
    organ: str
    leg: str
    payload: dict[str, Any]
    severity: int
    narrative: str
    event_kind: str = "signed"
    expected: str = "finding"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "phase": self.phase,
            "actor": self.actor,
            "technique": self.technique,
            "target": self.target,
            "entity": self.entity,
            "organ": self.organ,
            "leg": self.leg,
            "payload": dict(self.payload),
            "severity": self.severity,
            "narrative": self.narrative,
            "event_kind": self.event_kind,
            "expected": self.expected,
        }


def _firing(organ: str) -> dict[str, Any]:
    return dict(ORGAN_FIXTURES[organ]["firing"])


SCENARIO_STEPS: tuple[AttackStep, ...] = (
    AttackStep(
        id="credential-replay",
        title="Visitor Wi-Fi credential replay",
        phase="Initial access",
        actor="Synthetic attacker",
        technique="Session replay against guest portal",
        target="Guest Wi-Fi portal",
        entity="HOST_GUEST_113",
        organ="cookie_fluid_turbulence",
        leg="citizen",
        payload=_firing("cookie_fluid_turbulence"),
        severity=4,
        narrative="A replayed visitor session crosses the guest portal repeatedly. The signed event becomes the first campaign leg.",
    ),
    AttackStep(
        id="hostile-document",
        title="Hostile document in ER operations",
        phase="Delivery and fusion",
        actor="Synthetic attacker",
        technique="Adversarial document suffix",
        target="ER operations workstation",
        entity="HOST_ER_OPS_01",
        organ="bragg_fft_firewall",
        leg="infra",
        payload=_firing("bragg_fft_firewall"),
        severity=4,
        narrative="A crafted document reaches ER operations. The second campaign leg fuses the case and triggers deterministic planning.",
    ),
    AttackStep(
        id="ransomware-parity",
        title="Ransomware-style parity break",
        phase="Impact attempt",
        actor="Synthetic attacker",
        technique="Honey-block XOR invariant break",
        target="PACS imaging workstation",
        entity="HOST_PACS_WS_02",
        organ="page_curve_trap",
        leg="infra",
        payload=_firing("page_curve_trap"),
        severity=5,
        narrative="A simulated mass-encryption signal hits an imaging workstation. Detection is sealed before any dry-run proposal.",
    ),
    AttackStep(
        id="unsigned-infusion-pump",
        title="Unsigned infusion-pump telemetry",
        phase="Integrity failure",
        actor="Misconfigured synthetic sensor",
        technique="Missing signature",
        target="ICU monitor feed",
        entity="HOST_ICU_MONITOR_01",
        organ="hashimoto_percolation",
        leg="infra",
        payload=_firing("hashimoto_percolation"),
        severity=4,
        narrative="The crown clinical feed receives unsigned telemetry. Quarantine happens before detection, so no accusation is made.",
        event_kind="unsigned",
        expected="quarantined",
    ),
    AttackStep(
        id="tampered-coldchain",
        title="Tampered pharmacy cold-chain event",
        phase="Integrity failure",
        actor="Synthetic attacker",
        technique="Signature-preserving field tamper",
        target="Pharmacy OT controller",
        entity="HOST_PHARMACY_OT_03",
        organ="page_curve_trap",
        leg="infra",
        payload=_firing("page_curve_trap"),
        severity=4,
        narrative="A signed pharmacy event is altered after signing. The envelope validator quarantines it before any rule fires.",
        event_kind="tampered",
        expected="quarantined",
    ),
    AttackStep(
        id="forged-badge-reader",
        title="Forged badge-reader alert",
        phase="Integrity failure",
        actor="Synthetic attacker",
        technique="Wrong sensor key",
        target="Reception workstation",
        entity="HOST_RECEPTION_04",
        organ="muts_ebpf_repair",
        leg="infra",
        payload=_firing("muts_ebpf_repair"),
        severity=4,
        narrative="A badge-reader alert is signed with the wrong key. It is quarantined as forged rather than becoming evidence.",
        event_kind="forged",
        expected="quarantined",
    ),
    AttackStep(
        id="model-drift",
        title="Clinical model drift signal",
        phase="AI agent defence",
        actor="Synthetic attacker",
        technique="Sharp-curvature trajectory drift",
        target="ER decision-support service",
        entity="HOST_ER_OPS_01",
        organ="hessian_lyapunov_guard",
        leg="infra",
        payload=_firing("hessian_lyapunov_guard"),
        severity=3,
        narrative="A simulated decision-support signal shows unstable curvature and positive Lyapunov drift.",
    ),
    AttackStep(
        id="power-anomaly",
        title="Imaging workstation power anomaly",
        phase="Endpoint silicon",
        actor="Synthetic attacker",
        technique="Unexplained package-power residual",
        target="PACS workstation",
        entity="HOST_PACS_WS_02",
        organ="landauer_thermal_audit",
        leg="infra",
        payload=_firing("landauer_thermal_audit"),
        severity=3,
        narrative="Power telemetry cannot be explained by instruction rate on the synthetic imaging host.",
    ),
    AttackStep(
        id="cascade-risk",
        title="Lab subnet cascade risk",
        phase="Network healing",
        actor="Synthetic attacker",
        technique="Non-backtracking spectral-radius spike",
        target="Lab integration node",
        entity="HOST_LAB_09",
        organ="hashimoto_percolation",
        leg="infra",
        payload=_firing("hashimoto_percolation"),
        severity=4,
        narrative="A cascade-risk feature crosses the synthetic lab subnet threshold.",
    ),
    AttackStep(
        id="ebpf-invariant",
        title="Dual-strand invariant mismatch",
        phase="Endpoint silicon",
        actor="Synthetic attacker",
        technique="Simulated eBPF invariant break",
        target="Hospital app server",
        entity="HOST_APP_SRV_07",
        organ="muts_ebpf_repair",
        leg="infra",
        payload=_firing("muts_ebpf_repair"),
        severity=4,
        narrative="A simulated shield reports a dual-strand invariant mismatch on the app server.",
    ),
    AttackStep(
        id="rank-one-session",
        title="Rank-one session condensation",
        phase="Perimeter identity",
        actor="Synthetic attacker",
        technique="Condensed identity sessions",
        target="Reception workstation",
        entity="HOST_RECEPTION_04",
        organ="bec_spectral_filter",
        leg="citizen",
        payload=_firing("bec_spectral_filter"),
        severity=4,
        narrative="Reception sessions collapse into a rank-one pattern across a sufficient synthetic sample window.",
    ),
    AttackStep(
        id="unknown-sensor-adapter",
        title="Unknown sensor adapter",
        phase="Fail-closed boundary",
        actor="Unknown synthetic device",
        technique="Unregistered organ identifier",
        target="Guest device",
        entity="HOST_GUEST_113",
        organ="UNKNOWN_HOSPITAL_SENSOR",
        leg="infra",
        payload=_firing("hashimoto_percolation"),
        severity=3,
        narrative="An unknown organ identifier is quarantined before detection because no registered rule is allowed to run.",
        event_kind="unknown_organ",
        expected="quarantined",
    ),
)


class HospitalScenario:
    """Stateful fake-hospital exercise backed by the real deterministic runtime."""

    def __init__(self, topology_path: str | Path | None = None,
                 policy_path: str | Path | None = None) -> None:
        self.topology_path = str(topology_path or HOSPITAL_TOPOLOGY_PATH)
        self.policy_path = str(policy_path or DEFAULT_POLICY)
        self.topology = Topology.from_path(self.topology_path)
        self._lock = threading.RLock()
        self.reset()

    def _new_runtime(self) -> SafetyRuntime:
        token_store = TokenStore.from_tokens([
            ("hospital-admin", "admin", ("admin", "read", "telemetry:write")),
            ("hospital-sensor", "sensor", ("telemetry:write",)),
            ("hospital-observer", "observer", ("read",)),
        ])
        return SafetyRuntime(
            detector=detect_event,
            sensor_key=HOSPITAL_SENSOR_KEY,
            token_store=token_store,
            topology_path=self.topology_path,
            policy_path=self.policy_path,
            rate_limit_epm=600,
            blast_cap=3,
        )

    def reset(self) -> dict[str, Any]:
        with self._lock:
            self.runtime = self._new_runtime()
            self.cursor = 0
            self.attacks: list[dict[str, Any]] = []
            topology = self.topology.to_dict()
            self.assets: dict[str, dict[str, Any]] = {
                str(node["id"]): {
                    "id": str(node["id"]),
                    "kind": node.get("kind"),
                    "role": node.get("role") or node.get("kind"),
                    "crown": bool(node.get("crown")),
                    "status": "normal",
                    "last_event": None,
                    "last_outcome": None,
                }
                for node in topology["nodes"]
            }
            self.state = "ready"
            return self.state_snapshot()

    def _event_for_step(self, step: AttackStep, index: int) -> dict[str, Any]:
        raw: dict[str, Any] = {
            "event_id": f"EV-HOSP-{index:02d}-{step.id.upper()}",
            "ts": f"2026-11-26T10:{index:02d}:00Z",
            "organ": step.organ,
            "campaign_id": HOSPITAL_CAMPAIGN_ID,
            "case_id": HOSPITAL_CASE_ID,
            "leg": step.leg,
            "severity": step.severity,
            "entity": step.entity,
            "summary": step.title,
            "payload": dict(step.payload),
        }
        if step.event_kind == "unsigned":
            return raw
        if step.event_kind == "forged":
            return sign_event(raw, key=b"wrong-hospital-demo-key")
        signed = sign_event(raw, key=HOSPITAL_SENSOR_KEY)
        if step.event_kind == "tampered":
            tampered = dict(signed)
            tampered["severity"] = 1
            return tampered
        return signed

    def _asset_status(self, step: AttackStep, result: dict[str, Any]) -> str:
        if result.get("quarantined"):
            return "quarantined"
        if result.get("detections"):
            return "detected"
        if result.get("executions"):
            return "dry_run_contained"
        return "observed"

    def step(self) -> dict[str, Any] | None:
        with self._lock:
            if self.cursor >= len(SCENARIO_STEPS):
                self.state = "complete"
                return None
            index = self.cursor + 1
            attack = SCENARIO_STEPS[self.cursor]
            event = self._event_for_step(attack, index)
            result = self.runtime.process_event(event, source="hospital-demo")
            detections = list(result.get("detections") or [])
            decisions = list(result.get("decisions") or [])
            executions = list(result.get("executions") or [])
            status = self._asset_status(attack, result)
            asset = self.assets.get(attack.entity)
            if asset is not None:
                asset["status"] = status
                asset["last_event"] = attack.id
                asset["last_outcome"] = result.get("reason") or status
            entry = {
                "index": index,
                "event_id": event.get("event_id", ""),
                "timestamp": event.get("ts", ""),
                "step": attack.to_dict(),
                "outcome": "quarantined" if result.get("quarantined") else ("finding" if detections else "no_detection"),
                "result": result,
                "detector_rules": [str(item.get("rule_id") or "") for item in detections],
                "verdicts": [str(item.get("verdict") or "") for item in decisions],
                "dry_run_actions": [str(item.get("status") or "") for item in executions],
                "real_actions": sum(
                    1 for item in executions
                    if item.get("real_action") or item.get("executed")
                ),
                "ledger_height": int(result.get("ledger_height") or self.runtime.ledger.height()),
                "asset_status": status,
            }
            self.attacks.append(entry)
            self.cursor += 1
            self.state = "complete" if self.cursor == len(SCENARIO_STEPS) else "running"
            return entry

    def start(self) -> dict[str, Any]:
        with self._lock:
            self.reset()
            first = self.step()
            return {"step": first, "state": self.state_snapshot()}

    def state_snapshot(self) -> dict[str, Any]:
        with self._lock:
            runtime_state = self.runtime.state_snapshot()
            decisions = self.runtime.decisions_snapshot()
            quarantine = self.runtime.quarantine_snapshot()
            metrics = self.runtime.metrics_snapshot()
            ledger_verify = self.runtime.ledger.verify()
            all_executions = [action for entry in self.attacks for action in entry["dry_run_actions"]]
            real_actions = sum(int(entry["real_actions"]) for entry in self.attacks)
            next_step = SCENARIO_STEPS[self.cursor].to_dict() if self.cursor < len(SCENARIO_STEPS) else None
            return {
                "contract": HOSPITAL_CONTRACT,
                "status": "ok",
                "organization": dict(HOSPITAL_ORGANIZATION),
                "scenario": {
                    "name": "Aster Memorial Hospital attack exercise",
                    "state": self.state,
                    "started": self.cursor > 0,
                    "done": self.cursor >= len(SCENARIO_STEPS),
                    "steps_total": len(SCENARIO_STEPS),
                    "steps_completed": self.cursor,
                    "campaign_id": HOSPITAL_CAMPAIGN_ID,
                    "case_id": HOSPITAL_CASE_ID,
                    "campaign_fused": any(bool(c.get("fused")) for c in runtime_state["campaigns"]),
                    "executor_mode": "dry-run",
                    "commander_enabled": False,
                    "model_backed": False,
                    "real_action_count": real_actions,
                    "dry_run_action_count": len(all_executions),
                    "claims_not_made": list(CLAIMS_NOT_MADE),
                },
                "topology": self.topology.to_dict(),
                "assets": [dict(self.assets[key]) for key in sorted(self.assets)],
                "steps": [step.to_dict() for step in SCENARIO_STEPS],
                "next_step": next_step,
                "attacks": [dict(entry) for entry in self.attacks],
                "runtime": {
                    "state": runtime_state,
                    "decisions": decisions,
                    "quarantine": quarantine,
                    "metrics": metrics,
                    "ledger_verify": ledger_verify,
                    "ledger_height": self.runtime.ledger.height(),
                    "timeline": runtime_state["timeline"],
                    "finding_count": len(runtime_state["detections"]),
                    "quarantine_count": quarantine["count"],
                    "decision_count": decisions["count"],
                },
            }


__all__ = [
    "HOSPITAL_TOPOLOGY_PATH", "HOSPITAL_SENSOR_KEY", "HOSPITAL_CONTRACT",
    "HOSPITAL_ORGANIZATION", "HOSPITAL_CAMPAIGN_ID", "HOSPITAL_CASE_ID",
    "CLAIMS_NOT_MADE", "AttackStep", "SCENARIO_STEPS", "HospitalScenario",
]
