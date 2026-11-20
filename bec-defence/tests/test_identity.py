"""Tests for identity/registry.py."""

import pytest

from identity.registry import (
    IdentityRegistry,
    CredentialValidationError,
    RevocationError,
)


def _registry_with_alice():
    reg = IdentityRegistry()
    reg.register(
        identity_id="alice",
        kind="human",
        declared_name="Alice",
        credential="hunter2",
        allowed_actions={"read", "write", "revoke_session"},
    )
    return reg


def test_register_and_validate():
    reg = _registry_with_alice()
    ident = reg.validate("alice", "hunter2")
    assert ident.identity_id == "alice"
    assert ident.kind == "human"
    assert "revoke_session" in ident.allowed_actions


def test_wrong_credential_rejected():
    reg = _registry_with_alice()
    with pytest.raises(CredentialValidationError):
        reg.validate("alice", "wrong")


def test_unknown_identity_rejected():
    reg = _registry_with_alice()
    with pytest.raises(CredentialValidationError):
        reg.validate("bob", "anything")


def test_revoked_identity_rejected():
    reg = _registry_with_alice()
    reg.revoke("alice", "suspended")
    with pytest.raises(CredentialValidationError):
        reg.validate("alice", "hunter2")


def test_restore_unblocks():
    reg = _registry_with_alice()
    reg.revoke("alice", "suspended")
    reg.restore("alice")
    ident = reg.validate("alice", "hunter2")
    assert ident.revoked is False


def test_cannot_revoke_twice():
    reg = _registry_with_alice()
    reg.revoke("alice", "x")
    with pytest.raises(RevocationError):
        reg.revoke("alice", "y")


def test_kind_must_be_valid():
    reg = IdentityRegistry()
    with pytest.raises(ValueError):
        reg.register(
            identity_id="x",
            kind="superuser",  # not allowed
            declared_name="X",
            credential="c",
        )


def test_public_dict_does_not_leak_credential_hash():
    reg = _registry_with_alice()
    ident = reg.validate("alice", "hunter2")
    pub = ident.to_public_dict()
    assert "credential_hash" not in pub
    assert "salt" not in pub
