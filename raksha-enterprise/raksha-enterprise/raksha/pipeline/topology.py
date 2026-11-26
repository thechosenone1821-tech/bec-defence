"""Deployment topology: the asset graph containment math runs on.

Loaded from data/topology.json (seeded from the packaged default on bootstrap).
Nodes carry crown flags; edges may be marked crown_gateway (the segment uplink
whose removal severs a whole segment). Blast radius is computed by graph
traversal — no authored numbers anywhere.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

PACKAGE_DEFAULT = "packagedata/topology_c2247.json"


@dataclass(slots=True)
class Topology:
    nodes: dict[str, dict]
    edges: list[dict]
    crown_assets: tuple[str, ...]
    _adj: dict[str, list[tuple[str, dict]]] = field(init=False)

    @classmethod
    def load(cls, path: Path | None, crown_assets: tuple[str, ...]) -> "Topology":
        if path is not None and path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
        else:
            raw = json.loads(resources.files("raksha").joinpath(PACKAGE_DEFAULT).read_text(encoding="utf-8"))
        return cls(nodes={n["id"]: n for n in raw["nodes"]}, edges=raw["edges"],
                   crown_assets=crown_assets or tuple(n["id"] for n in raw["nodes"] if n.get("crown")))

    def __post_init__(self) -> None:
        self._adj = {node_id: [] for node_id in self.nodes}
        for edge in self.edges:
            self._adj.setdefault(edge["src"], []).append((edge["dst"], edge))
            self._adj.setdefault(edge["dst"], []).append((edge["src"], edge))

    # -- lookups -------------------------------------------------------------
    def node(self, node_id: str) -> dict | None:
        return self.nodes.get(node_id)

    def is_crown(self, node_id: str) -> bool:
        return node_id in self.crown_assets

    def edge(self, edge_id: str) -> dict | None:
        for edge in self.edges:
            if edge["id"] == edge_id:
                return edge
        return None

    def crown_gateway_edge(self) -> dict | None:
        for edge in self.edges:
            if edge.get("crown_gateway"):
                return edge
        return None

    def outbound_edges(self, node_id: str) -> list[dict]:
        return [e for e in self.edges if e["src"] == node_id]

    def neighbors(self, node_id: str) -> list[str]:
        return [dst for dst, _ in self._adj.get(node_id, [])]

    # -- containment math ----------------------------------------------------
    def severed_by_edge_cut(self, edge_id: str) -> set[str]:
        """Assets that lose connectivity when this link is removed. Traversal
        follows service links only (edges carrying `carries_traffic: true`) —
        observation edges (probes, detections) are not network paths and must
        not keep a segment alive on paper. Crown assets are never counted."""
        cut = self.edge(edge_id)
        if cut is None:
            return set()

        def traversable(edge: dict) -> bool:
            return edge["id"] != edge_id and edge.get("carries_traffic") is True

        seen = {cut["dst"]}
        stack = [cut["dst"]]
        while stack:
            current = stack.pop()
            for neighbor, incident in self._adj.get(current, []):
                if not traversable(incident):
                    continue
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        return seen - set(self.crown_assets)

    def severed_by_node_quarantine(self, node_id: str, outbound_only: bool = False) -> set[str]:
        """Assets affected by isolating one node: the node itself plus its
        neighbours on the cut links (crown assets excluded — blocking traffic
        *to* a crown protects it and does not sever it)."""
        if node_id not in self.nodes or self.is_crown(node_id):
            return set()
        affected = {node_id}
        if outbound_only:
            links = self.outbound_edges(node_id)
        else:
            links = [edge for _dst, edge in self._adj.get(node_id, [])]
        for link in links:
            other = link["dst"] if link["src"] == node_id else link["src"]
            if not self.is_crown(other):
                affected.add(other)
        return affected

    def crown_gateway_in(self, edge_ids: list[str]) -> bool:
        return any((self.edge(eid) or {}).get("crown_gateway") for eid in edge_ids)

    def to_dict(self) -> dict[str, object]:
        return {
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
            "crown_assets": list(self.crown_assets),
        }
