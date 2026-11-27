"""The 10-tool allowlist and the strict action schema.

This module is the first gate of the Governor. Three properties matter:

1. CLOSED WORLD. TOOL_REGISTRY is defined at import time and nothing can add
   tools to it at runtime. An action naming anything else is dropped with
   reason UNKNOWN_TOOL. There is deliberately no "register_tool" function.

2. DROP, DO NOT REPAIR. If the action envelope or the tool parameters do not
   match the schema *exactly* (right keys, right types, no extras, nothing
   missing), the action is dropped with SCHEMA_VIOLATION. The Governor never
   guesses what a malformed action "meant".

3. TARGETS MUST EXIST. Hosts, VLANs, edges and identities are validated
   against the topology fixture. Actions naming unknown targets are dropped
   (a classic prompt-injection dodge is to invent a target).

The envelope of an action is::

    {
      "tool": <one of the 10 registry names>,
      "params": {<exactly the tool's parameter keys>},
      "justification": <non-empty string, <= 512 chars>,
      "requested_by": <non-empty string, <= 64 chars>,
      "assertion": <optional FIDO2 assertion dict>
    }
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .canonical import canonical_hash

# Budget buckets. A tool with bucket=None is unrestricted by blast-radius
# budgets (read-only or negligible impact) but is still schema-checked,
# policy-checked and logged like everything else.
BUCKET_CUT = "cut"
BUCKET_QUARANTINE = "quarantine"
BUCKET_SPLICE = "splice"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    bucket: Optional[str]
    disruptive: bool          # does this action change the state of the network?
    params: Dict[str, type]   # exact parameter name -> required type
    inverse: Optional[str]    # tool that undoes this one, if any
    description: str


TOOL_REGISTRY: Dict[str, ToolSpec] = {
    spec.name: spec
    for spec in (
        ToolSpec(
            "host.quarantine", BUCKET_QUARANTINE, True, {"host": str},
            "host.release",
            "Isolate one host from the network (quarantine NIC).",
        ),
        ToolSpec(
            "host.release", BUCKET_SPLICE, False, {"host": str},
            None,
            "Release a host from quarantine (restores connectivity).",
        ),
        ToolSpec(
            "vlan.move", BUCKET_QUARANTINE, True,
            {"host": str, "to_vlan": str},
            "vlan.move",
            "Move one host to another VLAN (typically remediation).",
        ),
        ToolSpec(
            "edge.sever", BUCKET_CUT, True, {"edge": str},
            "edge.restore",
            "Sever one topology edge (cut a network path).",
        ),
        ToolSpec(
            "edge.restore", BUCKET_SPLICE, False, {"edge": str},
            None,
            "Restore a previously severed edge (splice).",
        ),
        ToolSpec(
            "session.terminate", BUCKET_QUARANTINE, True,
            {"host": str, "user": str},
            None,
            "Terminate a user's active sessions on one host.",
        ),
        ToolSpec(
            "creds.rotate", None, True, {"identity": str},
            None,
            "Force credential rotation for one service identity.",
        ),
        ToolSpec(
            "firewall.rule.add", BUCKET_CUT, True, {"edge": str},
            "firewall.rule.remove",
            "Install a Raksha deny rule on one topology edge.",
        ),
        ToolSpec(
            "firewall.rule.remove", BUCKET_SPLICE, False, {"rule_id": str},
            None,
            "Remove a Raksha-installed firewall rule (rollback only).",
        ),
        ToolSpec(
            "snapshot.capture", None, False, {"host": str},
            None,
            "Take a forensic snapshot of one host (non-disruptive).",
        ),
    )
}

TOOL_NAMES = tuple(sorted(TOOL_REGISTRY))

ENVELOPE_FIELDS = {"tool", "params", "justification", "requested_by", "assertion"}
REQUIRED_ENVELOPE_FIELDS = {"tool", "params", "justification", "requested_by"}
ASSERTION_FIELDS = {"signer", "challenge", "counter", "ts", "sig"}

# Which envelope parameter carries the target, per tool.
TARGET_FIELD = {
    "host.quarantine": "host",
    "host.release": "host",
    "vlan.move": "host",
    "session.terminate": "host",
    "snapshot.capture": "host",
    "edge.sever": "edge",
    "edge.restore": "edge",
    "firewall.rule.add": "edge",
    "creds.rotate": "identity",
    "firewall.rule.remove": "rule_id",
}


@dataclass(frozen=True)
class Action:
    """A fully validated action, ready for policy evaluation."""

    tool: str
    params: Dict[str, str]
    justification: str
    requested_by: str
    assertion: Optional[dict]
    digest: str  # sha256 over the canonical form of the four fields above


def digest_for(raw: dict) -> str:
    """Digest of an action envelope, bindable by FIDO2 challenges.

    Deliberately excludes the assertion itself: the signature signs the
    action, not itself.
    """
    return canonical_hash(
        {
            "tool": raw.get("tool"),
            "params": raw.get("params"),
            "justification": raw.get("justification"),
            "requested_by": raw.get("requested_by"),
        }
    )


def parse_action(
    raw: object, topology: object
) -> Tuple[Optional[Action], Optional[str], Optional[str]]:
    """Validate a raw action dict against the schema and the topology.

    Returns (action, None, None) on success, or (None, reason, detail) with a
    drop reason. Never raises, never repairs, never fills in defaults.
    """
    if not isinstance(raw, dict):
        return None, "MALFORMED_ACTION", "action must be a JSON object"

    tool = raw.get("tool")
    if not isinstance(tool, str) or tool not in TOOL_REGISTRY:
        return None, "UNKNOWN_TOOL", f"tool={tool!r} is not on the allowlist"

    extra = set(raw) - ENVELOPE_FIELDS
    missing = REQUIRED_ENVELOPE_FIELDS - set(raw)
    if extra or missing:
        detail = []
        if extra:
            detail.append(f"unexpected fields {sorted(extra)}")
        if missing:
            detail.append(f"missing fields {sorted(missing)}")
        return None, "SCHEMA_VIOLATION", "; ".join(detail)

    params = raw.get("params")
    if not isinstance(params, dict):
        return None, "MALFORMED_ACTION", "params must be a JSON object"

    spec = TOOL_REGISTRY[tool]
    if set(params) != set(spec.params):
        return (
            None,
            "SCHEMA_VIOLATION",
            f"{tool} expects exactly {sorted(spec.params)}, got {sorted(params)}",
        )
    for key, value in params.items():
        if not isinstance(value, str):
            return (
                None,
                "SCHEMA_VIOLATION",
                f"parameter {key!r} must be a string, got {type(value).__name__}",
            )

    justification = raw.get("justification")
    if not isinstance(justification, str) or not (1 <= len(justification) <= 512):
        return None, "SCHEMA_VIOLATION", "justification must be 1..512 characters"
    requested_by = raw.get("requested_by")
    if not isinstance(requested_by, str) or not (1 <= len(requested_by) <= 64):
        return None, "SCHEMA_VIOLATION", "requested_by must be 1..64 characters"

    assertion = raw.get("assertion")
    if assertion is not None:
        if not isinstance(assertion, dict) or set(assertion) != ASSERTION_FIELDS:
            return None, "SCHEMA_VIOLATION", (
                f"assertion must have exactly {sorted(ASSERTION_FIELDS)}"
            )
        counter = assertion["counter"]
        ts = assertion["ts"]
        if isinstance(counter, bool) or not isinstance(counter, int):
            return None, "SCHEMA_VIOLATION", "assertion.counter must be an integer"
        if isinstance(ts, bool) or not isinstance(ts, (int, float)):
            return None, "SCHEMA_VIOLATION", "assertion.ts must be a number"

    if not _targets_resolve(tool, params, topology):
        return (
            None,
            "UNKNOWN_TARGET",
            f"{tool} names a target that does not exist in the topology",
        )

    action = Action(
        tool=tool,
        params=dict(params),
        justification=justification,
        requested_by=requested_by,
        assertion=assertion,
        digest=digest_for(raw),
    )
    return action, None, None


def _targets_resolve(tool: str, params: Dict[str, str], topology) -> bool:
    """Every named target must exist in the topology fixture."""
    field = TARGET_FIELD[tool]
    value = params[field]
    if field == "host":
        if not topology.host_exists(value):
            return False
    elif field == "edge":
        if not topology.edge_exists(value):
            return False
    elif field == "identity":
        if not topology.identity_exists(value):
            return False
    elif field == "rule_id":
        # Only Raksha-installed rules may ever be removed. Part 4's executor
        # will mint rule ids of this exact form at decision time.
        if not value.startswith("raksha-"):
            return False
    if tool == "vlan.move":
        if not topology.vlan_exists(params["to_vlan"]):
            return False
    return True
