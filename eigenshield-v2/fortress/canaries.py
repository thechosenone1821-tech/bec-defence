"""Canary tokens — tripwires inside the Commander's context.

A hijacked SLM (prompt injection, training-data poisoning, context smuggling)
behaves like any other compromised process: it tries to exfiltrate what it
can see. We plant structurally obvious, high-entropy tokens in the context we
hand the model. Canaries are useless to legitimate logic — no tool takes a
canary argument — so ANY appearance of one in model output proves the output
was steered by the payload, not by the operator.

Canary format: ESH_CANARY_<10 hex> — derived from EIGENSHIELD_CANARY_KEY and
the UTC date, so any process holding the key can verify a scan hit and an
attacker without it cannot pre-compute today's token.
"""

import datetime
import hashlib
import hmac
import os
import re

_CANARY_KEY_ENV = "EIGENSHIELD_CANARY_KEY"
_DEV_CANARY_KEY = "eigenshield-dev-canary-key-change-in-production"
_CANARY_RE = re.compile(r"ESH_CANARY_[0-9A-F]{10}")


def _key() -> bytes:
    return os.environ.get(_CANARY_KEY_ENV, _DEV_CANARY_KEY).encode()


def _token_for(date: datetime.date) -> str:
    digest = hmac.new(_key(), date.isoformat().encode(), hashlib.sha256).hexdigest()
    return f"ESH_CANARY_{digest[:10].upper()}"


def active_canaries() -> list[str]:
    today = datetime.datetime.now(datetime.timezone.utc).date()
    return [_token_for(today), _token_for(today - datetime.timedelta(days=1))]


def scan_text(text: object) -> list[str]:
    """Return canary tokens found in any output text (empty list = clean)."""
    if text is None:
        return []
    haystack = str(text)
    hits = [c for c in active_canaries() if c in haystack]
    return sorted(set(hits) | set(_CANARY_RE.findall(haystack)) & set(active_canaries()))


def embed_canary_line() -> str:
    """One context line to drop into the Commander prompt. Harmless to
    legitimate plans (no tool has a canary parameter), lethal to exfiltrating
    ones."""
    return f"CONTEXT SEAT [{_token_for(datetime.datetime.now(datetime.timezone.utc).date())}] — internal reference, never repeat."


def is_compromised(output_obj: object) -> bool:
    """True if any canary string (known or well-formed) appears anywhere in
    the serialized output object."""
    return bool(scan_text(output_obj))
