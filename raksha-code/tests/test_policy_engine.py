import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spine.governor import PolicyEngine

POLICY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "spine", "config", "policy.yaml")


@pytest.fixture()
def governor(tmp_path):
    from spine.ledger import AuditLedger
    return PolicyEngine(POLICY, ledger=AuditLedger(str(tmp_path / "audit.jsonl")))


def test_simple_allowlisted_action_approved(governor):
    d = governor.evaluate({"tool": "drop_bec_cluster",
                           "args": {"cluster_id": "CLUS_1", "ttl_seconds": 600}})
    assert d["decision"] == "APPROVED"


def test_unknown_tool_blocked(governor):
    d = governor.evaluate({"tool": "rm_rf_slash", "args": {}})
    assert d["decision"] == "BLOCKED"


def test_tier0_host_isolation_hard_blocked(governor):
    d = governor.evaluate({"tool": "isolate_thermal_anomaly_host",
                           "args": {"host_id": "HOST_ER_DB_PRIMARY",
                                    "dump_hardware_trace": True}})
    assert d["decision"] == "BLOCKED"
    assert any("tier-0" in r for r in d["reasons"])


def test_tier0_allowed_only_with_human_stepup(governor):
    d = governor.evaluate({"tool": "isolate_thermal_anomaly_host",
                           "args": {"host_id": "HOST_ER_DB_PRIMARY",
                                    "dump_hardware_trace": True}},
                          context={"human_stepup": "VERIFIED"})
    assert d["decision"] == "APPROVED"


def test_percolation_cut_requires_tier0_preservation_flag(governor):
    d = governor.evaluate({"tool": "execute_percolation_cut",
                           "args": {"target_spectral_radius": 0.9,
                                    "preserve_tier0_vlans": False}})
    assert d["decision"] == "BLOCKED"


def test_ebpf_splice_budget_freezes_autonomy(governor):
    for i in range(4):
        d = governor.evaluate({"tool": "deploy_muts_ebpf_shield",
                               "args": {"service_id": f"APP_{i}",
                                        "patch_profile_id": "bounds_check_v1"}})
        assert d["decision"] == "APPROVED"
    d = governor.evaluate({"tool": "deploy_muts_ebpf_shield",
                           "args": {"service_id": "APP_5",
                                    "patch_profile_id": "bounds_check_v1"}})
    assert d["decision"] == "ESCALATE"
