"""Phase 3 — one append / verify interface over three shipped ledger shapes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LedgerVerification:
    ok: bool
    entries: int | None
    head: str | None
    reason: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.ok, "ok": self.ok, "entries": self.entries,
            "head": self.head, "reason": self.reason, "source": self.source,
        }


def append_record(backend: Any, record_type: str, payload: dict[str, Any], *, profile: str = "spine-v2") -> Any:
    """Append through one interface, adapting to each backend's native signature."""
    if profile == "spine-v2":
        return backend.append(record_type, payload)
    if profile == "enterprise-i1":
        return backend.append(
            kind=record_type,
            ref=str(payload.get("ref", "-")),
            text=str(payload.get("text", record_type)),
            payload=payload,
        )
    if profile == "governance-v1":
        import time
        return backend.append(
            ts=payload.get("ts", time.time()), actor=str(payload.get("actor", "phase3")),
            tool=str(payload.get("tool", "-")), action_digest=str(payload.get("action_digest", "")),
            status=str(payload.get("status", "DENY")), reason=str(payload.get("reason", record_type)),
            detail=str(payload.get("detail", "")),
        )
    return backend.append(record_type, payload)


def verify_ledger(backend: Any, *, profile: str = "spine-v2") -> LedgerVerification:
    result = backend.verify()
    if isinstance(result, dict):
        return LedgerVerification(
            ok=bool(result.get("valid", result.get("ok", False))),
            entries=result.get("entries"), head=result.get("head"),
            reason=str(result.get("reason", "chain intact" if result.get("valid", result.get("ok")) else "invalid chain")),
            source=profile,
        )
    if isinstance(result, tuple):
        ok = bool(result[0])
        return LedgerVerification(ok=ok, entries=None, head=None,
                                  reason="chain intact" if ok else f"first_bad_seq={result[1]}",
                                  source=profile)
    ok = bool(getattr(result, "ok", False))
    return LedgerVerification(
        ok=ok, entries=getattr(result, "height", None), head=getattr(result, "head", None),
        reason=str(getattr(result, "reason", "chain intact" if ok else "invalid chain")),
        source=profile,
    )


class LedgerAdapter:
    def __init__(self, backend: Any, *, profile: str = "spine-v2"):
        self.backend = backend
        self.profile = profile

    def append(self, record_type: str, payload: dict[str, Any]) -> Any:
        return append_record(self.backend, record_type, payload, profile=self.profile)

    def verify(self) -> dict[str, Any]:
        return verify_ledger(self.backend, profile=self.profile).to_dict()


__all__ = ["LedgerVerification", "append_record", "verify_ledger", "LedgerAdapter"]
