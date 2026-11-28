"""Phase 3 — one sanitizer/entity-token rule set.

The legacy sanitizer and entity graph import these constants. Keeping them here
means Citizen, Infra, RAAVAN and eval events all receive the same opaque token
prefixes and the same entity path.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
from typing import Optional

SALT_ENV = "EIGENSHIELD_SALT"
DEFAULT_SALT = "eigenshield-dev-salt-change-me"

SIGNAL_RE = re.compile(r"^[A-Z0-9_]{3,64}$")
RING_RE = re.compile(r"^RING_[1-4]_[A-Z_]{3,48}$")
ORGAN_RE = re.compile(r"^[A-Z0-9_]{3,64}$")
EVENT_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{4,64}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
PRINTABLE_RE = re.compile(r"[^ -~]")
REASON_MAX = 240

ENTITY_PREFIX = {
    "host_id": "HOST",
    "user_id": "USER",
    "vlan_id": "VLAN",
    "session_id": "SESS",
    "process_hash": "PROC",
    "agent_id": "AGENT",
    "doc_hash": "DOC",
    "service_id": "SVC",
    "cluster_id": "CLUS",
}
ENTITY_PATH = ("session_id", "user_id", "host_id", "vlan_id", "service_id")
OPAQUE_PREFIXES = tuple(f"{p}_" for p in ENTITY_PREFIX.values()) + ("sha256:", "pid:")


def get_salt() -> bytes:
    return os.environ.get(SALT_ENV, DEFAULT_SALT).encode()


def opaque_token(prefix: str, raw: str, salt: Optional[bytes] = None) -> str:
    salt = salt or get_salt()
    digest = hmac.new(salt, str(raw).encode(), hashlib.sha256).hexdigest()
    return f"{prefix}_{digest[:6].upper()}"


def is_opaque_identifier(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(OPAQUE_PREFIXES)


def digest(raw: Any) -> str:
    return "sha256:" + hashlib.sha256(str(raw).encode()).hexdigest()[:32]


def clean_reason(value: Any) -> str:
    """Whitespace-collapsed, printable-ASCII, bounded organ reason."""
    text = str(value or "")
    text = PRINTABLE_RE.sub(" ", text)
    text = " ".join(text.split())
    return text[:REASON_MAX]


__all__ = [
    "SALT_ENV", "DEFAULT_SALT", "SIGNAL_RE", "RING_RE", "ORGAN_RE",
    "EVENT_ID_RE", "TIMESTAMP_RE", "PRINTABLE_RE", "REASON_MAX",
    "ENTITY_PREFIX", "ENTITY_PATH", "OPAQUE_PREFIXES", "get_salt",
    "opaque_token", "is_opaque_identifier", "digest", "clean_reason",
]
