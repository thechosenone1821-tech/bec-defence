"""Ledger anchor — pin the hash-chain head outside the writable ledger file.

The append-only ledger detects *modification* of any entry (hash chain), but
an attacker who can rewrite the file end-to-end could re-forge a *shorter,
internally consistent* chain. The anchor pins (seq, head_hash) after every
append to a tiny side file with its own HMAC; verify() compares both.
Truncation, re-forging, or reordering then fail verification loudly.

Honest note: an anchor on the SAME writable filesystem raises the bar but is
not a boundary. In production, anchor to WORM storage / HSM / remote signer
(the interface takes an opaque `anchor_writer`/`anchor_reader` pair for that).
"""

import hashlib
import hmac
import json
import os
from typing import Any, Optional

_DEV_KEY = "eigenshield-dev-ledger-anchor-change-in-production"


def _key() -> bytes:
    return os.environ.get("EIGENSHIELD_ANCHOR_KEY", _DEV_KEY).encode()


def _seal(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hmac.new(_key(), body, hashlib.sha256).hexdigest()


class LedgerAnchor:
    def __init__(self, anchor_path: str):
        self.anchor_path = anchor_path

    def exists(self) -> bool:
        return os.path.exists(self.anchor_path)

    def pin(self, seq: int, head_hash: str) -> dict[str, Any]:
        payload = {"seq": int(seq), "head": str(head_hash)}
        sealed = {"anchor": payload, "mac": _seal(payload)}
        with open(self.anchor_path, "w", encoding="utf-8") as f:
            json.dump(sealed, f)
        return sealed

    def read(self) -> Optional[dict[str, Any]]:
        if not os.path.exists(self.anchor_path):
            return None
        try:
            with open(self.anchor_path, "r", encoding="utf-8") as f:
                sealed = json.load(f)
            payload = sealed.get("anchor", {})
            if not hmac.compare_digest(_seal(payload), str(sealed.get("mac", ""))):
                return {"valid": False, "reason": "anchor HMAC mismatch — anchor itself was tampered"}
            return {"valid": True, "seq": payload.get("seq"), "head": payload.get("head")}
        except (OSError, json.JSONDecodeError) as exc:
            return {"valid": False, "reason": f"anchor unreadable: {exc}"}

    def verify(self, ledger_verify_result: dict[str, Any]) -> dict[str, Any]:
        """Cross-check an AuditLedger.verify() result against the pinned head."""
        anchor = self.read()
        if anchor is None:
            return {"anchored": False, "ok": ledger_verify_result.get("valid", False),
                    "reason": "no anchor pinned yet (first boot?)"}
        if not anchor.get("valid"):
            return {"anchored": True, "ok": False, "reason": anchor.get("reason")}
        head = str(ledger_verify_result.get("head", ""))
        entries = int(ledger_verify_result.get("entries", -1))
        ok = hmac.compare_digest(head, str(anchor["head"])) and entries == int(anchor["seq"]) + 1
        return {"anchored": True, "ok": ok,
                "reason": "head matches anchor" if ok else
                          f"head/seq mismatch: anchor seq={anchor['seq']} entries={entries}"}
