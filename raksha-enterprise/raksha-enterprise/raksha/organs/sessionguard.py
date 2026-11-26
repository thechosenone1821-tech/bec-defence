"""sessionguard — replayed banking sessions (token reuse across geographies)."""

from __future__ import annotations

from typing import Any

from .base import Organ, _num


class SessionGuard(Organ):
    name = "sessionguard"

    def evaluate(self, payload: dict[str, Any]) -> tuple[bool, str | None]:
        reuse = _num(payload, "token_reuse_count", 0.0)
        distance = _num(payload, "geo_distance_km", 0.0)
        if reuse >= 2 and distance > 300:
            return True, "SG-REPLAY-01"
        return False, None
