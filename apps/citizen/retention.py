"""App-owned retention policy for VIGIL image sessions.

VIGIL keeps decoded pixels in process memory only. A user can explicitly purge a
session, and the engine enforces its own TTL and active-session cap. Exported PNG,
JSON and ZIP bytes are generated on request and are not persisted by Citizen.
"""
from __future__ import annotations

from typing import Any, Dict

SESSION_TTL_SECONDS = 300
MAX_ACTIVE_SESSIONS = 3
STORAGE = "process memory only"
PURGE_TRIGGERS = (
    "DELETE /vigil/api/sessions/{id}",
    "session TTL expiry",
    "service restart",
)


def retention_policy() -> Dict[str, Any]:
    return {
        "session_ttl_seconds": SESSION_TTL_SECONDS,
        "max_active_sessions": MAX_ACTIVE_SESSIONS,
        "storage": STORAGE,
        "persistent_uploads": False,
        "purge_triggers": list(PURGE_TRIGGERS),
        "privacy_efficacy": "UNMEASURED",
        "source": "packages/vigil/config.py + packages/vigil/engines/security_engine.py",
    }


def session_card(session_id: str) -> Dict[str, Any]:
    return {
        "session_id": session_id,
        "storage": STORAGE,
        "ttl_seconds": SESSION_TTL_SECONDS,
        "purge_route": f"/vigil/api/sessions/{session_id}",
    }


__all__ = [
    "MAX_ACTIVE_SESSIONS", "PURGE_TRIGGERS", "SESSION_TTL_SECONDS", "STORAGE",
    "retention_policy", "session_card",
]
