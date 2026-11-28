"""TCB twins: two independent policy evaluators that must agree.

The Governor runs the SAME action through two separately-written evaluators.
If their verdicts (status, reason, and every metadata field) are not
identical, the decision is DENY/TCB_DISAGREEMENT. When the twins disagree,
the answer is always no -- this is what "TCB twins must agree" means in the
architecture.

TwinA is the rule-table evaluator: it computes the facts, then walks a fixed
rule list. TwinB is an independent second implementation with its own touch
checks and control flow, written so that a bug in one is unlikely to be
mirrored in the other. Both share the impact arithmetic in policy.py -- a
documented Part-1 scope decision; Part 2 duplicates the arithmetic too and
moves the twins into separate processes.

Neither twin sees the FIDO2 assertion or the budget counters. Those are
runtime state owned by the Governor proper; the twins decide what the POLICY
requires (allow / refuse / demand sign-off), the Governor then applies state
(budgets, signature verification). This split is deliberate: state cannot
influence the double-checked reasoning, and reasoning cannot mutate state.
"""
from __future__ import annotations

from .decisions import Decision, DENY, ESCALATE, ALLOW, explain
from .fixtures import Topology
from .policy import metadata_for, severed_critical_weight, projected_uptime
from .tools import Action, TOOL_REGISTRY


class TwinA:
    """Rule-table policy evaluator (the primary readable implementation)."""

    name = "twin-a (rule table)"

    def evaluate(
        self,
        action: Action,
        topology: Topology,
        uptime_current: float,
        floor: float,
        is_revert: bool = False,
    ) -> Decision:
        from .policy import assess

        spec = TOOL_REGISTRY[action.tool]
        # Read-only tools never trigger the crown or Tier-0 locks: the locks
        # exist to stop disruption, and both twins apply the same gate.
        crown, tier0, severed, projected = assess(
            action, topology, uptime_current, floor
        )
        crown = spec.disruptive and crown
        tier0 = spec.disruptive and tier0
        md = metadata_for(spec, crown, tier0, severed, projected)

        # Rule 1 -- crown-jewel lock. Absolute. Checked before everything.
        if crown:
            return Decision(
                DENY,
                "CROWN_JEWEL_LOCK",
                md,
                explain("CROWN_JEWEL_LOCK", f"{action.tool} targets the ICU VLAN"),
            )
        # Rule 2 -- uptime floor. Absolute. No sign-off can buy this.
        # A forced REVERT skips this check: the floor pre-check exists to
        # stop actions that DAMAGE critical uptime, and a restore can only
        # give service back. The floor was already broken -- that is why the
        # watchdog is reverting at all.
        if (not is_revert) and projected < floor:
            return Decision(
                DENY,
                "UPTIME_FLOOR",
                md,
                explain(
                    "UPTIME_FLOOR",
                    f"projected {projected:.5f} < floor {floor:.5f}",
                ),
            )
        # Rule 3 -- Tier-0 step-up requirement (the Governor verifies the
        # actual signature; the twin only decides that sign-off is required).
        if tier0:
            return Decision(
                ESCALATE,
                "FIDO2_REQUIRED",
                md,
                explain("FIDO2_REQUIRED", f"{action.tool} touches a Tier-0 asset"),
            )
        return Decision(
            ALLOW, "ALLOWED_STANDARD", md, explain("ALLOWED_STANDARD", action.tool)
        )


class TwinB:
    """Independent second implementation of the same policy.

    Written differently on purpose: own touch checks, own loop over edges,
    guard cascade composed the other way round. Same semantics, different
    code -- that is the whole point.
    """

    name = "twin-b (independent)"

    def evaluate(
        self,
        action: Action,
        topology: Topology,
        uptime_current: float,
        floor: float,
        is_revert: bool = False,
    ) -> Decision:
        spec = TOOL_REGISTRY[action.tool]
        crown = spec.disruptive and self._touches_crown(action, topology)
        tier0 = spec.disruptive and self._touches_tier0(action, topology)
        severed = self._severed(action, topology)
        projected = projected_uptime(
            uptime_current, severed, topology.total_critical_weight()
        )
        md = metadata_for(spec, crown, tier0, severed, projected)

        # A forced revert skips the floor check (see TwinA rule 2): the
        # uptime is already below floor -- reverting is the remedy.
        floor_broken = (projected < floor) and not is_revert

        if not crown and not floor_broken and not tier0:
            return Decision(
                ALLOW,
                "ALLOWED_STANDARD",
                md,
                explain("ALLOWED_STANDARD", action.tool),
            )
        if crown:
            return Decision(
                DENY,
                "CROWN_JEWEL_LOCK",
                md,
                explain(
                    "CROWN_JEWEL_LOCK",
                    f"ICU VLAN asset involved: {action.tool}",
                ),
            )
        if floor_broken:
            return Decision(
                DENY,
                "UPTIME_FLOOR",
                md,
                explain(
                    "UPTIME_FLOOR",
                    f"critical uptime would fall to {projected:.5f}, "
                    f"floor is {floor:.5f}",
                ),
            )
        return Decision(
            ESCALATE,
            "FIDO2_REQUIRED",
            md,
            explain("FIDO2_REQUIRED", f"Tier-0 asset involved: {action.tool}"),
        )

    # --- private, independently written touch checks ---

    def _touches_crown(self, action: Action, topo: Topology) -> bool:
        crown_vlan = topo.crown_vlan
        host = action.params.get("host")
        if host is not None:
            if topo.hosts.get(host) == crown_vlan:
                return True
        if action.tool == "vlan.move" and action.params.get("to_vlan") == crown_vlan:
            return True
        edge_id = action.params.get("edge")
        if edge_id is not None:
            edge = topo.edges.get(edge_id)
            if edge is not None and crown_vlan in {
                topo.hosts.get(edge.a), topo.hosts.get(edge.b)
            }:
                return True
        return False

    def _touches_tier0(self, action: Action, topo: Topology) -> bool:
        if action.tool == "creds.rotate":
            return action.params.get("identity") in topo.tier0_identities
        if action.tool == "firewall.rule.remove":
            return False
        hosts_to_check = set(topo.tier0_hosts) | {
            h for h in topo.hosts if topo.is_crown_host(h)
        }
        host = action.params.get("host")
        if host is not None and host in hosts_to_check:
            return True
        if action.tool == "vlan.move":
            return False  # moving ONTO a tier0 host name is not a thing
        edge_id = action.params.get("edge")
        if edge_id is not None:
            edge = topo.edges.get(edge_id)
            if edge is not None and (
                edge.a in hosts_to_check or edge.b in hosts_to_check
            ):
                return True
        return False

    def _severed(self, action: Action, topo: Topology) -> float:
        tool = action.tool
        if tool in {"host.quarantine", "vlan.move"}:
            host = action.params["host"]
            return sum(
                e.weight
                for e in topo.edges.values()
                if e.critical and (e.a == host or e.b == host)
            )
        if tool in {"edge.sever", "firewall.rule.add"}:
            edge = topo.edges.get(action.params["edge"])
            return edge.weight if (edge is not None and edge.critical) else 0.0
        return 0.0


DEFAULT_TWINS = (TwinA(), TwinB())
