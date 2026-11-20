"""SPINE — Deterministic Hard Safety Governor (ZERO AI).

Five deterministic invariants guard every Commander-proposed action:

1. Strict 10-tool schema lock            (malformed/unlisted tools dropped)
2. Immutable Crown-Jewel lock            (tier_0_protected: AI can NEVER isolate)
3. Blast-radius budgeter                 (max cuts / quarantines / splices per 5 min)
4. Cryptographic human step-up           (Tier-0 override requires FIDO2 sign-off)
5. Uptime auto-rollback watchdog         (see rollback_watchdog.py)

Every decision is appended to the SHA-256 hash-chained audit ledger.
"""

from __future__ import annotations

import json
import os
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

import yaml

_HERE = os.path.dirname(__file__)
_DEFAULT_TOOL_SCHEMAS = os.path.join(_HERE, "tool_schemas.json")

# Tools that disrupt hosts/VLANs and therefore arm the blast-radius budgets.
_BUDGET_CATEGORY = {
    "execute_percolation_cut": "vlan_cuts",
    "isolate_thermal_anomaly_host": "host_quarantines",
    "set_service_readonly": "host_quarantines",
    "deploy_muts_ebpf_shield": "ebpf_splices",
}

_BUDGET_LIMIT_KEY = {
    "vlan_cuts": "max_vlan_cuts_per_5min",
    "host_quarantines": "max_host_quarantines_per_5min",
    "ebpf_splices": "max_ebpf_splices_per_5min",
}

_HORIZON_SEC = 300  # 5 minutes


