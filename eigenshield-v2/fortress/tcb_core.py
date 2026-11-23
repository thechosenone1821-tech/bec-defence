"""TCB-core — primary decision procedure. Pure Python standard library ONLY.

This module is part of the Trusted Computing Base. It must stay auditable in
under ~15 minutes by a competent engineer. Hard rules for contributors:

* imports: json, hashlib, hmac, re — nothing else
* no recursion (explicit stacks only), no unbounded loops over untrusted input
* no YAML, no files, no network, no clock dependence for correctness
* never raises: always returns a decision dict

Semantics deliberately mirror governor/policy_engine.py for the STATELESS
invariants only (tool allowlist, args shape, presence/type/enum checks, the
Tier-0 crown-jewel lock). Stateful invariants (sliding blast-radius budgets,
uptime SLO floors) stay in the Governor; the Governor fails closed if this
module and its own check disagree.
"""

import hashlib
import hmac
import json

MAX_ARGS_BYTES = 8192          # an argument blob bigger than this is rejected
MAX_NODES = 512                # total JSON values walked
MAX_DEPTH = 32                 # nesting depth
MAX_STRING = 2048              # any single string value
MAX_KEY = 64                   # any single object key

ALLOWED_TOOLS = frozenset([
    "drop_bec_cluster",
    "revoke_turbulent_session",
    "quarantine_ai_document",
    "clamp_lyapunov_steering",
    "arm_page_curve_traps",
    "isolate_thermal_anomaly_host",
    "execute_percolation_cut",
    "deploy_muts_ebpf_shield",
    "set_service_readonly",
    "escalate_human_stepup",
])

REQUIRED_ARGS = {
    "drop_bec_cluster": ("cluster_id", "ttl_seconds"),
    "revoke_turbulent_session": ("session_id", "user_id", "require_fido2"),
    "quarantine_ai_document": ("doc_hash", "agent_id"),
    "clamp_lyapunov_steering": ("model_id", "stiffness_gain"),
    "arm_page_curve_traps": ("host_id", "density_level"),
    "isolate_thermal_anomaly_host": ("host_id", "dump_hardware_trace"),
    "execute_percolation_cut": ("target_spectral_radius", "preserve_tier0_vlans"),
    "deploy_muts_ebpf_shield": ("service_id", "patch_profile_id"),
    "set_service_readonly": ("service_id", "ttl_seconds"),
    "escalate_human_stepup": ("incident_id", "severity", "summary"),
}

_ENUM_ARGS = {
    "density_level": ("low", "standard", "high"),
    "patch_profile_id": ("bounds_check_v1", "cfi_v1", "syscall_filter_v1"),
}

_NUMBER_ARGS = {
    "stiffness_gain": (0.05, 1.0),
    "target_spectral_radius": (0.5, 0.99),
    "severity": (0.0, 1.0),
}

_BOOL_ARGS = ("require_fido2", "dump_hardware_trace", "preserve_tier0_vlans")
_INT_ARGS = ("ttl_seconds",)


def _walk_errors(value):
    """Iterative structural validation. Returns a list of reason strings."""
    errors = []
    stack = [(value, 0)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > MAX_NODES:
            errors.append("args exceed node bound (512)")
            return errors
        if depth > MAX_DEPTH:
            errors.append("args exceed depth bound (32)")
            return errors
        if isinstance(current, str):
            if len(current) > MAX_STRING:
                errors.append("string value exceeds 2048 chars")
        elif isinstance(current, dict):
            for k, v in current.items():
                if not isinstance(k, str) or len(k) > MAX_KEY:
                    errors.append("object key invalid or too long")
                stack.append((v, depth + 1))
        elif isinstance(current, (list, tuple)):
            for v in current:
                stack.append((v, depth + 1))
        elif isinstance(current, bool) or current is None:
            pass
        elif isinstance(current, (int, float)):
            pass
        else:
            errors.append(f"unsupported JSON value type: {type(current).__name__}")
    return errors


def _strings(value):
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, str):
            yield current
        elif isinstance(current, dict):
            stack.extend(current.keys())
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _type_errors(tool, args):
    errors = []
    for key, value in args.items():
        if key in _BOOL_ARGS and not isinstance(value, bool):
            errors.append(f"arg {key} must be boolean")
        if key in _INT_ARGS and not _is_int(value):
            errors.append(f"arg {key} must be integer")
        if key in _NUMBER_ARGS:
            if not _is_num(value):
                errors.append(f"arg {key} must be a number")
            else:
                lo, hi = _NUMBER_ARGS[key]
                if not (lo <= float(value) <= hi):
                    errors.append(f"arg {key} out of range [{lo}, {hi}]")
        if key in _ENUM_ARGS and value not in _ENUM_ARGS[key]:
            errors.append(f"arg {key} not in {_ENUM_ARGS[key]}")
    if tool == "execute_percolation_cut" and args.get("preserve_tier0_vlans") is not True:
        errors.append("execute_percolation_cut requires preserve_tier0_vlans=true")
    if tool == "escalate_human_stepup":
        sev = args.get("severity")
        if _is_num(sev) and not (0.0 <= float(sev) <= 1.0):
            errors.append("severity out of [0,1]")
        summary = args.get("summary")
        if isinstance(summary, str) and len(summary) > 500:
            errors.append("summary exceeds 500 chars")
    if tool in ("drop_bec_cluster", "set_service_readonly") and "ttl_seconds" in args:
        if _is_int(args["ttl_seconds"]) and not (60 <= args["ttl_seconds"] <= 86400):
            errors.append("ttl_seconds out of [60, 86400]")
    if tool == "clamp_lyapunov_steering":
        gain = args.get("stiffness_gain")
        if _is_num(gain) and not (0.05 <= float(gain) <= 1.0):
            errors.append("stiffness_gain out of [0.05, 1.0]")
    return errors


def decide(tool, args, tier0_vlans, tier0_hosts, human_ok=False):
    """Decide the stateless invariants for one action.

    Returns {"decision": "APPROVED"|"BLOCKED", "reasons": [str, ...]}.
    Never raises. tier0_* are iterables of exact-match protected identifiers.
    """
    reasons = []
    tier0_vlans = frozenset(tier0_vlans or ())
    tier0_hosts = frozenset(tier0_hosts or ())

    if not isinstance(tool, str) or tool not in ALLOWED_TOOLS:
        reasons.append(f"tool not in 10-tool allowlist: {tool}")
    if not isinstance(args, dict):
        return {"decision": "BLOCKED", "reasons": reasons + ["args must be an object"]}

    try:
        blob = json.dumps(args, separators=(",", ":"), default=str)
        if len(blob.encode("utf-8")) > MAX_ARGS_BYTES:
            reasons.append("args exceed 8 KB bound")
    except (TypeError, ValueError):
        reasons.append("args not JSON-serialisable")

    reasons.extend(_walk_errors(args))
    if isinstance(tool, str) and tool in ALLOWED_TOOLS:
        for req in REQUIRED_ARGS[tool]:
            if req not in args:
                reasons.append(f"missing required arg: {req}")
        reasons.extend(_type_errors(tool, args))

    hits = sorted({s for s in _strings(args)
                   if s in tier0_vlans or s in tier0_hosts})
    if hits and not human_ok:
        reasons.append(f"tier-0 protected asset(s) referenced: {hits}")

    if reasons:
        return {"decision": "BLOCKED", "reasons": reasons}
    return {"decision": "APPROVED", "reasons": ["stateless invariants satisfied"]}
