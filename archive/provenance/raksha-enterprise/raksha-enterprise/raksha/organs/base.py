"""Organ detector base.

An organ is a pure function over an event's feature payload: it flags or does
not flag, and names the rule that fired. Missing feature keys never flag — an
event without a rule's features is not actionable on that rule (contract R3).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Detection:
    organ: str
    rule_id: str
    event_id: str
    campaign_id: str
    case_id: str
    leg: str
    entity: str
    severity: int
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "organ": self.organ, "rule_id": self.rule_id, "event_id": self.event_id,
            "campaign_id": self.campaign_id, "case_id": self.case_id, "leg": self.leg,
            "entity": self.entity, "severity": self.severity, "summary": self.summary,
        }


class Organ(ABC):
    """Base class for organ detectors. One organ per detection surface."""

    name: str = "organ"

    @abstractmethod
    def evaluate(self, payload: dict[str, Any]) -> tuple[bool, str | None]:
        """Return (flagged, rule_id). rule_id is None when not flagged."""

    def detect(self, payload: dict[str, Any]) -> str | None:
        flagged, rule_id = self.evaluate(payload)
        return rule_id if flagged else None


def _num(payload: dict[str, Any], key: str, default: float) -> float:
    value = payload.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


def _flag(payload: dict[str, Any], key: str) -> bool:
    return payload.get(key) == 1
