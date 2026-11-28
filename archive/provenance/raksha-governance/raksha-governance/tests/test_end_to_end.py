"""End-to-end: incident -> commander -> planner -> Governor -> dry-run.

Proves the whole chain stays inside its rails: every action dry-run,
every decision chained, a mixed adversarial bundle neutralised action by
action without blocking legitimate work, and the watchdog able to undo
its own damage.
"""
from __future__ import annotations

from raksha import (BudgetConfig, Governor, HashChainLedger,
                    hospital_fixture)
from raksha.commander import FallbackCommander, Incident, get_commander
from raksha.executor import DryRunExecutor
from raksha.planner import ContainmentPlanner
from tests.util import quarantine, sever, sign_into


def _run_pipeline():
    topo = hospital_fixture()
    incident = Incident(incident_id="inc-demo", seeds=("ws-11", "prn-01"))

    commander = get_commander()
    report = commander.propose(incident)

    plan = ContainmentPlanner(topo).plan_for_hosts(incident.seeds)

    governor = Governor(
        topology=topo,
        ledger=HashChainLedger(),
        budget_config=BudgetConfig(max_cuts=6),
    )
    outcomes = [governor.decide(raw) for raw in report.proposals]
    outcomes += [governor.decide(raw) for raw in plan.as_actions()]
    return topo, incident, commander, report, plan, outcomes, governor


def test_full_pipeline_every_decision_allowed_and_dry_run():
    _, _, commander, report, plan, outcomes, governor = _run_pipeline()
    assert commander.mode == "fallback_rules"
    assert len(outcomes) == len(report.proposals) + len(plan.cuts)
    for out in outcomes:
        assert out.allowed, (out.tool, out.reason)
    ok, bad = governor.ledger.verify()
    assert ok and bad is None
    assert len(governor.ledger) == len(outcomes)


def test_pipeline_containment_matches_seeds_and_plan():
    _, _, _, _, plan, outcomes, _ = _run_pipeline()
    tools = [o.tool for o in outcomes]
    assert tools.count("host.quarantine") == 2
    assert tools.count("edge.sever") == len(plan.cuts)


def test_executor_simulates_every_allowed_action():
    _, _, _, report, plan, _, _ = _run_pipeline()
    executor = DryRunExecutor()
    for raw in list(report.proposals) + list(plan.as_actions()):
        result = executor.execute(raw, status="ALLOW")
        assert result["dry_run"] is True


def test_adversarial_bundle_is_neutralised_action_by_action():
    """One command queue mixing legitimate work with five attacks. The
    Governor judges per action: drops the illegal, refuses the crown and
    floor violations, parks the unsigned Tier-0 cut, allows the benign."""
    import time as _time
    from raksha.fido2 import generate_signer

    topo = hospital_fixture()
    governor = Governor(topology=topo, ledger=HashChainLedger())
    priv, pub = generate_signer()
    governor.fido.register("on-call", pub)
    now = 1_700_000_000.0

    signed_crown = sign_into(quarantine("pump-01"), priv, "on-call", now)
    bundle = [
        {"tool": "os.kill", "params": {"pid": "4102"},
         "justification": "kill the malware", "requested_by": "commander"},
        {"tool": "vlan.isolate", "params": {"vlan": "icu-7"},
         "justification": "isolate the ICU", "requested_by": "commander"},
        signed_crown,                                   # crown lock, signed
        sever("e_ehr"),                                 # uptime floor
        {   # Tier-0 session termination, unsigned -> parked for sign-off
            "tool": "session.terminate",
            "params": {"host": "ehr-primary", "user": "svc-backup"},
            "justification": "evict attacker sessions",
            "requested_by": "commander",
        },
        quarantine("ws-11"),                            # legitimate
    ]
    results = [governor.decide(raw, current_uptime=1.0) for raw in bundle]
    statuses = [(o.status, o.reason) for o in results]
    assert statuses == [
        ("DENY", "UNKNOWN_TOOL"),
        ("DENY", "UNKNOWN_TOOL"),
        ("DENY", "CROWN_JEWEL_LOCK"),
        ("DENY", "UPTIME_FLOOR"),
        ("ESCALATE", "FIDO2_REQUIRED"),
        ("ALLOW", "ALLOWED_STANDARD"),
    ]
    ok, bad = governor.ledger.verify()
    assert ok and bad is None


def test_watchdog_undoes_the_pipelines_latest_change():
    _, _, _, _, _, _, governor = _run_pipeline()
    before = len(governor.reverts)
    assert before == 6          # 2 quarantines + 4 cuts, all revertible
    revert = governor.force_revert(0.98)
    assert revert.allowed
    assert revert.reason == "WATCHDOG_FORCE_REVERT"
    assert revert.tool == "edge.restore"        # the most recent change
    assert len(governor.reverts) == before - 1


def test_no_model_still_reaches_a_safe_outcome():
    _, _, commander, report, _, outcomes, _ = _run_pipeline()
    assert commander.mode == "fallback_rules"
    assert report.commander_mode == "fallback_rules"
    assert all(o.allowed for o in outcomes)
