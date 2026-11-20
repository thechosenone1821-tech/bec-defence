"""PLANE 3 — Cross-ring kill-chain correlator & executive brief writer.

Attempts the local SLM first (grammar-constrained JSON via SLMClient). If the
model is unreachable or returns invalid/non-allowlisted output, falls back to a
deterministic rule engine so demos and tests are reproducible offline.

Defense in depth: every action — from either path — is validated against
commander/tool_schemas.json here, and AGAIN by the Plane-4 Governor. The
Commander can propose; only the Governor disposes.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from commander.slm_client import SLMClient

_HERE = os.path.dirname(__file__)


def load_tool_schemas(path: Optional[str] = None) -> List[Dict[str, Any]]:
    with open(path or os.path.join(_HERE, "tool_schemas.json")) as f:
        return json.load(f)


def load_system_prompt(path: Optional[str] = None) -> str:
    with open(path or os.path.join(_HERE, "system_prompt.txt")) as f:
        return f.read()


ALLOWED_TOOLS = {t["name"] for t in load_tool_schemas()}
TOOL_INDEX = {t["name"]: t for t in load_tool_schemas()}


def validate_action(action: Dict[str, Any]) -> Optional[str]:
    """Return None if valid, else a rejection reason."""
    if not isinstance(action, dict):
        return "action is not an object"
    tool = action.get("tool")
    if tool not in ALLOWED_TOOLS:
        return f"tool not in allowlist: {tool}"
    args = action.get("args")
    if not isinstance(args, dict):
        return "args must be an object"
    schema = TOOL_INDEX[tool]["parameters"]
    for req in schema.get("required", []):
        if req not in args:
            return f"missing required arg: {req}"
    props = schema.get("properties", {})
    for key, value in args.items():
        spec = props.get(key)
        if spec is None:
            return f"unexpected arg: {key}"
        typ = spec.get("type")
        ok = {
            "string": isinstance(value, str),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
        }.get(typ, True)
        if not ok:
            return f"arg {key} has wrong type (want {typ})"
        if "enum" in spec and value not in spec["enum"]:
            return f"arg {key} not in enum {spec['enum']}"
    return None


class Orchestrator:
    def __init__(self, slm: Optional[SLMClient] = None):
        self.slm = slm or SLMClient()
        self.system_prompt = load_system_prompt()

    def mode(self) -> str:
        return self.slm.mode()

    # ------------------------------------------------------------------ #
    def plan_actions(self, events: List[Dict[str, Any]],
                     graph_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        slm_plan = self._try_slm(events, graph_payload)
        if slm_plan is not None:
            plan = slm_plan
            plan["commander_mode"] = "slm"
        else:
            plan = self._fallback_rules(events)
            plan["commander_mode"] = "fallback_rules"

        # Allowlist + schema validation (independent of which path produced it)
        clean_actions = []
        rejected = []
        for action in plan.get("actions", []):
            reason = validate_action(action)
            if reason is None:
                clean_actions.append(action)
            else:
                rejected.append({"action": action, "reason": reason})
        plan["actions"] = clean_actions
        if rejected:
            plan["rejected_actions"] = rejected
        plan.setdefault("plan_id", f"plan_{uuid.uuid4().hex[:10]}")
        plan.setdefault("brief", self._auto_brief(events, clean_actions))
        plan["generated_at"] = time.time()
        return plan

    # ------------------------------------------------------------------ #
    def _try_slm(self, events, graph_payload) -> Optional[Dict[str, Any]]:
        prompt = json.dumps({
            "telemetry_batch": events[-50:],
            "entity_graph": graph_payload or {},
            "instruction": "Correlate this batch. Emit ONLY the JSON plan object.",
        }, default=str)
        plan = self.slm.complete_json(prompt, system=self.system_prompt)
        if not plan or not isinstance(plan.get("actions"), list):
            return None
        return plan

    # ------------------------------------------------------------------ #
    def _fallback_rules(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        actions: List[Dict[str, Any]] = []
        stages: List[str] = []
        hosts, users, sessions = set(), set(), set()

        for e in events:
            sig = e.get("signal_type", "")
            sev = float(e.get("severity", 0.0))
            ent = e.get("entities", {}) or {}
            host = ent.get("host_id"); user = ent.get("user_id")
            sess = ent.get("session_id"); svc = ent.get("service_id")
            if host: hosts.add(host)
            if user: users.add(user)
            if sess: sessions.add(sess)

            if sig == "RANK1_CONDENSATION_DETECTED" and sev >= 0.7:
                actions.append({"tool": "drop_bec_cluster",
                                "args": {"cluster_id": ent.get("cluster_id", "CLUS_BEC_01"),
                                         "ttl_seconds": 3600},
                                "rationale": "Rank-1 condensation above 0.72 threshold"})
                stages.append("recon")

            elif sig == "TURBULENT_SESSION_REPLAY" and sev >= 0.5:
                actions.append({"tool": "revoke_turbulent_session",
                                "args": {"session_id": sess or "SESS_UNKNOWN",
                                         "user_id": user or "USER_UNKNOWN",
                                         "require_fido2": True},
                                "rationale": "Laminar->turbulent transition on replayed cookie"})
                stages.append("initial_access")
                # Pre-arm downstream ransomware traps for the affected user's hosts
                if host:
                    actions.append({"tool": "arm_page_curve_traps",
                                    "args": {"host_id": host, "density_level": "high"},
                                    "rationale": "Pre-arm Ring 3 before cookie replay pivots to ransomware"})

            elif sig == "INDIRECT_INJECTION_BLOCKED":
                actions.append({"tool": "quarantine_ai_document",
                                "args": {"doc_hash": ent.get("doc_hash", "sha256:unknown"),
                                         "agent_id": ent.get("agent_id", "agent_unknown")},
                                "rationale": "Indirect injection blocked by Bragg/Fiedler gates"})
                stages.append("execution")

            elif sig == "JAILBREAK_TRAJECTORY_DEFLECTED":
                actions.append({"tool": "clamp_lyapunov_steering",
                                "args": {"model_id": ent.get("agent_id", "agent_llm_local"),
                                         "stiffness_gain": 0.5},
                                "rationale": "Curvature cliff crossed; increase restoring stiffness"})
                stages.append("execution")

            elif sig == "PARITY_ENTROPY_COLLAPSE" and sev >= 0.9:
                actions.append({"tool": "arm_page_curve_traps",
                                "args": {"host_id": host or "HOST_UNKNOWN", "density_level": "high"},
                                "rationale": "Honey-block parity collapsed; reinforce trap density"})
                actions.append({"tool": "escalate_human_stepup",
                                "args": {"incident_id": f"inc_{uuid.uuid4().hex[:8]}",
                                         "severity": sev,
                                         "summary": "Ransomware parity collapse; PID terminated by reflex"},
                                "rationale": "Human in the loop for confirmed encryption attempt"})
                stages.append("impact")

            elif sig == "UNACCOUNTED_POWER_RESIDUAL":
                actions.append({"tool": "isolate_thermal_anomaly_host",
                                "args": {"host_id": host or "HOST_UNKNOWN", "dump_hardware_trace": True},
                                "rationale": "Sustained unattributed Joule dissipation"})
                stages.append("persistence")

            elif sig == "MISMATCH_SHIELD_SPLICED":
                actions.append({"tool": "deploy_muts_ebpf_shield",
                                "args": {"service_id": svc or "APP_SRV_07",
                                         "patch_profile_id": "bounds_check_v1"},
                                "rationale": "Zero-day mismatch observed; persist verified shield"})
                stages.append("lateral_movement")

            elif sig == "PERCOLATION_CUT_EXECUTED":
                stages.append("lateral_movement")

        # De-duplicate identical (tool, args-signature) proposals
        seen, unique_actions = set(), []
        for a in actions:
            key = (a["tool"], json.dumps(a["args"], sort_keys=True))
            if key not in seen:
                seen.add(key)
                unique_actions.append(a)

        stage = stages[-1] if stages else "recon"
        correlated = sorted(hosts | users | sessions)
        return {
            "plan_id": f"plan_{uuid.uuid4().hex[:10]}",
            "kill_chain_stage": stage,
            "correlated_entities": correlated[:50],
            "actions": unique_actions[:8],
        }

    # ------------------------------------------------------------------ #
    @staticmethod
    def _auto_brief(events, actions) -> str:
        sigs = [e.get("signal_type", "?") for e in events[-8:]]
        return (f"Correlated {len(events)} sanitized alerts ({', '.join(dict.fromkeys(sigs))}). "
                f"Proposed {len(actions)} allowlisted action(s); all require Plane-4 Governor approval "
                f"before touching infrastructure. Tier-0 assets untouched. Review the hash-chained "
                f"audit ledger for full trace.")
