"""Shared deterministic safety-core boundary."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_LEGACY_CODE_ROOT = Path(__file__).resolve().parents[2] / "raksha-code"
if str(_LEGACY_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LEGACY_CODE_ROOT))

__all__ = [
    "PolicyEngine", "SharedActionGate", "GateDecision", "evaluate_governed_action",
    "Governor", "ExhaustivePlanner", "DryRunExecutor", "Topology", "Proposal",
    "Decision", "UnsafeProposal", "VERDICT_ALLOWED", "VERDICT_REFUSED",
    "safety_card", "commander_card", "COMMANDER_CONTRACT",
]


def __getattr__(name: str) -> Any:
    if name == "PolicyEngine":
        from .governor import PolicyEngine
        return PolicyEngine
    if name in {"SharedActionGate", "GateDecision", "evaluate_governed_action"}:
        from . import gate
        return getattr(gate, name)
    if name in {
        "Governor", "ExhaustivePlanner", "DryRunExecutor", "Topology",
        "Proposal", "Decision", "UnsafeProposal", "VERDICT_ALLOWED",
        "VERDICT_REFUSED", "safety_card",
    }:
        from . import safety
        return getattr(safety, name)
    if name in {"commander_card", "COMMANDER_CONTRACT"}:
        from . import commander
        return getattr(commander, name)
    raise AttributeError(name)
