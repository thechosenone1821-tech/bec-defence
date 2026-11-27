"""Dry-run executor (Part 4 of the governance build).

Statement of record (spec): every disruptive action in this build is
SIMULATED. "We blocked it" actually means "we would have blocked it".

Going live requires, in order: a signed MoU with a pilot site, a feature
flag flipped only after the Part 1 watchdog has been proven in drills,
and a human on the line. When that day comes, this is the LAST module to
change -- and it changes behind a flag.

This module imports nothing that could reach a machine: no os, no
subprocess, no sockets. It cannot execute anything by construction. It
also refuses to act on anything that did not come out of an ALLOW
decision -- the caller passes the GovernorOutcome's action envelope, and
the executor re-checks the status.
"""
from __future__ import annotations

from typing import Dict

DRY_RUN = True   # module-level invariant; asserted on every call

_WOULD = {
    "host.quarantine":      lambda p: f"move host {p['host']!r} to quarantine NIC",
    "host.release":         lambda p: f"release host {p['host']!r} from quarantine",
    "vlan.move":            lambda p: f"move host {p['host']!r} to VLAN {p['to_vlan']!r}",
    "edge.sever":           lambda p: f"sever topology edge {p['edge']!r}",
    "edge.restore":         lambda p: f"restore topology edge {p['edge']!r}",
    "session.terminate":    lambda p: (f"terminate sessions of {p['user']!r} "
                                       f"on {p['host']!r}"),
    "creds.rotate":         lambda p: f"force credential rotation for {p['identity']!r}",
    "firewall.rule.add":    lambda p: f"install Raksha deny rule on edge {p['edge']!r}",
    "firewall.rule.remove": lambda p: f"remove Raksha deny rule {p['rule_id']!r}",
    "snapshot.capture":     lambda p: f"take forensic snapshot of {p['host']!r}",
}


class DryRunExecutor:
    def execute(self, raw_action: dict, status: str) -> Dict:
        """Simulate one action. Only an ALLOW decision may reach this.

        Returns a dict that ALWAYS carries dry_run=True. A non-ALLOW
        status raises ValueError: the executor is not a decision maker.
        """
        assert DRY_RUN, "dry-run invariant broken"
        if status != "ALLOW":
            raise ValueError(
                f"executor refuses non-ALLOW status {status!r}: "
                f"the executor is not a decision maker")
        tool = raw_action.get("tool")
        if tool not in _WOULD:
            raise ValueError(f"executor does not know tool {tool!r}")
        params = raw_action.get("params", {})
        return {
            "tool": tool,
            "params": dict(params),
            "dry_run": True,
            "effect": "simulated",
            "would": _WOULD[tool](params) + " (simulated)",
            "note": "no packet sent, no host touched, no VLAN changed",
        }
