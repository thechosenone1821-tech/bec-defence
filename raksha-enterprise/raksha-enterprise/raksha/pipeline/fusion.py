"""Campaign fusion: verified detections grouped into cross-leg campaigns.

A campaign exists only when detections share an opaque case token; a campaign
spanning both citizen and infra legs is the fused object the planner works on.
The console's low-entropy-token caveat applies here too: case tokens must be
high-entropy random values in production.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from ..organs import Detection


@dataclass(slots=True)
class CampaignState:
    campaign_id: str
    case_id: str
    legs: set[str] = field(default_factory=set)
    organs: set[str] = field(default_factory=set)
    entities: set[str] = field(default_factory=set)
    detections: list[Detection] = field(default_factory=list)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    @property
    def fused(self) -> bool:
        return len(self.legs) >= 2

    def risk_score(self) -> int:
        """Deterministic severity-weighted risk (sum of capped detection severities)."""
        return min(100, sum(d.severity for d in self.detections) * 2)

    def to_dict(self) -> dict[str, object]:
        return {
            "campaign_id": self.campaign_id,
            "case_id": self.case_id,
            "legs": sorted(self.legs),
            "organs": sorted(self.organs),
            "entities": sorted(self.entities),
            "fused": self.fused,
            "risk_score": self.risk_score(),
            "detections": len(self.detections),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


class CampaignFusion:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._campaigns: dict[tuple[str, str], CampaignState] = {}

    def add(self, detection: Detection) -> CampaignState:
        key = (detection.campaign_id, detection.case_id)
        with self._lock:
            state = self._campaigns.get(key)
            if state is None:
                state = CampaignState(campaign_id=detection.campaign_id, case_id=detection.case_id)
                self._campaigns[key] = state
            state.legs.add(detection.leg)
            state.organs.add(detection.organ)
            state.entities.add(detection.entity)
            state.detections.append(detection)
            state.last_seen = time.time()
            return state

    def get(self, campaign_id: str, case_id: str) -> CampaignState | None:
        with self._lock:
            return self._campaigns.get((campaign_id, case_id))

    def all(self) -> list[CampaignState]:
        with self._lock:
            return list(self._campaigns.values())

    def known_campaigns(self) -> set[str]:
        """Campaign ids a proposal has already been planned for (idempotency)."""
        with self._lock:
            return {c.campaign_id for c in self._campaigns.values()}
