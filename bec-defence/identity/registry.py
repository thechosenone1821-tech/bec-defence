"""Minimal identity registry.

A credential establishes a **registered identity**, not proof that its
operator is human. The registry therefore distinguishes:

* ``kind`` -- ``"human" | "service" | "registered_agent"``. This is a
  *declared* attribute of the identity, set by an administrator at
  registration time. It is NOT inferred from the credential itself.

* ``revoked`` -- whether the identity's credential is currently revoked.

Allowed actions are declared per-identity and consulted by the response
layer before any (dry-run) action is taken.

This module does **not** implement a real human-verification mechanism (that
is a separate project). It does not hash or salt credentials; in a real
deployment credentials would be stored as salted hashes via a proper
secrets backend. The plaintext comparison here is intentionally minimal so
the demo can run end-to-end.
"""

from __future__ import annotations

import hashlib
import secrets
import threading
from dataclasses import dataclass, field
from typing import Any, Iterable


class CredentialValidationError(ValueError):
    """Raised when a credential is wrong, unknown or revoked."""


class RevocationError(ValueError):
    """Raised when an action is attempted on an already-revoked identity."""


@dataclass
class Identity:
    """A registered identity."""

    identity_id: str
    kind: str                     # "human" | "service" | "registered_agent"
    declared_name: str
    credential_hash: str          # sha256 of salt + credential
    salt: str
    allowed_actions: set[str] = field(default_factory=set)
    revoked: bool = False
    revoked_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def credential_matches(self, credential: str) -> bool:
        h = hashlib.sha256((self.salt + credential).encode("utf-8")).hexdigest()
        return secrets.compare_digest(h, self.credential_hash)

    def to_public_dict(self) -> dict[str, Any]:
        """Public view -- never exposes the credential hash or salt."""
        return {
            "identity_id": self.identity_id,
            "kind": self.kind,
            "declared_name": self.declared_name,
            "allowed_actions": sorted(self.allowed_actions),
            "revoked": self.revoked,
            "revoked_reason": self.revoked_reason,
        }


class IdentityRegistry:
    """In-memory identity registry. Thread-safe."""

    def __init__(self) -> None:
        self._by_id: dict[str, Identity] = {}
        self._lock = threading.Lock()

    # -- registration ------------------------------------------------------- #
    @staticmethod
    def _hash(credential: str, salt: str) -> str:
        return hashlib.sha256((salt + credential).encode("utf-8")).hexdigest()

    def register(
        self,
        *,
        identity_id: str,
        kind: str,
        declared_name: str,
        credential: str,
        allowed_actions: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> Identity:
        if not identity_id:
            raise ValueError("identity_id must be non-empty")
        if kind not in {"human", "service", "registered_agent"}:
            raise ValueError(
                "kind must be one of: human, service, registered_agent"
            )
        if not credential:
            raise ValueError("credential must be non-empty")
        salt = secrets.token_hex(16)
        cred_hash = self._hash(credential, salt)
        ident = Identity(
            identity_id=identity_id,
            kind=kind,
            declared_name=declared_name,
            credential_hash=cred_hash,
            salt=salt,
            allowed_actions=set(allowed_actions),
            metadata=metadata or {},
        )
        with self._lock:
            if identity_id in self._by_id:
                raise ValueError(f"identity {identity_id!r} already registered")
            self._by_id[identity_id] = ident
        return ident

    # -- validation --------------------------------------------------------- #
    def validate(self, identity_id: str, credential: str) -> Identity:
        """Return the identity if the credential matches and is not revoked.

        Raises :class:`CredentialValidationError` otherwise. Note that a
        successful validation only proves the credential matches a registered
        identity; it does **not** prove the operator is human even if
        ``kind == "human"``.
        """
        with self._lock:
            ident = self._by_id.get(identity_id)
            if ident is None:
                raise CredentialValidationError("unknown identity")
            if not ident.credential_matches(credential):
                raise CredentialValidationError("credential mismatch")
            if ident.revoked:
                raise CredentialValidationError(
                    f"identity revoked: {ident.revoked_reason or 'unspecified'}"
                )
            return ident

    # -- revocation --------------------------------------------------------- #
    def revoke(self, identity_id: str, reason: str) -> Identity:
        with self._lock:
            ident = self._by_id.get(identity_id)
            if ident is None:
                raise ValueError(f"unknown identity {identity_id!r}")
            if ident.revoked:
                raise RevocationError(
                    f"identity {identity_id!r} already revoked"
                )
            ident.revoked = True
            ident.revoked_reason = reason
            return ident

    def restore(self, identity_id: str) -> Identity:
        with self._lock:
            ident = self._by_id.get(identity_id)
            if ident is None:
                raise ValueError(f"unknown identity {identity_id!r}")
            ident.revoked = False
            ident.revoked_reason = None
            return ident

    # -- query -------------------------------------------------------------- #
    def get(self, identity_id: str) -> Identity | None:
        with self._lock:
            return self._by_id.get(identity_id)

    def all_identities(self) -> list[Identity]:
        with self._lock:
            return list(self._by_id.values())
