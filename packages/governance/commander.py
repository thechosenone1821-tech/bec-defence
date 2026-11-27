"""Phase 7 — optional Commander card.

The Commander remains a fallback-only reserved seam for a later phase. This
module contains no model imports, no network calls and no inference path. The
Phase 6–8 runtime displays the card but never invokes a Commander.
"""
from __future__ import annotations

COMMANDER_CONTRACT_VERSION = "raksha-optional-commander-v1"
COMMANDER_CONTRACT = {
    "contract": COMMANDER_CONTRACT_VERSION,
    "enabled": False,
    "mode": "disabled",
    "fallback_only": True,
    "model_invoked": False,
    "ai_model_loaded": False,
    "reason": "Infra uses the deterministic Governor; no Commander inference is run",
    "live_endpoint": None,
}


def commander_card() -> dict[str, object]:
    return dict(COMMANDER_CONTRACT)


__all__ = ["COMMANDER_CONTRACT_VERSION", "COMMANDER_CONTRACT", "commander_card"]
