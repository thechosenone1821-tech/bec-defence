"""Phase 3 — no app may bypass signature verification or the Governor."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .envelope import validate_envelope


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str
    validation: dict[str, Any]
    governor_decision: Any
    executor_result: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed, "reason": self.reason,
            "validation": self.validation, "governor_decision": self.governor_decision,
            "executor_result": self.executor_result,
        }


def _decision_status(decision: Any) -> str:
    if isinstance(decision, dict):
        return str(decision.get("decision") or decision.get("status") or decision.get("verdict") or "").upper()
    return str(getattr(decision, "decision", None) or getattr(decision, "status", None) or getattr(decision, "verdict", None) or "").upper()


class SharedActionGate:
    """One door from a signed event + proposed action to a dry-run executor."""

    def __init__(self, governor: Any, executor: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None):
        self.governor = governor
        self.executor = executor

    def submit(self, raw_event: dict[str, Any], action: dict[str, Any], *, context: dict[str, Any] | None = None, key: Any = None) -> GateDecision:
        validation = validate_envelope(raw_event, key=key, require_signature=True)
        validation_dict = validation.to_dict()
        if not validation.actionable:
            return GateDecision(False, f"signature_not_valid:{validation.state.value}", validation_dict, None, None)

        ctx = dict(context or {})
        ctx["envelope_contract"] = validation.contract
        ctx["event_profile"] = validation.profile
        if hasattr(self.governor, "evaluate"):
            decision = self.governor.evaluate(action, context=ctx)
        elif hasattr(self.governor, "decide"):
            decision = self.governor.decide(action)
            if hasattr(decision, "to_dict"):
                decision = decision.to_dict()
        else:
            raise TypeError("governor must expose evaluate() or decide()")

        status = _decision_status(decision)
        allowed = status == "APPROVED" or bool(getattr(decision, "allowed", False)) if not isinstance(decision, dict) else status == "APPROVED"
        if not allowed:
            return GateDecision(False, f"governor_refused:{status or 'UNKNOWN'}", validation_dict, decision, None)

        if self.executor is None:
            result = {"status": "GOVERNOR_APPROVED_NO_EXECUTOR", "dry_run": True, "executed": False}
        else:
            result = dict(self.executor(str(action.get("tool", "")), dict(action.get("args", {}))))
            result.setdefault("executed", True)
        return GateDecision(True, "approved", validation_dict, decision, result)


def evaluate_governed_action(governor: Any, executor: Callable[[str, dict[str, Any]], dict[str, Any]] | None, raw_event: dict[str, Any], action: dict[str, Any], *, context: dict[str, Any] | None = None, key: Any = None) -> GateDecision:
    return SharedActionGate(governor, executor).submit(raw_event, action, context=context, key=key)


__all__ = ["GateDecision", "SharedActionGate", "evaluate_governed_action"]
