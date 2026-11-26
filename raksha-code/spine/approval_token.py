"""Governor-signed approval tokens (Part 4, Phase 7).

A kill switch needs authority. The first version of `OrganFleet.halt()` took an
``approved_by`` string and checked it was non-empty — which verifies that the
caller wrote *something*, not that a Governor approved anything. That is the
"self-reported provenance" defect this codebase has recorded and fixed before.

So approval is a signed token:

* the **Governor** mints it, and only the Governor holds the minting path;
* it names the exact action, organ and reason it authorises, so a token for
  ``halt:BRAGG`` cannot be replayed to halt ``COOKIE``;
* it expires, so yesterday's approval is not today's;
* it is single-use, so one approval does not stop the fleet one organ at a time.

The signature is HMAC-SHA256 over the same secret the RPC envelopes use. In
production this would be the Governor's own key, separate from the organ-RPC
key — the token shape would not change.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

DEFAULT_TTL_SEC = 120.0


def _secret() -> bytes:
    # Deliberately a *different* key from the organ-RPC secret: an entity that
    # can mint organ RPCs must not thereby be able to mint kill-switch approvals.
    return os.environ.get("RAKSHA_GOVERNOR_APPROVAL_SECRET",
                          "raksha-dev-governor-approval-secret-not-for-prod").encode()


def _body(token: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in token.items() if k != "signature"}


def _sign(token: Dict[str, Any]) -> str:
    payload = json.dumps(_body(token), sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(_secret(), payload, hashlib.sha256).hexdigest()


class ApprovalLedger:
    """Tracks spent tokens. Single-use is enforced here, not by politeness."""

    def __init__(self) -> None:
        self._spent: Dict[str, float] = {}

    def spend(self, token_id: str, now: float) -> bool:
        """Mark a token used. Returns False if it was already spent."""
        if token_id in self._spent:
            return False
        self._spent[token_id] = now
        return True

    def spent_ids(self) -> List[str]:
        return sorted(self._spent)


def mint(action: str, organ: str, reason: str,
         ttl_sec: float = DEFAULT_TTL_SEC,
         clock=time.time,
         decision: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Mint an approval token. **Called by the Governor, after `evaluate()`.**

    `decision` is the Governor's own verdict. A token is refused unless that
    verdict is APPROVED — a Governor that blocks an action cannot hand out
    permission for it, and the token should make that impossible rather than
    rely on the caller to check.
    """
    if decision is not None:
        verdict = str(decision.get("decision", "")).upper()
        if verdict != "APPROVED":
            raise ValueError(f"cannot mint an approval for a {verdict or 'missing'} decision")
    if not action or not organ:
        raise ValueError("an approval must name an action and an organ")
    now = clock()
    token = {
        "token_id": f"apr_{uuid.uuid4().hex[:16]}",
        "action": str(action),
        "organ": str(organ),
        "reason": str(reason),
        "issued_at": now,
        "expires_at": now + float(ttl_sec),
        "issuer": "governor",
    }
    token["signature"] = _sign(token)
    return token


def verify(token: Any, action: str, organ: str, now: Optional[float] = None) -> Dict[str, Any]:
    """Check a token for a specific action+organ. Returns {ok, reason}.

    Every failure names what was wrong, because an operator staring at
    "HALT_REFUSED" needs to know whether the token expired or was forged.
    """
    now = time.time() if now is None else now
    if not isinstance(token, dict):
        return {"ok": False, "reason": "no approval token supplied"}
    if "signature" not in token:
        return {"ok": False, "reason": "approval token is unsigned"}
    expected = _sign(token)
    if not hmac.compare_digest(expected, str(token.get("signature", ""))):
        return {"ok": False, "reason": "approval token signature does not verify"}
    if token.get("action") != action:
        return {"ok": False,
                "reason": f"approval is for {token.get('action')!r}, not {action!r}"}
    if token.get("organ") != organ:
        return {"ok": False,
                "reason": f"approval names organ {token.get('organ')!r}, not {organ!r}"}
    expires = token.get("expires_at")
    if not isinstance(expires, (int, float)):
        return {"ok": False, "reason": "approval token has no expiry"}
    if now > float(expires):
        return {"ok": False,
                "reason": f"approval expired {now - float(expires):.0f}s ago"}
    return {"ok": True, "reason": "approval verified", "token_id": token.get("token_id")}
