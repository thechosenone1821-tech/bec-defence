"""Decision vocabulary shared by every governance component.

Three terminal statuses exist and nothing else:

  ALLOW     the action may proceed (the executor, when it exists, still runs
            it dry-run behind a feature flag)
  DENY      the action is refused; it must never reach the executor
  ESCALATE  the action needs a human; it is parked until valid sign-off arrives

Every Decision carries a machine-readable ``reason`` code and a plain-English
``explanation`` written for a hospital IT generalist, not for a lawyer. If a
reason code is missing from REASON_EXPLANATIONS that is a bug in this package,
not something to paper over at runtime.

The ``metadata`` field is a tuple of (key, value) pairs computed by the policy
evaluators. The TCB twins must agree on every pair (floats compared with a
tolerance) or the decision is refused as TCB_DISAGREEMENT.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

ALLOW = "ALLOW"
DENY = "DENY"
ESCALATE = "ESCALATE"

Metadata = Tuple[Tuple[str, object], ...]
EMPTY_METADATA: Metadata = ()

REASON_EXPLANATIONS = {
    "ALLOWED_STANDARD": (
        "Allowed: the action is on the tool allowlist, touches no crown asset, "
        "keeps projected critical uptime above the floor and is inside every "
        "blast-radius budget."
    ),
    "ALLOWED_WITH_TIER0_OVERRIDE": (
        "Allowed with Tier-0 override: a human signed this exact action with a "
        "valid FIDO2 step-up assertion, and every other invariant passed."
    ),
    "CROWN_JEWEL_LOCK": (
        "Refused: this action would disrupt the ICU VLAN, which Raksha may "
        "never isolate or disrupt under any plan, with or without human "
        "sign-off."
    ),
    "UPTIME_FLOOR": (
        "Refused: the projected critical-service uptime after this action "
        "falls below the floor. No sign-off can authorise breaking hospital "
        "systems."
    ),
    "BUDGET_EXCEEDED": (
        "Refused: the blast-radius budget for this class of action is "
        "exhausted for the current 5-minute window. Wait for the window to "
        "slide, or have a human take over."
    ),
    "FIDO2_REQUIRED": (
        "Escalated: this action touches a Tier-0 asset, so it cannot proceed "
        "without cryptographic human sign-off (FIDO2 step-up)."
    ),
    "FIDO2_INVALID": (
        "Refused: the FIDO2 assertion is not valid (unknown signer, bad "
        "signature, or a challenge bound to a different action)."
    ),
    "FIDO2_EXPIRED": (
        "Refused: the FIDO2 assertion is stale. Fresh sign-off is required "
        "for the current action."
    ),
    "FIDO2_REPLAY": (
        "Refused: this FIDO2 assertion has already been used or its counter "
        "is not strictly increasing. Replayed sign-offs are rejected."
    ),
    "TCB_DISAGREEMENT": (
        "Refused: the TCB twins disagree about this action. When the twins "
        "disagree, the answer is always no."
    ),
    "SCHEMA_VIOLATION": (
        "Dropped: the action does not match the tool schema exactly. "
        "Malformed actions are dropped, never repaired."
    ),
    "UNKNOWN_TOOL": (
        "Dropped: the requested tool is not on the 10-tool allowlist. There "
        "is no way to register new tools at runtime."
    ),
    "MALFORMED_ACTION": (
        "Dropped: the action is not a well-formed JSON object with the "
        "expected envelope."
    ),
    "UNKNOWN_TARGET": (
        "Dropped: the action names a host, VLAN, edge or identity that does "
        "not exist in the topology."
    ),
    "INTERNAL_GUARD_FAILURE": (
        "Refused fail-closed: an internal error occurred while evaluating "
        "this action. On any internal error the answer is no."
    ),
    "WATCHDOG_FORCE_REVERT": (
        "Forced revert: the uptime watchdog observed critical uptime below "
        "the floor and rolled back the most recent Raksha-initiated change, "
        "bypassing budgets and sign-off by design (reverting restores "
        "service; it never destroys it)."
    ),
    "HUMAN_REQUIRED": (
        "Escalated to a human: the watchdog cannot fix this automatically "
        "(nothing revertible is registered, or the revert itself fails "
        "policy), so a human operator must act."
    ),
    "WATCHDOG_IDLE": (
        "No action taken: critical uptime is above the floor."
    ),
}


@dataclass(frozen=True)
class Decision:
    """The outcome of evaluating one action against one policy evaluator."""

    status: str
    reason: str
    metadata: Metadata = EMPTY_METADATA
    explanation: str = ""

    def __str__(self) -> str:
        return f"{self.status}/{self.reason}: {self.explanation}"


def explain(reason: str, detail: Optional[str] = None) -> str:
    """Build a plain-English explanation for a reason code."""
    base = REASON_EXPLANATIONS.get(
        reason, "(no explanation registered for this reason code)"
    )
    if detail:
        return f"{base} [{detail}]"
    return base


def decisions_agree(a: Decision, b: Decision, float_tol: float = 1e-9) -> bool:
    """True when two evaluator verdicts are semantically identical.

    Status and reason must match exactly. Metadata is compared key by key;
    numeric values are compared with a tolerance so that two independent
    implementations are not punished for last-bit floating point differences.
    Explanations are deliberately NOT compared: twins may phrase things
    differently, that is not a semantic disagreement.
    """
    if a.status != b.status or a.reason != b.reason:
        return False
    da, db = dict(a.metadata), dict(b.metadata)
    if da.keys() != db.keys():
        return False
    for key in da:
        x, y = da[key], db[key]
        if isinstance(x, float) or isinstance(y, float):
            try:
                if abs(float(x) - float(y)) > float_tol:
                    return False
            except (TypeError, ValueError):
                return False
        elif x != y:
            return False
    return True
