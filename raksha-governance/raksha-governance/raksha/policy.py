"""Pure topology arithmetic: what does an action touch, and what does it cost?

Both TCB twins call the SAME impact functions here. That is a deliberate,
documented scope decision for Part 1: the twins exist to double-check the
POLICY BRANCHING (which guard fires, in which order, with which verdict).
Duplicating the arithmetic itself is Part 2 work (hardened twins as separate
processes with independent math), tracked in GOVERNANCE_BUILD_PLAN.md.

Everything in this module is a pure function of (action, topology, numbers).
No clock, no state, no I/O.
"""
from __future__ import annotations

from typing import Tuple

from .fixtures import Topology
from .tools import Action, ToolSpec

HOST_TARGET_TOOLS = {"host.quarantine", "host.release", "session.terminate",
                     "snapshot.capture"}
EDGE_TARGET_TOOLS = {"edge.sever", "edge.restore", "firewall.rule.add"}


def touches_vlan(action: Action, topology: Topology, vlan: str) -> bool:
    """Does this action target any host/edge on `vlan`, or move a host onto it?"""
    tool, params = action.tool, action.params
    if tool in HOST_TARGET_TOOLS:
        return topology.hosts.get(params["host"]) == vlan
    if tool == "vlan.move":
        return (
            topology.hosts.get(params["host"]) == vlan
            or params["to_vlan"] == vlan
        )
    if tool in EDGE_TARGET_TOOLS:
        edge = topology.edges.get(params["edge"])
        if edge is None:
            return False
        return (
            topology.hosts.get(edge.a) == vlan
            or topology.hosts.get(edge.b) == vlan
        )
    return False  # creds.rotate / firewall.rule.remove never touch a VLAN


def touches_host(action: Action, topology: Topology, host: str) -> bool:
    """Does this action target `host` directly or via an incident edge?"""
    tool, params = action.tool, action.params
    if tool in HOST_TARGET_TOOLS or tool == "vlan.move":
        return params.get("host") == host
    if tool in EDGE_TARGET_TOOLS:
        edge = topology.edges.get(params["edge"])
        return edge is not None and host in {edge.a, edge.b}
    return False


def touches_crown(action: Action, topology: Topology) -> bool:
    return touches_vlan(action, topology, topology.crown_vlan)


def touches_tier0(action: Action, topology: Topology) -> bool:
    if action.tool == "creds.rotate":
        return action.params["identity"] in topology.tier0_identities
    if action.tool == "firewall.rule.remove":
        return False
    # Crown hosts are a subset of Tier-0; check every Tier-0 host by NAME.
    tier0_hosts = set(topology.tier0_hosts) | {
        h for h in topology.hosts if topology.is_crown_host(h)
    }
    return any(touches_host(action, topology, h) for h in tier0_hosts)


def severed_critical_weight(action: Action, topology: Topology) -> float:
    """Critical flow weight (fixture) severed by this action if allowed.

    Model (documented, simple, conservative):

    - quarantine / vlan.move        -> all critical edges of the host drop
    - edge.sever / firewall.rule.add -> the edge's critical weight drops
    - session.terminate              -> 0 (sessions die, flows persist)
    - restores, releases, removals   -> 0 (they give service back)
    - creds.rotate                   -> 0 (auth churn, not flow loss)
    - snapshot.capture               -> 0 (read-only)
    """
    tool = action.tool
    if tool in {"edge.sever", "firewall.rule.add"}:
        edge = topology.edges.get(action.params["edge"])
        if edge is not None and edge.critical:
            return edge.weight
        return 0.0
    if tool in {"host.quarantine", "vlan.move"}:
        return sum(
            e.weight
            for e in topology.edges_of_host(action.params["host"])
            if e.critical
        )
    return 0.0


def projected_uptime(
    uptime_current: float, severed: float, total_critical: float
) -> float:
    """Uptime model: fraction of critical flow weight still delivered.

    ``uptime_current`` is what the monitor reports (fixture in tests);
    the projection scales it by the share of critical weight this action
    would remove. The uptime watchdog (invariant 5) refuses any action whose
    projection falls below the floor.
    """
    if total_critical <= 0:
        return uptime_current
    return uptime_current * max(0.0, 1.0 - severed / total_critical)


def assess(action: Action, topology: Topology, uptime_current: float,
           floor: float) -> Tuple[bool, bool, float, float]:
    """One call returning (crown, tier0, severed, projected) for twins."""
    crown = touches_crown(action, topology)
    tier0 = touches_tier0(action, topology)
    severed = severed_critical_weight(action, topology)
    projected = projected_uptime(
        uptime_current, severed, topology.total_critical_weight()
    )
    return crown, tier0, severed, projected


def metadata_for(
    spec: ToolSpec, crown: bool, tier0: bool, severed: float, projected: float
) -> Tuple[Tuple[str, object], ...]:
    """Canonical metadata tuple attached to every twin verdict."""
    return (
        ("bucket", spec.bucket),
        ("crown", crown),
        ("projected_uptime", projected),
        ("severed_critical", severed),
        ("tier0", tier0),
    )
