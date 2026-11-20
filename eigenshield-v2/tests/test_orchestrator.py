import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commander.orchestrator import Orchestrator, validate_action


def _events():
    return [
        {"signal_type": "TURBULENT_SESSION_REPLAY", "severity": 0.74,
         "entities": {"session_id": "SESS_X", "user_id": "USER_019", "host_id": "HOST_042"}},
        {"signal_type": "PARITY_ENTROPY_COLLAPSE", "severity": 0.96,
         "entities": {"host_id": "HOST_042", "user_id": "USER_019"}},
    ]


def test_unknown_tool_rejected_by_validator():
    assert validate_action({"tool": "nuke_everything", "args": {}}) is not None
    assert validate_action({"tool": "drop_bec_cluster",
                            "args": {"cluster_id": "C", "ttl_seconds": 60}}) is None


def test_fallback_plan_is_allowlisted_and_shaped():
    orch = Orchestrator()
    orch.slm = type("Dead", (), {"mode": lambda self: "fallback_rules",
                                 "complete_json": lambda self, p, system="": None})()
    plan = orch.plan_actions(_events())
    assert plan["commander_mode"] == "fallback_rules"
    tools = [a["tool"] for a in plan["actions"]]
    assert "revoke_turbulent_session" in tools
    assert "arm_page_curve_traps" in tools
    for action in plan["actions"]:
        assert validate_action(action) is None
    assert plan["brief"]
