"""TCB-mirror — independent N-version re-derivation of the stateless decision.

Written against the SAME specification as fortress/tcb_core.py but with
deliberately different structure, data tables and control flow: table-driven
predicate folding instead of sequential guards, count-based size estimation
instead of json round-trip, recursive descent with an explicit depth guard
instead of an explicit stack. A defect class that survives both lineages is
vastly less likely than one in either alone — and any disagreement fails
CLOSED at the Governor.

Imports: json only (for canonical size estimate) + nothing else of substance.
"""

import json

_MAX_SIZE = 8192
_MAX_DEPTH = 32
_MAX_NODES = 512
_MAX_TEXT = 2048

_TOOLS = frozenset({
    "drop_bec_cluster", "revoke_turbulent_session", "quarantine_ai_document",
    "clamp_lyapunov_steering", "arm_page_curve_traps", "isolate_thermal_anomaly_host",
    "execute_percolation_cut", "deploy_muts_ebpf_shield", "set_service_readonly",
    "escalate_human_stepup",
})

_NEED = {
    "drop_bec_cluster": ["cluster_id", "ttl_seconds"],
    "revoke_turbulent_session": ["session_id", "user_id", "require_fido2"],
    "quarantine_ai_document": ["doc_hash", "agent_id"],
    "clamp_lyapunov_steering": ["model_id", "stiffness_gain"],
    "arm_page_curve_traps": ["host_id", "density_level"],
    "isolate_thermal_anomaly_host": ["host_id", "dump_hardware_trace"],
    "execute_percolation_cut": ["target_spectral_radius", "preserve_tier0_vlans"],
    "deploy_muts_ebpf_shield": ["service_id", "patch_profile_id"],
    "set_service_readonly": ["service_id", "ttl_seconds"],
    "escalate_human_stepup": ["incident_id", "severity", "summary"],
}

_CHOICES = {"density_level": {"low", "standard", "high"},
            "patch_profile_id": {"bounds_check_v1", "cfi_v1", "syscall_filter_v1"}}
_RANGE = {"stiffness_gain": (0.05, 1.0), "target_spectral_radius": (0.5, 0.99),
          "severity": (0.0, 1.0), "ttl_seconds": (60, 86400)}
_FLAGS = {"require_fido2", "dump_hardware_trace", "preserve_tier0_vlans"}


def _size(value):
    try:
        return len(json.dumps(value, default=str).encode())
    except Exception:
        return _MAX_SIZE + 1


def _depth_nodes(value):
    """Recursive descent — different shape from tcb_core's stack machine on purpose."""
    counter = [0]

    def visit(node, depth):
        counter[0] += 1
        if depth > _MAX_DEPTH or counter[0] > _MAX_NODES:
            return False
        if isinstance(node, str):
            if len(node) > _MAX_TEXT:
                return False
            return True
        if isinstance(node, dict):
            for k, v in node.items():
                if not isinstance(k, str) or len(k) > 64:
                    return False
                if not visit(v, depth + 1):
                    return False
            return True
        if isinstance(node, (list, tuple)):
            return all(visit(v, depth + 1) for v in node)
        return isinstance(node, (bool, int, float)) or node is None

    return visit(value, 0), counter[0]


def _hits_tier0(value, protected):
    if isinstance(value, str):
        return [value] if value in protected else []
    found = []
    if isinstance(value, dict):
        for k, v in value.items():
            found += _hits_tier0(k, protected)
            found += _hits_tier0(v, protected)
    elif isinstance(value, (list, tuple)):
        for v in value:
            found += _hits_tier0(v, protected)
    return found


def _ok_types(args):
    for k, v in args.items():
        if k in _FLAGS and not isinstance(v, bool):
            return f"arg {k} must be boolean"
        if k in _RANGE:
            lo, hi = _RANGE[k]
            if k == "ttl_seconds":
                if not (isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi):
                    return f"arg {k} out of range [{lo}, {hi}]"
            else:
                if not (isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= float(v) <= hi):
                    return f"arg {k} out of range [{lo}, {hi}]"
        if k in _CHOICES and v not in _CHOICES[k]:
            return f"arg {k} not in {_CHOICES[k]}"
    if "summary" in args and isinstance(args["summary"], str) and len(args["summary"]) > 500:
        return "summary exceeds 500 chars"
    return None


def decide(tool, args, tier0_vlans, tier0_hosts, human_ok=False):
    """Fold a fixed checklist. Returns the same shape as tcb_core.decide."""
    if not isinstance(tool, str) or tool not in _TOOLS:
        return {"decision": "BLOCKED", "reasons": [f"tool not in 10-tool allowlist: {tool}"]}
    if not isinstance(args, dict):
        return {"decision": "BLOCKED", "reasons": ["args must be an object"]}

    checks = []

    def check(name, ok):
        checks.append((name, bool(ok)))

    check("args-size", _size(args) <= _MAX_SIZE)
    bounded, _nodes = _depth_nodes(args)
    check("args-structure", bounded)
    missing = [r for r in _NEED[tool] if r not in args]
    check("required-args", not missing)
    type_err = _ok_types(args)
    check("types-and-enums", type_err is None)
    check("tier0-flag",
          not (tool == "execute_percolation_cut" and args.get("preserve_tier0_vlans") is not True))
    protected = set(tier0_vlans or ()) | set(tier0_hosts or ())
    hits = sorted(set(_hits_tier0(args, protected)))
    check("crown-jewel-lock", human_ok or not hits)

    failed = [name for name, ok in checks if not ok]
    if failed:
        return {"decision": "BLOCKED", "reasons": failed}
    return {"decision": "APPROVED", "reasons": ["stateless invariants satisfied"]}
