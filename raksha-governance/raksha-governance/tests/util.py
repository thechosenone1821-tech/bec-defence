"""Shared helpers for the governance tests."""
from __future__ import annotations

from raksha.fido2 import make_assertion
from raksha.tools import digest_for


def sign_into(raw: dict, priv, signer_id: str, ts: float, counter: int = 1) -> dict:
    """Attach a valid FIDO2 assertion for exactly this raw action."""
    assertion = make_assertion(priv, digest_for(raw), ts, counter, signer_id)
    return {**raw, "assertion": assertion}


def quarantine(host: str, justification: str = "suspected compromise") -> dict:
    return {
        "tool": "host.quarantine",
        "params": {"host": host},
        "justification": justification,
        "requested_by": "commander",
    }


def sever(edge: str, justification: str = "sever attacker path") -> dict:
    return {
        "tool": "edge.sever",
        "params": {"edge": edge},
        "justification": justification,
        "requested_by": "commander",
    }
