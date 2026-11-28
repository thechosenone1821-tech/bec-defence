"""Phase 7 — one deterministic safety brain.

One exhaustive/blast-radius planner produces proposals. One Governor rules on
them. One dry-run executor may simulate an approved proposal. Crown-jewel and
Tier-0 assets are excluded from the planner and rejected by the Proposal type
itself, so a crown cut is impossible by construction. There is no override and
no live Commander path: refusals are first-class decisions to be ledgered by
the runtime.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from packages.contracts.canonical import canonical_hash
from packages.contracts.config import DEFAULT_TOPOLOGY

PLANNER_ID = "ExhaustivePlanner-v1"
GOVERNOR_ID = "Phase7Governor-v1"
EXECUTOR_ID = "DryRunExecutor-v1"
VERDICT_ALLOWED = "ALLOWED"
VERDICT_REFUSED = "REFUSED"

ALLOWED_ACTIONS = ("edge_cut", "node_quarantine", "egress_only_isolation")


class UnsafeProposal(ValueError):
    """Raised when code attempts to construct a structurally unsafe proposal."""


@dataclass(frozen=True)
class Topology:
    nodes: dict[str, dict[str, Any]]
    edges: tuple[dict[str, Any], ...]
    crown_assets: frozenset[str]
    crown_gateway_edges: frozenset[str]

    @classmethod
    def from_path(cls, path: str | Path | None = None) -> "Topology":
        raw = json.loads(Path(path or DEFAULT_TOPOLOGY).read_text(encoding="utf-8"))
        nodes: dict[str, dict[str, Any]] = {}
        crown_vlans = {
            str(v["id"]) for v in raw.get("vlans", [])
            if int(v.get("tier", 99)) == 0 or v.get("criticality") == "crown_jewel"
        }
        for vlan in raw.get("vlans", []):
            node_id = str(vlan["id"])
            crown = node_id in crown_vlans
            nodes[node_id] = {"id": node_id, "kind": "vlan", "tier": vlan.get("tier"),
                              "crown": crown, "leg": "infra"}
        for host in raw.get("hosts", []):
            node_id = str(host["id"])
            home = str(host.get("vlan") or "")
            crown = (int(host.get("tier", 99)) == 0
                     or host.get("criticality") == "crown_jewel"
                     or home in crown_vlans)
            nodes[node_id] = {"id": node_id, "kind": "host", "tier": host.get("tier"),
                              "vlan": home, "role": host.get("role"), "crown": crown,
                              "leg": "infra"}
        edges: list[dict[str, Any]] = []
        for index, edge in enumerate(raw.get("edges", [])):
            src, dst = str(edge["a"]), str(edge["b"])
            edge_id = str(edge.get("id") or f"EDGE-{index:02d}-{src}-{dst}")
            gateway = (src in crown_vlans or dst in crown_vlans
                       or edge.get("criticality") == "crown_jewel"
                       or nodes.get(src, {}).get("crown") is True
                       or nodes.get(dst, {}).get("crown") is True)
            weight = edge.get("weight")
            edges.append({
                "id": edge_id, "src": src, "dst": dst, "weight": weight,
                "crown_gateway": gateway,
                "carries_traffic": weight is not None and not gateway,
                "criticality": edge.get("criticality"),
            })
        return cls(
            nodes=nodes, edges=tuple(edges),
            crown_assets=frozenset(node_id for node_id, node in nodes.items() if node["crown"]),
            crown_gateway_edges=frozenset(e["id"] for e in edges if e["crown_gateway"]),
        )

    def edge(self, edge_id: str) -> dict[str, Any] | None:
        return next((e for e in self.edges if e["id"] == edge_id), None)

    def is_crown(self, node_id: str) -> bool:
        return node_id in self.crown_assets

    def _incident(self, node_id: str, *, outbound_only: bool = False) -> Iterable[dict[str, Any]]:
        for edge in self.edges:
            if not edge.get("carries_traffic"):
                continue
            if outbound_only:
                if edge["src"] == node_id:
                    yield edge
            elif edge["src"] == node_id or edge["dst"] == node_id:
                yield edge

    def severed_by_edge_cut(self, edge_id: str) -> tuple[str, ...]:
        edge = self.edge(edge_id)
        if edge is None or edge.get("crown_gateway") or not edge.get("carries_traffic"):
            return ()
        seen = {edge["dst"]}
        stack = [edge["dst"]]
        while stack:
            current = stack.pop()
            for incident in self._incident(current):
                if incident["id"] == edge_id:
                    continue
                other = incident["dst"] if incident["src"] == current else incident["src"]
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
        return tuple(sorted(seen - set(self.crown_assets)))

    def affected_by_node_isolation(self, node_id: str, *, egress_only: bool = False) -> tuple[str, ...]:
        if node_id not in self.nodes or self.is_crown(node_id):
            return ()
        affected = {node_id}
        for edge in self._incident(node_id, outbound_only=egress_only):
            other = edge["dst"] if edge["src"] == node_id else edge["src"]
            if not self.is_crown(other):
                affected.add(other)
        return tuple(sorted(affected - set(self.crown_assets)))

    def legal_edges(self) -> tuple[dict[str, Any], ...]:
        return tuple(e for e in self.edges if not e["crown_gateway"] and e["carries_traffic"])

    def legal_hosts(self) -> tuple[str, ...]:
        return tuple(sorted(node_id for node_id, node in self.nodes.items()
                            if node["kind"] == "host" and not node["crown"]))

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [dict(self.nodes[k]) for k in sorted(self.nodes)],
            "edges": [dict(e) for e in self.edges],
            "crown_assets": sorted(self.crown_assets),
            "crown_gateway_edges": sorted(self.crown_gateway_edges),
        }


@dataclass(frozen=True)
class Proposal:
    campaign_id: str
    action: str
    entity: str
    assets_severed: tuple[str, ...]
    edges_cut: tuple[str, ...]
    blast_radius: tuple[str, ...]
    detail: str
    fallback_proposal_id: str | None
    planner_id: str
    crown_assets: frozenset[str]
    crown_gateway_edges: frozenset[str]
    proposal_id: str = field(init=False)

    def __post_init__(self) -> None:
        if self.planner_id != PLANNER_ID:
            raise UnsafeProposal("proposal did not come from the canonical planner")
        if self.action not in ALLOWED_ACTIONS:
            raise UnsafeProposal(f"action {self.action!r} is not dry-run allowlisted")
        touched = set(self.assets_severed) | set(self.blast_radius) | {self.entity}
        crown_hits = sorted(touched & set(self.crown_assets))
        if crown_hits:
            raise UnsafeProposal(f"crown/Tier-0 assets cannot be severed: {crown_hits}")
        gateway_hits = sorted(set(self.edges_cut) & set(self.crown_gateway_edges))
        if gateway_hits:
            raise UnsafeProposal(f"crown gateway edges cannot be cut: {gateway_hits}")
        body = {
            "campaign_id": self.campaign_id, "action": self.action,
            "entity": self.entity, "assets_severed": list(self.assets_severed),
            "edges_cut": list(self.edges_cut), "blast_radius": list(self.blast_radius),
            "detail": self.detail, "fallback": self.fallback_proposal_id,
        }
        object.__setattr__(self, "proposal_id", "P-" + canonical_hash(body)[:20])

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id, "campaign_id": self.campaign_id,
            "action": self.action, "entity": self.entity,
            "assets_severed": list(self.assets_severed),
            "edges_cut": list(self.edges_cut), "blast_radius": list(self.blast_radius),
            "detail": self.detail, "fallback_proposal_id": self.fallback_proposal_id,
            "planner_id": self.planner_id, "dry_run": True,
        }


@dataclass(frozen=True)
class Decision:
    proposal_id: str
    verdict: str
    reason: str
    rule_id: str
    fallback_proposal_id: str | None
    assets_severed: tuple[str, ...]
    blast_radius: int
    governor_id: str = GOVERNOR_ID

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id, "verdict": self.verdict,
            "reason": self.reason, "rule_id": self.rule_id,
            "fallback_proposal_id": self.fallback_proposal_id,
            "assets_severed": list(self.assets_severed),
            "blast_radius": self.blast_radius, "governor_id": self.governor_id,
            "dry_run": True, "admin_override": False,
        }


class ExhaustivePlanner:
    """Enumerate every legal edge cut, host quarantine and egress fallback."""

    def __init__(self, topology: Topology):
        self.topology = topology

    def _make(self, campaign_id: str, action: str, entity: str,
              assets: tuple[str, ...], edges: tuple[str, ...], detail: str,
              fallback: str | None) -> Proposal:
        return Proposal(
            campaign_id=campaign_id, action=action, entity=entity,
            assets_severed=assets, edges_cut=edges, blast_radius=assets,
            detail=detail, fallback_proposal_id=fallback, planner_id=PLANNER_ID,
            crown_assets=self.topology.crown_assets,
            crown_gateway_edges=self.topology.crown_gateway_edges,
        )

    def proposals_for(self, campaign: Mapping[str, Any]) -> tuple[Proposal, ...]:
        campaign_id = str(campaign.get("campaign_id") or "C-UNKNOWN")
        out: list[Proposal] = []
        fallback_by_host: dict[str, str] = {}
        for host in self.topology.legal_hosts():
            affected = self.topology.affected_by_node_isolation(host, egress_only=True)
            fallback = self._make(
                campaign_id, "egress_only_isolation", host, affected, (),
                f"egress-only isolation of {host}: preserve forensics reachability",
                None,
            )
            fallback_by_host[host] = fallback.proposal_id
            out.append(fallback)
        for host in self.topology.legal_hosts():
            affected = self.topology.affected_by_node_isolation(host)
            out.append(self._make(
                campaign_id, "node_quarantine", host, affected, (),
                f"node quarantine of {host}; fallback {fallback_by_host[host]}",
                fallback_by_host[host],
            ))
        for edge in self.topology.legal_edges():
            affected = self.topology.severed_by_edge_cut(edge["id"])
            out.append(self._make(
                campaign_id, "edge_cut", edge["dst"], affected, (edge["id"],),
                f"blast-radius edge cut {edge['id']} ({edge['src']} -> {edge['dst']})",
                None,
            ))
        unique: dict[str, Proposal] = {}
        for proposal in out:
            unique.setdefault(proposal.proposal_id, proposal)
        return tuple(unique.values())


class Governor:
    """One zero-AI Governor. It has no override method."""

    def __init__(self, *, blast_cap: int = 3):
        self.blast_cap = max(0, int(blast_cap))

    def decide(self, proposal: Proposal) -> Decision:
        if proposal.planner_id != PLANNER_ID:
            return self._refuse(proposal, "G0-UNPLANNED", "proposal lacks canonical planner provenance")
        crown_hits = sorted((set(proposal.assets_severed) | set(proposal.blast_radius)
                             | {proposal.entity}) & set(proposal.crown_assets))
        if crown_hits:
            return self._refuse(proposal, "G1-CROWN-LOCK", "crown/Tier-0 cut is impossible")
        gateway_hits = sorted(set(proposal.edges_cut) & set(proposal.crown_gateway_edges))
        if gateway_hits:
            return self._refuse(proposal, "G2-CROWN-GATEWAY", "crown gateway edge is immutable")
        if len(proposal.blast_radius) > self.blast_cap:
            return self._refuse(
                proposal, "G3-BLAST-CAP",
                f"blast radius {len(proposal.blast_radius)} exceeds cap {self.blast_cap}",
            )
        if proposal.action not in ALLOWED_ACTIONS:
            return self._refuse(proposal, "G4-NON-DRY-RUN", "action is not dry-run allowlisted")
        return Decision(
            proposal_id=proposal.proposal_id, verdict=VERDICT_ALLOWED,
            reason="crown lock intact; within deterministic blast cap; dry-run only",
            rule_id="G4-ALLOW-DRY-RUN", fallback_proposal_id=proposal.fallback_proposal_id,
            assets_severed=proposal.assets_severed, blast_radius=len(proposal.blast_radius),
        )

    def _refuse(self, proposal: Proposal, rule_id: str, reason: str) -> Decision:
        return Decision(
            proposal_id=proposal.proposal_id, verdict=VERDICT_REFUSED,
            reason=reason, rule_id=rule_id,
            fallback_proposal_id=proposal.fallback_proposal_id,
            assets_severed=proposal.assets_severed, blast_radius=len(proposal.blast_radius),
        )


class DryRunExecutor:
    """The only executor: it never performs real containment."""

    def execute(self, decision: Decision) -> dict[str, Any]:
        if decision.verdict != VERDICT_ALLOWED:
            return {
                "executor_id": EXECUTOR_ID, "status": "SKIPPED_REFUSAL",
                "executed": False, "dry_run": True, "real_action": False,
                "reason": "Governor refusal is never executed",
            }
        return {
            "executor_id": EXECUTOR_ID, "status": "SIMULATED",
            "executed": False, "dry_run": True, "real_action": False,
            "reason": "approved proposal was simulated only; no host, VLAN, process or network changed",
        }


def safety_card() -> dict[str, Any]:
    return {
        "phase": 7, "planner": PLANNER_ID, "governor": GOVERNOR_ID,
        "executor": EXECUTOR_ID, "allowed_actions": list(ALLOWED_ACTIONS),
        "crown_cuts": "impossible_by_construction",
        "admin_override": "impossible",
        "refusals": "first_class_decision_records",
        "ai_commander": "optional_fallback_only_not_run",
    }


__all__ = [
    "PLANNER_ID", "GOVERNOR_ID", "EXECUTOR_ID", "VERDICT_ALLOWED",
    "VERDICT_REFUSED", "ALLOWED_ACTIONS", "UnsafeProposal", "Topology",
    "Proposal", "Decision", "ExhaustivePlanner", "Governor", "DryRunExecutor",
    "safety_card",
]
