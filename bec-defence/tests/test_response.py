"""Tests for response/dryrun.py."""

import pytest

from core.events import UnifiedEvent, Incident
from identity.registry import IdentityRegistry
from response.dryrun import DryRunResponseLayer


def _registry():
    reg = IdentityRegistry()
    reg.register(
        identity_id="alice",
        kind="human",
        declared_name="Alice",
        credential="hunter2",
        allowed_actions={"read", "write", "revoke_session"},
    )
    reg.register(
        identity_id="svc_backup",
        kind="service",
        declared_name="Backup",
        credential="svc-token",
        allowed_actions={"read"},  # NOT allowed to be revoked via this action
    )
    return reg


def _incident(entity_id=None, resource=None, severity="high"):
    key = entity_id if entity_id is not None else resource
    kind = "entity_id" if entity_id is not None else "resource"
    inc = Incident(incident_id="inc-1", key=key, key_kind=kind, opened_at=0.0)
    e = UnifiedEvent(
        engine="spectral",
        entity_id=entity_id or "n/a",
        resource=resource or "n/a",
        severity=severity,
        score=0.8,
        reason="test",
    )
    inc.add(e)
    # Add a second event so it counts as a real incident (>= 2 events).
    e2 = UnifiedEvent(
        engine="blackhole",
        entity_id=entity_id or "n/a",
        resource=resource or "n/a",
        severity=severity,
        score=0.9,
        reason="test2",
    )
    inc.add(e2)
    return inc


def test_high_severity_revokes_allowed_identity():
    reg = _registry()
    layer = DryRunResponseLayer(reg)
    decisions = layer.evaluate_incident(_incident(entity_id="alice", severity="high"))
    revokes = [d for d in decisions if d.action == "revoke_session"]
    assert revokes, "expected a revoke_session decision"
    assert revokes[0].would_execute is True
    assert revokes[0].executed is True
    # Identity is now revoked.
    assert reg.get("alice").revoked is True


def test_revocation_not_allowed_for_service_without_action():
    reg = _registry()
    layer = DryRunResponseLayer(reg)
    decisions = layer.evaluate_incident(
        _incident(entity_id="svc_backup", severity="high")
    )
    revokes = [d for d in decisions if d.action == "revoke_session"]
    # svc_backup does NOT have revoke_session in allowed_actions.
    if revokes:
        assert revokes[0].would_execute is False
        assert revokes[0].executed is False
        assert reg.get("svc_backup").revoked is False


def test_medium_severity_does_dry_run_deny_only():
    reg = _registry()
    layer = DryRunResponseLayer(reg)
    decisions = layer.evaluate_incident(
        _incident(entity_id="alice", severity="medium")
    )
    # Medium -> would_deny_action, but NOT revoke_session.
    denies = [d for d in decisions if d.action == "would_deny_action"]
    revokes = [d for d in decisions if d.action == "revoke_session"]
    assert denies
    assert all(d.executed is False for d in denies)
    assert not revokes


def test_file_quarantine_is_dry_run_only():
    reg = _registry()
    layer = DryRunResponseLayer(reg)
    decisions = layer.evaluate_incident(
        _incident(resource="/data/notes.txt", severity="high")
    )
    quarantines = [d for d in decisions if d.action == "would_request_file_quarantine"]
    assert quarantines
    assert all(d.executed is False for d in quarantines)


def test_single_event_does_not_trigger_revocation():
    reg = _registry()
    layer = DryRunResponseLayer(reg)
    e = UnifiedEvent(
        engine="spectral",
        entity_id="alice",
        resource="r",
        severity="critical",
        score=1.0,
        reason="single",
    )
    decisions = layer.evaluate_event(e)
    # evaluate_event wraps a single event in an incident with < 2 events;
    # it must NOT revoke.
    assert decisions == []
    assert reg.get("alice").revoked is False
