"""Organ registry. Unknown organs are quarantined at ingest, never executed."""

from __future__ import annotations

from .base import Detection, Organ
from .docguard import DocGuard
from .fileguard import FileGuard
from .idguard import IdGuard
from .netguard import NetGuard
from .quorumguard import QuorumGuard
from .sessionguard import SessionGuard
from .tier0guard import Tier0Guard
from .voiceguard import VoiceGuard

ORGANS: dict[str, Organ] = {
    organ.name: organ
    for organ in (VoiceGuard(), DocGuard(), SessionGuard(), FileGuard(),
                  NetGuard(), IdGuard(), QuorumGuard(), Tier0Guard())
}

__all__ = ["Detection", "Organ", "ORGANS", "get_organ", "known_organs"]


def get_organ(name: str) -> Organ | None:
    return ORGANS.get(name)


def known_organs() -> list[str]:
    return sorted(ORGANS)
