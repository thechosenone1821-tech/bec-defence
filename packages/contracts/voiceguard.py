"""Phase 3 — reserved VoiceGuard contract slot.

This module intentionally imports NO VoiceGuard or MAYA implementation. The
maintainer parked that seam until a later phase; the slot only records what a
future integration would have to satisfy.
"""
from __future__ import annotations

from dataclasses import dataclass

VOICEGUARD_SLOT_STATUS = "RESERVED_NOT_INTEGRATED"


@dataclass(frozen=True)
class VoiceGuardContractSlot:
    profile: str = "voiceguard-future-v1"
    status: str = VOICEGUARD_SLOT_STATUS
    import_policy: str = "No packages/ module may import VoiceGuard/MAYA logic in Phases 1-10."
    required_when_integrated: tuple[str, ...] = (
        "signed event envelope validation",
        "consent and retention policy",
        "reason-code catalogue and i18n coverage",
        "honest synthetic-only measurement labels",
        "Governor and append-only ledger compatibility",
    )
    citizen_seam: str = "apps/citizen/legacy_voiceguard.py"
    frozen_asset_check: str = "python tools/check_frozen_assets.py"


VOICEGUARD_CONTRACT_SLOT = VoiceGuardContractSlot()

__all__ = ["VOICEGUARD_SLOT_STATUS", "VoiceGuardContractSlot", "VOICEGUARD_CONTRACT_SLOT"]