def _load_allowed_tools(path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    with open(path or _DEFAULT_TOOL_SCHEMAS) as f:
        return {t["name"]: t for t in json.load(f)}


class PolicyEngine:
    def __init__(self, policy_path: str, ledger: Optional[Any] = None,
                 tool_schemas_path: Optional[str] = None):
        with open(policy_path) as f:
            self.policy = yaml.safe_load(f)
        self.tools = _load_allowed_tools(tool_schemas_path)
        self.ledger = ledger
        self.tier0_vlans = set(self.policy.get("tier_0_protected", {}).get("vlans", []))
        self.tier0_hosts = set(self.policy.get("tier_0_protected", {}).get("hosts", []))
        self.limits = self.policy.get("blast_radius_limits", {})
        self.min_uptime = float(self.limits.get("min_preserved_graph_uptime_pct", 90.0))
        self._budget_window: Dict[str, Deque[float]] = {k: deque() for k in _BUDGET_CATEGORY.values()}
        self._frozen_until: Dict[str, float] = {}

    # ------------------------------------------------------------------ #
    def _tier0_targets_in_args(self, args: Any) -> List[str]:
        hits: List[str] = []

        def walk(value: Any) -> None:
            if isinstance(value, str):
                if value in self.tier0_vlans or value in self.tier0_hosts:
                    hits.append(value)
            elif isinstance(value, dict):
                for v in value.values():
                    walk(v)
            elif isinstance(value, list):
                for v in value:
                    walk(v)

        walk(args)
        return hits

    def _budget_ok(self, category: str) -> bool:
        now = time.time()
        if self._frozen_until.get(category, 0) > now:
            return False
        window = self._budget_window[category]
        while window and now - window[0] > _HORIZON_SEC:
            window.popleft()
        limit = int(self.limits.get(_BUDGET_LIMIT_KEY[category], 999))
        return len(window) < limit

    def _record_budget(self, category: str) -> None:
        self._budget_window[category].append(time.time())

    # ------------------------------------------------------------------ #
    def evaluate(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        reasons: List[str] = []
        decision = "APPROVED"

        # FORTRESS tripwire: when frozen, the AI path is fully closed. Organs
        # keep defending; only a human step-up reopens decisions.
        try:
            from spine import tripwire
            _tw = tripwire.shared()
            if _tw.is_frozen():
                return {"decision": "BLOCKED", "tool": action.get("tool") if isinstance(action, dict) else None,
                        "args": action.get("args") if isinstance(action, dict) else None,
                        "reasons": [f"FORTRESS tripwire frozen — {_tw.status()['frozen_reason']}; human step-up required"],
                        "autonomy_mode": self.policy.get("autonomy_mode", "GUARDED_AUTO"),
                        "fortress_tcb": "frozen", "ts": time.time()}
        except ImportError:
            pass

        tool = action.get("tool") if isinstance(action, dict) else None
        args = action.get("args", {}) if isinstance(action, dict) else {}

        # --- Invariant 1: schema lock -----------------------------------
        if tool not in self.tools:
            reasons.append(f"tool not in 10-tool allowlist: {tool}")
            decision = "BLOCKED"
        else:
            schema = self.tools[tool]["parameters"]
            for req in schema.get("required", []):
                if req not in args:
                    reasons.append(f"missing required arg: {req}")
                    decision = "BLOCKED"
            for key, value in args.items():
                spec = schema.get("properties", {}).get(key)
                if spec is None:
                    reasons.append(f"unexpected arg: {key}")
                    decision = "BLOCKED"
                    continue
                if spec.get("type") == "boolean" and not isinstance(value, bool):
                    reasons.append(f"arg {key} must be boolean")
                    decision = "BLOCKED"
            if tool == "execute_percolation_cut":
                if args.get("preserve_tier0_vlans") is not True:
                    reasons.append("execute_percolation_cut requires preserve_tier0_vlans=true")
                    decision = "BLOCKED"

        # --- Invariant 2 + 4: crown jewel + human step-up ---------------
        human_ok = str(context.get("human_stepup", "")).upper() in {"VERIFIED", "TRUE", "APPROVED"}
        tier0_hits = self._tier0_targets_in_args(args) if isinstance(args, dict) else []
        if tier0_hits and not human_ok:
            reasons.append(f"tier-0 protected asset(s) referenced: {sorted(set(tier0_hits))}; "
                           f"AI cannot isolate/cut crown jewels — human FIDO2 step-up required")
            decision = "BLOCKED"

        # --- Invariant 3: blast-radius budget ----------------------------
        category = _BUDGET_CATEGORY.get(tool or "", None)
        if category and decision == "APPROVED":
            if not self._budget_ok(category):
                reasons.append(f"blast-radius budget exhausted for {category} "
                               f"({self.limits.get(_BUDGET_LIMIT_KEY[category])} per 5 min); "
                               f"autonomy frozen — human escalation required")
                self._frozen_until[category] = time.time() + _HORIZON_SEC
                decision = "ESCALATE"

        uptime_estimate = context.get("expected_preserved_uptime_pct")
        if uptime_estimate is not None and float(uptime_estimate) < self.min_uptime:
            reasons.append(f"expected preserved uptime {uptime_estimate}% below floor {self.min_uptime}%")
            decision = "BLOCKED"

        # FORTRESS: independent N-version re-derivation (pure stdlib TCB).
        # Any disagreement with the in-engine verdict fails CLOSED.
        try:
            from spine import tcb_core, tcb_mirror
            human_ok = str(context.get("human_stepup", "")).upper() in {"VERIFIED", "TRUE", "APPROVED"}
            core = tcb_core.decide(tool or "", args if isinstance(args, dict) else {},
                                   self.tier0_vlans, self.tier0_hosts, human_ok=human_ok)
            mirror = tcb_mirror.decide(tool or "", args if isinstance(args, dict) else {},
                                       self.tier0_vlans, self.tier0_hosts, human_ok=human_ok)
            if core["decision"] != mirror["decision"]:
                reasons.append(f"FORTRESS TCB disagreement (core={core['decision']} mirror={mirror['decision']}) — fail closed")
                decision = "BLOCKED"
                result_tcb_note = "tcb_mismatch"
                try:
                    from spine import tripwire
                    tripwire.shared().record("tcb_mismatch")
                except ImportError:
                    pass
            elif decision == "APPROVED" and core["decision"] == "BLOCKED":
                reasons.append("FORTRESS independent TCB rejected action: " + "; ".join(core["reasons"]))
                decision = "BLOCKED"
                result_tcb_note = "tcb_override"
            else:
                result_tcb_note = "ok"
        except ImportError:
            result_tcb_note = "fortress_absent"
        except Exception as exc:
            reasons.append(f"FORTRESS TCB error — fail closed: {exc}")
            decision = "BLOCKED"
            result_tcb_note = "tcb_error_failclosed"

        result = {
            "decision": decision,
            "tool": tool,
            "args": args,
            "reasons": reasons or ["all invariants satisfied"],
            "autonomy_mode": self.policy.get("autonomy_mode", "GUARDED_AUTO"),
            "fortress_tcb": result_tcb_note,
            "ts": time.time(),
        }
        if decision == "BLOCKED":
            try:
                from spine import tripwire
                tripwire.shared().record("blocked")
            except ImportError:
                pass
        if decision == "APPROVED" and category:
            self._record_budget(category)
        if self.ledger is not None:
            entry = self.ledger.append("governor_decision", result)
            result["ledger_seq"] = entry["seq"]
            result["ledger_hash"] = entry["hash"]
        return result

    # ------------------------------------------------------------------ #
    def evaluate_plan(self, actions: List[Dict[str, Any]],
                      context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [self.evaluate(a, context) for a in actions]

    def status(self) -> Dict[str, Any]:
        now = time.time()
        integrity = "UNVERIFIED"
        try:
            from spine.boot_manifest import verify_manifest
            import os
            here = os.path.dirname(os.path.abspath(__file__))
            for candidate in (os.path.join(here, "config", "manifest.json"),        # raksha spine layout
                              os.path.join(os.path.dirname(here), "config", "manifest.json")):  # flat layout
                if os.path.exists(candidate):
                    integrity = "ok" if verify_manifest(candidate)["ok"] else "TAMPERED"
                    break
        except Exception:
            integrity = "unknown"
        return {
            "config_integrity": integrity,
            "autonomy_mode": self.policy.get("autonomy_mode"),
            "frozen_categories": {k: round(v - now, 1) for k, v in self._frozen_until.items() if v > now},
            "budget_window_usage": {k: len(v) for k, v in self._budget_window.items()},
            "min_preserved_graph_uptime_pct": self.min_uptime,
        }
