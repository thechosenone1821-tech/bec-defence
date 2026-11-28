"""quorumguard — probing of the Governor / containment decision surface."""

from __future__ import annotations

from typing import Any

from .base import Organ, _num


class QuorumGuard(Organ):
    name = "quorumguard"

    def evaluate(self, payload: dict[str, Any]) -> tuple[bool, str | None]:
        probe_rate = _num(payload, "decision_probe_rate", 0.0)
        anomalies = _num(payload, "signature_anomalies", 0.0)
        if probe_rate > 0.4:
            return True, "QG-DECISION-PROBE"
        if anomalies >= 2:
            return True, "QG-SIG-ANOMALY"
        return False, None
