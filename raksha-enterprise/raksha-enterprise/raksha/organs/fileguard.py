"""fileguard — ransomware staging: mass encryption, shadow-copy deletion, entropy."""

from __future__ import annotations

from typing import Any

from .base import Organ, _flag, _num


class FileGuard(Organ):
    name = "fileguard"

    def evaluate(self, payload: dict[str, Any]) -> tuple[bool, str | None]:
        rate = _num(payload, "encrypt_events_per_min", 0.0)
        entropy = _num(payload, "entropy", 0.0)
        if rate >= 400:
            return True, "FG-ENCRYPT-BURST"
        if entropy > 7.2 and _flag(payload, "shadow_delete"):
            return True, "FG-ENTROPY-SHADOW"
        return False, None
