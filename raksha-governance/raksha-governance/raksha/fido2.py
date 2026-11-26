"""FIDO2-style step-up sign-off (invariant 4).

Tier-0 actions require cryptographic human sign-off. This module implements
the miniature, honest version of a WebAuthn assertion:

- real Ed25519 signatures (via the `cryptography` package),
- a challenge bound to the *exact* action digest and to a timestamp,
- a per-signer monotonically increasing counter (clone/replay detection),
- a freshness TTL checked against the Governor's injected clock.

It is a stand-in, not full WebAuthn: there is no attestation, no origin
binding, no CTAP transport. The swap-in point for a real authenticator is
`Fido2Registry.verify` -- keep its contract (assertion dict in, VerifyResult
out) and everything above it stays unchanged.

An assertion dict (matches tools.ASSERTION_FIELDS)::

    {
      "signer":    "<registered signer id>",
      "challenge": sha256(f"{action_digest}|{ts}"),
      "counter":   <int, strictly greater than the signer's last counter>,
      "ts":        <unix seconds, within ttl of decision time>,
      "sig":       <base64 Ed25519 signature over the challenge string>
    }
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import Dict, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .canonical import canonical_bytes, sha256_hex
from .tools import ASSERTION_FIELDS

DEFAULT_TTL_SECONDS = 120.0


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    reason: Optional[str] = None   # FIDO2_INVALID / FIDO2_EXPIRED / FIDO2_REPLAY
    detail: Optional[str] = None


def challenge_for(action_digest: str, ts: float) -> str:
    """The challenge binds the sign-off to this exact action at this time."""
    return sha256_hex(canonical_bytes({"action": action_digest, "ts": ts}))


def generate_signer() -> tuple:
    """Dev/test helper: fresh (private_key, public_key) pair."""
    priv = Ed25519PrivateKey.generate()
    return priv, priv.public_key()


def make_assertion(
    priv: Ed25519PrivateKey,
    action_digest: str,
    ts: float,
    counter: int,
    signer_id: str,
) -> dict:
    """Dev/test helper: produce a valid assertion dict for an action."""
    challenge = challenge_for(action_digest, ts)
    sig = priv.sign(challenge.encode("utf-8"))
    return {
        "signer": signer_id,
        "challenge": challenge,
        "counter": counter,
        "ts": ts,
        "sig": base64.b64encode(sig).decode("ascii"),
    }


class Fido2Registry:
    """Registered step-up signers and their assertion counters."""

    def __init__(self, ttl: float = DEFAULT_TTL_SECONDS) -> None:
        self.ttl = ttl
        self._keys: Dict[str, Ed25519PublicKey] = {}
        self._counters: Dict[str, int] = {}

    def register(self, signer_id: str, public_key: Ed25519PublicKey) -> None:
        """Register (or re-register) a step-up signer. Counter resets to 0."""
        self._keys[signer_id] = public_key
        self._counters[signer_id] = 0

    def verify(
        self, action_digest: str, assertion: dict, now: float
    ) -> VerifyResult:
        """Verify one assertion against one action. Fail-closed throughout."""
        signer_id = assertion.get("signer")
        if not isinstance(signer_id, str) or signer_id not in self._keys:
            return VerifyResult(
                False, "FIDO2_INVALID", f"unknown signer {signer_id!r}"
            )

        ts = assertion.get("ts")
        try:
            ts_num = float(ts)
        except (TypeError, ValueError):
            return VerifyResult(False, "FIDO2_INVALID", "bad ts")
        if abs(now - ts_num) > self.ttl:
            return VerifyResult(
                False,
                "FIDO2_EXPIRED",
                f"assertion age {abs(now - ts_num):.0f}s > ttl {self.ttl:.0f}s",
            )

        expected = challenge_for(action_digest, ts_num)
        if assertion.get("challenge") != expected:
            return VerifyResult(
                False,
                "FIDO2_INVALID",
                "challenge is bound to a different action or timestamp",
            )

        counter = assertion.get("counter")
        if isinstance(counter, bool) or not isinstance(counter, int):
            return VerifyResult(False, "FIDO2_INVALID", "bad counter")
        if counter <= self._counters[signer_id]:
            return VerifyResult(
                False,
                "FIDO2_REPLAY",
                f"counter {counter} <= last seen {self._counters[signer_id]}",
            )

        try:
            sig = base64.b64decode(assertion.get("sig", ""), validate=True)
        except (binascii.Error, ValueError):
            return VerifyResult(False, "FIDO2_INVALID", "sig is not base64")
        try:
            self._keys[signer_id].verify(sig, expected.encode("utf-8"))
        except InvalidSignature:
            return VerifyResult(False, "FIDO2_INVALID", "signature does not verify")

        self._counters[signer_id] = counter
        return VerifyResult(True, None, None)
