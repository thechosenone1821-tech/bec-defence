"""PLANE 2 — 10-minute sliding-window enterprise entity graph.

Links Session -> User -> Host -> VLAN -> App Service. The Commander receives
exactly this compact JSON payload — never raw logs.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

_WINDOW_SEC = 600

# entity_key prefix -> tier in the kill-chain path
_PATH = ["session_id", "user_id", "host_id", "vlan_id", "service_id"]


class EntityGraph:
    def __init__(self, window_sec: int = _WINDOW_SEC):
        self.window_sec = window_sec
        self._edges: List[Tuple[float, str, str, str]] = []  # (ts, src, dst, kind)
        self._nodes: Dict[str, float] = {}

    # ------------------------------------------------------------------ #
    def add_event(self, event: Dict[str, Any]) -> None:
        ts = time.time()
        ent = event.get("entities", {}) or {}
        chain = [ent[k] for k in _PATH if ent.get(k)]
        for node in chain:
            self._nodes[str(node)] = ts
        for a, b in zip(chain, chain[1:]):
            self._edges.append((ts, str(a), str(b), "linked"))
        self.prune(ts)

    def prune(self, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        cutoff = now - self.window_sec
        self._edges = [e for e in self._edges if e[0] >= cutoff]
        self._nodes = {n: t for n, t in self._nodes.items() if t >= cutoff}

    # ------------------------------------------------------------------ #
    def snapshot(self) -> Dict[str, Any]:
        self.prune()
        nodes = sorted(self._nodes)
        edges = [{"src": s, "dst": d, "kind": k} for _, s, d, k in self._edges]
        return {
            "window_sec": self.window_sec,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes[:200],
            "edges": edges[:500],
        }

    def payload(self) -> Dict[str, Any]:
        snap = self.snapshot()
        snap["chain"] = "SESSION -> USER -> HOST -> VLAN -> SERVICE"
        return snap
