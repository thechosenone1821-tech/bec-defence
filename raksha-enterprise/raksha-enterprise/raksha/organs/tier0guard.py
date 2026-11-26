"""tier0guard — crown-asset proximity (Tier-0 blast-shadow monitoring)."""

from __future__ import annotations

from typing import Any

from .base import Organ, _num


class Tier0Guard(Organ):
    name = "tier0guard"

    def evaluate(self, payload: dict[str, Any]) -> tuple[bool, str | None]:
        touches = _num(payload, "crown_touch_events", 0.0)
        if touches >= 3:
            return True, "T0-PROXIMITY-01"
        return False, None
