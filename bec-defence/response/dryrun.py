"""Dry-run response layer.

Every response decision is recorded as a :class:`ResponseDecision` and
**executed in dry-run mode only**. No real process killing, no real file
encryption, no real user lockout. The only enforced action is revocation
against a demo identity in :class:`identity.registry.IdentityRegistry`,
which is itself an in-memory demo object.

The decision schema is intentionally narrow so downstream tooling can parse
it without surprises::

    decision_id, timestamp, incident_id, identity_id, action,
    would_execute, executed, reason, evidence

``would_execute`` is the recommendation; ``executed`` is what actually
happened (always ``False`` except for demo revocation against the
in-memory registry).

Safety rules enforced here:

1.  An action is only recommended when the identity is registered AND the
    action is in its ``allowed_actions`` AND the incident severity warrants
    it. Otherwise ``would_execute`` is ``False``.

2.  Even when ``would_execute`` is ``True``, only ``revoke_session`` is
    actually carried out, and only against the in-memory registry.

3.  The layer never calls ``os.kill``, never writes to user files, never
    contacts an external endpoint.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

from core.events import Incident
from identity.registry import IdentityRegistry, Identity


RESPONSE_ACTIONS = frozenset(
    {
        "would_revoke_session",
        "would_deny_action",
        "would_request_file_quarantine",
        "revoke_session",  # the only one we actually execute, on the demo registry
    }
)

# Severity that warrants each action.
_SEVERITY_FOR_ACTION: dict[str, str] = {
    "would_revoke_session": "high",
    "would_deny_action": "medium",
    "would_request_file_quarantine": "medium",
    "revoke_session": "high",
}

_LADDER = ["info", "low", "medium", "high", "critical"]


def _severity_at_least(actual: str, required: str) -> bool:
    try:
        return _LADDER.index(actual) >= _LADDER.index(required)
    except ValueError:
        return False


@dataclass
class ResponseDecision:
    decision_id: str
    timestamp: float
    incident_id: str | None
    identity_id: str | None
    action: str
    would_execute: bool
    executed: bool
    reason: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DryRunResponseLayer:
    """Maps incidents to (dry-run) response decisions."""

    def __init__(self, registry: IdentityRegistry):
        self.registry = registry
        self.decisions: list[ResponseDecision] = []

    def evaluate_incident(self, incident: Incident) -> list[ResponseDecision]:
        """Produce one or more dry-run decisions for an incident.

        Heuristics:

        * If the incident references an ``entity_id`` that is a registered
          identity and the severity is high+, recommend session revocation.
        * If the incident references a ``resource`` that looks like a file
          path and the severity is medium+, recommend file quarantine
          (dry-run).
        * If the incident references a registered identity but its severity
          is medium, recommend action denial (dry-run).
        """
        out: list[ResponseDecision] = []
        ts = time.time()

        # Look up an identity by entity_id (correlation engine uses entity_id
        # as the join key when one is available).
        ident: Identity | None = None
        if incident.key_kind == "entity_id":
            ident = self.registry.get(incident.key)

        # ---- session revocation (high+) ----
        if ident is not None and _severity_at_least(incident.severity, "high"):
            allowed = "revoke_session" in ident.allowed_actions
            reason_bits = [
                f"incident severity {incident.severity}",
                f"identity kind {ident.kind}",
                f"allowed_actions={sorted(ident.allowed_actions)}",
            ]
            would = allowed and not ident.revoked
            executed = False
            if would:
                try:
                    self.registry.revoke(ident.identity_id, f"incident {incident.incident_id}")
                    executed = True
                except Exception as exc:  # pragma: no cover -- defensive
                    reason_bits.append(f"revocation failed: {exc}")
            out.append(
                ResponseDecision(
                    decision_id=str(uuid.uuid4()),
                    timestamp=ts,
                    incident_id=incident.incident_id,
                    identity_id=ident.identity_id,
                    action="revoke_session",
                    would_execute=bool(would),
                    executed=executed,
                    reason="; ".join(reason_bits),
                    evidence=[e.reason for e in incident.events],
                )
            )

        # ---- action denial (medium+, dry-run) ----
        if ident is not None and _severity_at_least(incident.severity, "medium"):
            out.append(
                ResponseDecision(
                    decision_id=str(uuid.uuid4()),
                    timestamp=ts,
                    incident_id=incident.incident_id,
                    identity_id=ident.identity_id,
                    action="would_deny_action",
                    would_execute=True,
                    executed=False,
                    reason=f"dry-run: deny future actions for {ident.identity_id} "
                           f"(severity {incident.severity})",
                    evidence=[e.reason for e in incident.events],
                )
            )

        # ---- file quarantine (medium+, dry-run) ----
        if incident.key_kind == "resource" and _severity_at_least(incident.severity, "medium"):
            out.append(
                ResponseDecision(
                    decision_id=str(uuid.uuid4()),
                    timestamp=ts,
                    incident_id=incident.incident_id,
                    identity_id=None,
                    action="would_request_file_quarantine",
                    would_execute=True,
                    executed=False,
                    reason=f"dry-run: request quarantine for resource {incident.key!r}",
                    evidence=[e.reason for e in incident.events],
                )
            )

        self.decisions.extend(out)
        return out

    def evaluate_event(self, event) -> list[ResponseDecision]:
        """Convenience: wrap a single event in an ephemeral incident.

        Single-event evaluation does NOT trigger revocation -- revocation
        requires a correlated incident with >= 2 events.
        """
        from core.events import Incident
        inc = Incident(
            incident_id=str(uuid.uuid4()),
            key=event.entity_id if event.entity_id else event.resource,
            key_kind="entity_id" if event.entity_id else "resource",
            opened_at=event.timestamp,
        )
        inc.add(event)
        # Mark as single-event so evaluate_incident does not escalate to
        # revocation on its own.
        if len(inc.events) < 2:
            return []
        return self.evaluate_incident(inc)
