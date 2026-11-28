"""Planner: turns a fused campaign into concrete containment proposals.

Every proposal carries a blast radius computed on the topology (no authored
numbers) and a stable proposal_id so the Governor's decisions are idempotent.
Proposal kinds:
  NODE-QUARANTINE  isolate one asset (optionally egress-only)
  EDGE-CUT         remove one link (e.g. the crown segment uplink — the ICU cut)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..organs import Detection
from .fusion import CampaignState
from .topology import Topology


@dataclass(frozen=True, slots=True)
class Proposal:
    proposal_id: str
    campaign_id: str
    kind: str                      # EDGE-CUT | NODE-QUARANTINE
    target: str                    # edge id or node id
    edges_cut: tuple[str, ...]
    assets_severed: int
    crown_path_risk: str           # high | low
    est_recovery_hours: int
    targets_crown_gateway: bool
    target_node_is_crown: bool
    detail: str
    fallback_id: str | None = None
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "proposal_id": self.proposal_id, "campaign_id": self.campaign_id,
            "kind": self.kind, "target": self.target, "edges_cut": list(self.edges_cut),
            "assets_severed": self.assets_severed, "crown_path_risk": self.crown_path_risk,
            "est_recovery_hours": self.est_recovery_hours,
            "targets_crown_gateway": self.targets_crown_gateway,
            "target_node_is_crown": self.target_node_is_crown,
            "detail": self.detail, "fallback_id": self.fallback_id,
            "payload": self.payload,
        }


class Planner:
    def __init__(self, topology: Topology) -> None:
        self._topo = topology

    def _node_quarantine(self, campaign: CampaignState, node_id: str, egress_only: bool,
                         detail: str, fallback_id: str | None = None) -> Proposal | None:
        topo = self._topo
        if node_id not in topo.nodes:
            return None
        edges = topo.outbound_edges(node_id) if egress_only else [
            e for e in topo.edges if node_id in (e["src"], e["dst"])
        ]
        edges = [e for e in edges if not (egress_only is False and topo.is_crown(e["src"]) and e.get("crown_gateway"))]
        if not edges:
            return None
        severed = topo.severed_by_node_quarantine(node_id, outbound_only=egress_only)
        gateway = topo.crown_gateway_in([e["id"] for e in edges])
        proposal_id = f"PROP-{campaign.campaign_id}-{node_id}{'-EGRESS' if egress_only else ''}"
        return Proposal(
            proposal_id=proposal_id, campaign_id=campaign.campaign_id,
            kind="NODE-QUARANTINE", target=node_id,
            edges_cut=tuple(e["id"] for e in edges),
            assets_severed=len(severed),
            crown_path_risk="high" if gateway else "low",
            est_recovery_hours=4 if len(severed) <= 2 else 24,
            targets_crown_gateway=gateway,
            target_node_is_crown=topo.is_crown(node_id),
            detail=detail,
            payload={"severed_assets": sorted(severed), "mode": "egress-only" if egress_only else "full"},
        )

    def _icu_cut(self, campaign: CampaignState, host: str) -> Proposal | None:
        topo = self._topo
        gateway_edge = topo.crown_gateway_edge()
        if gateway_edge is None:
            return None
        severed = topo.severed_by_edge_cut(gateway_edge["id"])
        return Proposal(
            proposal_id=f"PROP-{campaign.campaign_id}-ICU-CUT",
            campaign_id=campaign.campaign_id,
            kind="EDGE-CUT", target=gateway_edge["id"], edges_cut=(gateway_edge["id"],),
            assets_severed=len(severed),
            crown_path_risk="high",
            est_recovery_hours=96,
            targets_crown_gateway=True,
            target_node_is_crown=False,
            detail=(f"sever the crown segment uplink to isolate {host} and everything "
                    f"downstream ({len(severed)} assets lose connectivity)"),
            fallback_id=f"PROP-{campaign.campaign_id}-{host}-EGRESS",
            payload={"severed_assets": sorted(severed), "probing_host": host},
        )

    def proposals_for(self, campaign: CampaignState) -> list[Proposal]:
        out: list[Proposal] = []
        by_organ_entity = {(d.organ, d.entity) for d in campaign.detections}
        entities_by_organ: dict[str, set[str]] = {}
        for d in campaign.detections:
            entities_by_organ.setdefault(d.organ, set()).add(d.entity)

        # poisoned vendor invoice -> quarantine the document
        if "docguard" in entities_by_organ:
            for entity in sorted(entities_by_organ["docguard"]):
                prop = self._node_quarantine(
                    campaign, entity, egress_only=False,
                    detail=f"quarantine {entity}: poisoned vendor document")
                if prop:
                    out.append(prop)
        # replayed session -> kill the session object
        if "sessionguard" in entities_by_organ:
            for entity in sorted(entities_by_organ["sessionguard"]):
                prop = self._node_quarantine(
                    campaign, entity, egress_only=False,
                    detail=f"kill {entity}: replayed session token")
                if prop:
                    out.append(prop)
        # ransomware staging or governor probing on an infra host -> the ICU cut
        # (escalate to segment severing) plus its fallback (egress-only isolation)
        escalators = sorted(entities_by_organ.get("fileguard", set()) | entities_by_organ.get("quorumguard", set()))
        hosts = [e for e in escalators if self._topo.node(e) is not None
                 and self._topo.node(e)["leg"] == "infra" and self._topo.node(e)["type"] == "host"]
        for host in hosts:
            icu = self._icu_cut(campaign, host)
            if icu:
                out.append(icu)
            lesser = self._node_quarantine(
                campaign, host, egress_only=True,
                detail=f"egress-only isolation of {host}: cuts exfil and probe paths, keeps the host reachable for forensics")
            if lesser:
                out.append(lesser)
        # de-duplicate by stable proposal id
        unique: dict[str, Proposal] = {}
        for prop in out:
            unique.setdefault(prop.proposal_id, prop)
        return list(unique.values())
