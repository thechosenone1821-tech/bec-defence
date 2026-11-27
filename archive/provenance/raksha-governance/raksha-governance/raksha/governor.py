"""The Governor: deterministic safety gate between a proposal and any action.

This is the single most important component in RAKSHA, and it contains
deterministic. Every arrow into it is a place an action can stop.

The decision pipeline, in order (an action that fails any step stops there):

  1. SCHEMA LOCK        parse against the 10-tool allowlist, exact schema,
                        targets must exist. Drop, never repair.
  2. TWIN AGREEMENT     TwinA and TwinB independently evaluate the pure
                        policy (crown lock, uptime floor, Tier-0 step-up
                        requirement). Disagreement => refusal.
  3. BLAST-RADIUS BUDGET  max cuts / quarantines / splices per rolling
                        5-minute window. Runtime state, Governor-owned.
  4. FIDO2 STEP-UP      if the policy demands sign-off for a Tier-0 action,
                        verify the cryptographic assertion (fresh, bound to
                        this action digest, counter strictly increasing).
  5. ALLOW + REGISTER   reserve budget, register the inverse action with
                        the watchdog so the change stays revertible.

Fail-closed rule: any internal error anywhere in this pipeline produces
DENY/INTERNAL_GUARD_FAILURE. The Governor never allows on error.

Every terminal outcome is appended to the evidence ledger before the caller
sees it. The ledger is the memory of the hospital: what was proposed, what
was decided, why, and who signed it.

Why a separate part must never bypass this module: the Commander is an LLM.
It can be prompt-injected, confused, or simply wrong. The Governor is a few
hundred lines of deterministic Python a hospital IT generalist can read. If
you find yourself writing "temporarily skip the governor here", stop -- that
is the one change that makes the whole product unsafe.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .budgets import BudgetConfig, BudgetWindow
from .decisions import (
    ALLOW,
    DENY,
    Decision,
    ESCALATE,
    EMPTY_METADATA,
    decisions_agree,
    explain,
)
from .fido2 import Fido2Registry
from .fixtures import Topology, hospital_fixture
from .ledger import HashChainLedger
from .tools import Action, TOOL_REGISTRY, parse_action
from .tcb import DEFAULT_TWINS
from .watchdog import RevertRegistry


@dataclass(frozen=True)
class GovernorOutcome:
    decision: Decision
    ledger_seq: int
    action_digest: str
    tool: str

    @property
    def allowed(self) -> bool:
        return self.decision.status == ALLOW

    @property
    def status(self) -> str:
        return self.decision.status

    @property
    def reason(self) -> str:
        return self.decision.reason

    def __str__(self) -> str:
        return (
            f"#{self.ledger_seq} {self.status}/{self.reason} tool={self.tool} "
            f"digest={self.action_digest[:12] or '-'}"
        )


class Governor:
    """Compose the invariants. Own all runtime state. Append every outcome."""

    VERSION = "1.0.0"

    def __init__(
        self,
        topology: Optional[Topology] = None,
        ledger: Optional[HashChainLedger] = None,
        budget_config: Optional[BudgetConfig] = None,
        clock=time.time,
        fido2_registry: Optional[Fido2Registry] = None,
        twins=None,
    ) -> None:
        self.topo = topology if topology is not None else hospital_fixture()
        self.ledger = ledger if ledger is not None else HashChainLedger()
        self.clock = clock
        self.floor = self.topo.critical_floor
        self.budgets = BudgetWindow(
            budget_config if budget_config is not None else BudgetConfig(),
            clock,
        )
        self.fido = fido2_registry if fido2_registry is not None else Fido2Registry()
        self.twin_a, self.twin_b = twins if twins is not None else DEFAULT_TWINS
        self.reverts = RevertRegistry()

    # ------------------------------------------------------------------
    # main entry point
    # ------------------------------------------------------------------
    def decide(self, raw_action: dict, current_uptime: float = 1.0) -> GovernorOutcome:
        """Evaluate one raw action. This is the only door to the executor."""
        now = self.clock()
        digest = ""
        tool = "-"
        try:
            # -- 1. schema lock: drop, never repair ------------------------
            action, reason, detail = parse_action(raw_action, self.topo)
            if action is None:
                final = Decision(
                    DENY, reason, EMPTY_METADATA, explain(reason, detail)
                )
            else:
                digest, tool = action.digest, action.tool
                final = self._evaluate_with_state(action, current_uptime, now)
        except Exception as exc:  # fail-closed: on any error, the answer is no
            final = Decision(
                DENY,
                "INTERNAL_GUARD_FAILURE",
                EMPTY_METADATA,
                explain("INTERNAL_GUARD_FAILURE", f"{type(exc).__name__}: {exc}"),
            )
        seq = self.ledger.append(
            ts=now,
            actor="governor",
            tool=tool,
            action_digest=digest,
            status=final.status,
            reason=final.reason,
            detail=final.explanation,
        ).seq
        return GovernorOutcome(final, seq, digest, tool)

    # ------------------------------------------------------------------
    # steps 2-5 (pure policy via twins, then Governor-owned state)
    # ------------------------------------------------------------------
    def _evaluate_with_state(
        self, action: Action, current_uptime: float, now: float
    ) -> Decision:
        # -- 2. TCB twins must agree -----------------------------------
        va = self.twin_a.evaluate(action, self.topo, current_uptime, self.floor)
        vb = self.twin_b.evaluate(action, self.topo, current_uptime, self.floor)
        if not decisions_agree(va, vb):
            return Decision(
                DENY,
                "TCB_DISAGREEMENT",
                va.metadata,
                explain(
                    "TCB_DISAGREEMENT",
                    f"{self.twin_a.name} said {va.reason}, "
                    f"{self.twin_b.name} said {vb.reason}",
                ),
            )

        spec = TOOL_REGISTRY[action.tool]

        # -- 3. blast-radius budget (runtime state, Governor-owned) -----
        budget_ok, used = self.budgets.check(spec.bucket)
        if va.status == DENY:
            return va  # crown lock / uptime floor: policy refusal wins first
        if not budget_ok:
            return Decision(
                DENY,
                "BUDGET_EXCEEDED",
                va.metadata,
                explain(
                    "BUDGET_EXCEEDED",
                    f"{used}/{self.budgets.cap_for(spec.bucket)} "
                    f"{spec.bucket} actions already in the 5-minute window",
                ),
            )

        # -- 4. FIDO2 step-up for Tier-0 (the twin demanded sign-off) ---
        if va.status == ESCALATE:
            final = self._resolve_tier0(action, va.metadata, now)
        else:
            final = va  # ALLOW per policy

        # -- 5. commit state for any final ALLOW -----------------------
        if final.status == ALLOW:
            self.budgets.reserve(spec.bucket)
            inverse = self._build_inverse(action)
            if inverse is not None:
                self.reverts.record(now, action.digest, action.tool, inverse)
        return final

    def _resolve_tier0(
        self, action: Action, metadata: tuple, now: float
    ) -> Decision:
        assertion = action.assertion
        if assertion is None:
            return Decision(
                ESCALATE,
                "FIDO2_REQUIRED",
                metadata,
                explain(
                    "FIDO2_REQUIRED",
                    "no assertion supplied; the action is parked until an "
                    "on-call human signs this exact action digest",
                ),
            )
        result = self.fido.verify(action.digest, assertion, now)
        if result.ok:
            return Decision(
                ALLOW,
                "ALLOWED_WITH_TIER0_OVERRIDE",
                metadata,
                explain(
                    "ALLOWED_WITH_TIER0_OVERRIDE",
                    f"signed by {assertion['signer']}, counter {assertion['counter']}",
                ),
            )
        return Decision(
            DENY, result.reason, metadata, explain(result.reason, result.detail)
        )

    # ------------------------------------------------------------------
    # watchdog entry point (invariant 5, force-revert)
    # ------------------------------------------------------------------
    def force_revert(self, observed_uptime: float) -> GovernorOutcome:
        """Called when the monitor reports critical uptime below the floor."""
        now = self.clock()
        tool = "-"
        digest = ""
        try:
            if observed_uptime >= self.floor:
                final = Decision(
                    ALLOW,
                    "WATCHDOG_IDLE",
                    EMPTY_METADATA,
                    explain("WATCHDOG_IDLE"),
                )
            else:
                entry = self.reverts.peek_latest()
                if entry is None:
                    final = Decision(
                        ESCALATE,
                        "HUMAN_REQUIRED",
                        EMPTY_METADATA,
                        explain(
                            "HUMAN_REQUIRED",
                            f"observed uptime {observed_uptime:.5f} < floor "
                            f"{self.floor:.5f}, but no revertible Raksha "
                            "change is registered",
                        ),
                    )
                else:
                    final, action = self._authorise_revert(entry, observed_uptime)
                    if final is not None and action is not None:
                        self.reverts.pop_latest()
                        tool = action.tool
                        digest = action.digest
                    elif final is not None:
                        tool = entry["tool"]
                        digest = entry["action_digest"]
        except Exception as exc:
            final = Decision(
                DENY,
                "INTERNAL_GUARD_FAILURE",
                EMPTY_METADATA,
                explain("INTERNAL_GUARD_FAILURE", f"{type(exc).__name__}: {exc}"),
            )
        seq = self.ledger.append(
            ts=now,
            actor="watchdog",
            tool=tool,
            action_digest=digest,
            status=final.status,
            reason=final.reason,
            detail=final.explanation,
        ).seq
        return GovernorOutcome(final, seq, digest, tool)

    def _authorise_revert(self, entry: dict, observed_uptime: float):
        """Run the inverse action through schema + twins. Budgets and FIDO2
        are bypassed by design (a revert restores service). If the twins
        refuse the revert for any reason, escalate to a human instead."""
        action, reason, detail = parse_action(entry["inverse"], self.topo)
        if action is None:
            return (
                Decision(
                    ESCALATE,
                    "HUMAN_REQUIRED",
                    EMPTY_METADATA,
                    explain(
                        "HUMAN_REQUIRED",
                        f"registered revert failed schema: {reason} {detail}",
                    ),
                ),
                None,
            )
        va = self.twin_a.evaluate(
            action, self.topo, observed_uptime, self.floor, is_revert=True
        )
        vb = self.twin_b.evaluate(
            action, self.topo, observed_uptime, self.floor, is_revert=True
        )
        if not decisions_agree(va, vb):
            return (
                Decision(
                    ESCALATE,
                    "HUMAN_REQUIRED",
                    EMPTY_METADATA,
                    explain(
                        "HUMAN_REQUIRED",
                        "TCB twins disagree about the revert; refusing to act "
                        "automatically",
                    ),
                ),
                None,
            )
        if va.status == DENY:
            return (
                Decision(
                    ESCALATE,
                    "HUMAN_REQUIRED",
                    EMPTY_METADATA,
                    explain(
                        "HUMAN_REQUIRED",
                        f"revert refused by policy ({va.reason}); a human must "
                        "look at this",
                    ),
                ),
                None,
            )
        return (
            Decision(
                ALLOW,
                "WATCHDOG_FORCE_REVERT",
                va.metadata,
                explain(
                    "WATCHDOG_FORCE_REVERT",
                    f"reverting {entry['tool']} (digest {entry['action_digest'][:12]})",
                ),
            ),
            action,
        )

    # ------------------------------------------------------------------
    # inverse-action construction (keeps every allowed change revertible)
    # ------------------------------------------------------------------
    def _build_inverse(self, action: Action):
        spec = TOOL_REGISTRY[action.tool]
        if not spec.disruptive or spec.inverse is None:
            return None
        p = action.params
        envelope = {
            "justification": f"watchdog revert of {action.digest[:12]}",
            "requested_by": "watchdog",
        }
        if action.tool == "host.quarantine":
            raw = {"tool": "host.release", "params": {"host": p["host"]}, **envelope}
        elif action.tool == "vlan.move":
            raw = {
                "tool": "vlan.move",
                "params": {
                    "host": p["host"],
                    "to_vlan": self.topo.hosts.get(p["host"], p["to_vlan"]),
                },
                **envelope,
            }
        elif action.tool == "edge.sever":
            raw = {"tool": "edge.restore", "params": {"edge": p["edge"]}, **envelope}
        elif action.tool == "firewall.rule.add":
            # The executor (Part 4) mints rule ids of this exact form from
            # the action digest, so the inverse is computable offline.
            raw = {
                "tool": "firewall.rule.remove",
                "params": {"rule_id": f"raksha-{action.digest[:12]}"},
                **envelope,
            }
        else:
            return None
        return raw
