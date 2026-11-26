"""Part 4 -- dry-run executor: simulated, gated, and incapable of I/O."""
from __future__ import annotations

import pytest

from raksha.executor import DRY_RUN, DryRunExecutor
from tests.util import quarantine, sever

EXECUTOR = DryRunExecutor()


def test_every_allow_is_simulated():
    result = EXECUTOR.execute(quarantine("ws-11"), status="ALLOW")
    assert result["dry_run"] is True
    assert result["effect"] == "simulated"
    assert "no packet sent" in result["note"]


def test_all_ten_tools_have_dry_run_sentences():
    from raksha.tools import TOOL_REGISTRY
    envelopes = {
        "host.quarantine": {"host": "ws-11"},
        "host.release": {"host": "ws-11"},
        "vlan.move": {"host": "ws-11", "to_vlan": "remediation-9"},
        "edge.sever": {"edge": "e_ws"},
        "edge.restore": {"edge": "e_ws"},
        "session.terminate": {"host": "ws-11", "user": "svc-backup"},
        "creds.rotate": {"identity": "svc-print"},
        "firewall.rule.add": {"edge": "e_ws"},
        "firewall.rule.remove": {"rule_id": "raksha-abcdef123456"},
        "snapshot.capture": {"host": "ws-11"},
    }
    for name, spec in TOOL_REGISTRY.items():
        raw = {"tool": name, "params": envelopes[name],
               "justification": "test", "requested_by": "test"}
        result = EXECUTOR.execute(raw, status="ALLOW")
        assert result["dry_run"] is True
        assert "simulated" in result["would"]


def test_executor_refuses_non_allow_statuses():
    with pytest.raises(ValueError):
        EXECUTOR.execute(sever("e_ws"), status="DENY")
    with pytest.raises(ValueError):
        EXECUTOR.execute(sever("e_ws"), status="ESCALATE")


def test_executor_module_cannot_reach_a_machine():
    import raksha.executor as module
    for banned in ("os", "subprocess", "socket", "requests", "urllib"):
        assert not hasattr(module, banned)
    assert DRY_RUN is True
