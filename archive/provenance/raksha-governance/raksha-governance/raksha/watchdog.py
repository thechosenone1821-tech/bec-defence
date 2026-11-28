"""Uptime watchdog: invariant 5, the guard that can act on its own.

Two jobs:

1. PRE-CHECK. Before any disruptive action is allowed, the projected
   critical uptime (policy.projected_uptime) must stay above the floor.
   No sign-off, no override, nothing authorises breaking the hospital.

2. FORCE-REVERT. If the monitor reports critical uptime BELOW the floor and
   Raksha recently made a revertible change, the watchdog authorises the
   inverse action immediately, bypassing budgets and FIDO2 by design:
   a revert restores service, it never destroys it, so the usual blast-radius
   concerns run in the opposite direction. The revert itself is still
   schema-checked and policy-checked by the TCB twins -- the watchdog cannot
   use the emergency to smuggle in something unrelated.

If uptime is below the floor and nothing revertible is registered, the
watchdog escalates to a human instead of guessing (binding rule 3: nothing
found is not nothing wrong).
"""
from __future__ import annotations

from typing import Dict, List, Optional


class RevertRegistry:
    """Revertible changes the Governor has authorised, newest last."""

    def __init__(self) -> None:
        self._items: List[Dict] = []

    def record(
        self, ts: float, action_digest: str, tool: str, inverse_raw: dict
    ) -> None:
        self._items.append(
            {
                "ts": ts,
                "action_digest": action_digest,
                "tool": tool,
                "inverse": inverse_raw,
            }
        )

    def peek_latest(self) -> Optional[Dict]:
        return self._items[-1] if self._items else None

    def pop_latest(self) -> Optional[Dict]:
        return self._items.pop() if self._items else None

    def __len__(self) -> int:
        return len(self._items)
