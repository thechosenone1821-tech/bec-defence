"""idguard — credential stuffing / identity-vault abuse."""

from __future__ import annotations

from typing import Any

from .base import Organ, _flag, _num


class IdGuard(Organ):
    name = "idguard"

    def evaluate(self, payload: dict[str, Any]) -> tuple[bool, str | None]:
        requests = _num(payload, "privilege_requests_24h", 0.0)
        if requests >= 15 and _flag(payload, "new_device"):
            return True, "ID-CREDSTUFF-01"
        return False, None
