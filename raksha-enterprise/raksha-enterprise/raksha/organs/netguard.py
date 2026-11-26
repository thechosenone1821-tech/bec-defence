"""netguard — staged exfiltration / beaconing to low-reputation destinations."""

from __future__ import annotations

from typing import Any

from .base import Organ, _num


class NetGuard(Organ):
    name = "netguard"

    def evaluate(self, payload: dict[str, Any]) -> tuple[bool, str | None]:
        reputation = _num(payload, "dest_reputation", 1.0)
        if reputation >= 0.3:
            return False, None
        egress = _num(payload, "egress_gb_24h", 0.0)
        jitter = _num(payload, "beacon_interval_jitter", 1.0)
        if egress > 2.0:
            return True, "NG-EGRESS-SPIKE"
        if jitter < 0.05:
            return True, "NG-BEACON"
        return False, None
