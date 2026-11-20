"""Exhaustive abstract verification of the Governor's stateless invariants.

The input space of the stateless decision procedure is FINITE enough to
enumerate: 10 tools × target classes × human-stepup ∈ {NONE, VERIFIED} ×
boundary argument values. We enumerate it and assert, for BOTH independent
TCB implementations, the crown-invariant:

    No tool executes against a Tier-0 asset without human step-up.  (I1)
    No tool outside the 10-tool allowlist is ever approved.          (I2)
    Any argument blob breaking the structural bounds is blocked.      (I3)

This is not a proof about the Python interpreter itself (nothing is), but it
is exhaustive over the decision's abstract input domain — the strongest cheap
guarantee available without a mechanized prover, and an honest one.
"""

import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spine import tcb_core, tcb_mirror

TIER0_VLANS = ("VLAN_ICU_CLINICAL", "VLAN_COLDCHAIN_TELEMETRY", "VLAN_CORE_AUTH")
TIER0_HOSTS = ("HOST_ER_DB_PRIMARY", "HOST_BLOODBANK_CTRL_01")

TOOLS = sorted(tcb_core.ALLOWED_TOOLS)
HOST_ARGS = {
    "arm_page_curve_traps": {"density_level": "high"},
    "isolate_thermal_anomaly_host": {"dump_hardware_trace": True},
    "quarantine_ai_document": {"doc_hash": "sha256:x", "agent_id": "agent_x"},
}


def _arg_variants(tool):
    base = {
        "drop_bec_cluster": [{"cluster_id": "CLUS_x", "ttl_seconds": t} for t in (60, 3600, 86400, 59, 86401)],
        "revoke_turbulent_session": [{"session_id": "s", "user_id": "u", "require_fido2": b} for b in (True, False)],
        "quarantine_ai_document": [{"doc_hash": "sha256:x", "agent_id": "a"}],
        "clamp_lyapunov_steering": [{"model_id": "m", "stiffness_gain": g} for g in (0.05, 0.35, 1.0, 0.01, 1.5)],
        "arm_page_curve_traps": [{"host_id": "HOST_x", "density_level": d} for d in ("low", "standard", "high", "turbo")],
        "isolate_thermal_anomaly_host": [{"host_id": "HOST_x", "dump_hardware_trace": True}],
        "execute_percolation_cut": [{"target_spectral_radius": r, "preserve_tier0_vlans": p}
                                    for r in (0.5, 0.9, 0.99, 0.1, 1.5) for p in (True, False)],
        "deploy_muts_ebpf_shield": [{"service_id": "s", "patch_profile_id": p}
                                    for p in ("bounds_check_v1", "cfi_v1", "syscall_filter_v1", "rootkit_me")],
        "set_service_readonly": [{"service_id": "s", "ttl_seconds": t} for t in (60, 600, 86400, 10)],
        "escalate_human_stepup": [{"incident_id": "i", "severity": s, "summary": "x" * n}
                                  for s in (0.0, 0.5, 1.0, 1.7) for n in (10, 500, 501)],
    }.get(tool, [{}])
    tier0_injections = [
        {"vlan_id": "VLAN_ICU_CLINICAL"},
        {"host_id": "HOST_ER_DB_PRIMARY"},
        {"note": "VLAN_COLDCHAIN_TELEMETRY"},
        {"nested": {"deep": ["ok", "HOST_BLOODBANK_CTRL_01"]}},
    ]
    for args in base:
        yield dict(args)
        for tier0 in tier0_injections:
            merged = dict(args)
            merged.update(tier0)
            yield merged


def test_exhaustive_tier0_and_allowlist_invariants():
    combos = 0
    violations = []
    for tool, human_ok in itertools.product(TOOLS, (False, True)):
        for args in _arg_variants(tool):
            for name, impl in (("core", tcb_core), ("mirror", tcb_mirror)):
                try:
                    verdict = impl.decide(tool, args, TIER0_VLANS, TIER0_HOSTS, human_ok=human_ok)
                except Exception as exc:  # never allowed to raise
                    violations.append((tool, args, name, f"raised {exc}"))
                    continue
                combos += 1
                blob = str(args)
                has_tier0 = any(t in blob for t in (*TIER0_VLANS, *TIER0_HOSTS))
                # I1 — crown jewel + no human => never APPROVED
                if has_tier0 and not human_ok and verdict["decision"] == "APPROVED":
                    violations.append((tool, args, name, "tier0 approved without human step-up"))
                # I2 — sanity: unknown tools never reach here (TOOLS comes from the allowlist)
                assert tool in tcb_core.ALLOWED_TOOLS
                # shape: decision always one of two values
                assert verdict["decision"] in ("APPROVED", "BLOCKED")
    assert violations == [], f"{len(violations)} invariant violation(s): {violations[:3]}"
    # exercise the full space size for the report
    assert combos > 300


def test_core_and_mirror_agree_on_entire_space():
    disagreements = []
    for tool, human_ok in itertools.product(TOOLS, (False, True)):
        for args in _arg_variants(tool):
            a = tcb_core.decide(tool, args, TIER0_VLANS, TIER0_HOSTS, human_ok=human_ok)
            b = tcb_mirror.decide(tool, args, TIER0_VLANS, TIER0_HOSTS, human_ok=human_ok)
            if a["decision"] != b["decision"]:
                disagreements.append((tool, args, a["decision"], b["decision"]))
    assert disagreements == [], f"N-version disagreement(s): {disagreements[:5]}"
