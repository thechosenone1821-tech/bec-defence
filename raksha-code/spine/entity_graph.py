"""SPINE — 10-minute sliding-window attack graph.

v0.1 scope: nodes/edges (SESSION -> USER -> HOST -> VLAN -> SERVICE) plus a
deterministic campaign correlator — events sharing >= 1 entity token inside
the window are unioned into one campaign. This is the smallest honest
version of cross-layer correlation; temporal kernels and weighted fingerprints
are Phase-2 work. The Commander receives the compact snapshot payload — never
raw logs.
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from packages.contracts.entities import ENTITY_PATH
except ImportError:  # pragma: no cover - minimal standalone checkout
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from packages.contracts.entities import ENTITY_PATH

_WINDOW_SEC = 600


class EntityGraph:
    def __init__(self, window_sec: int = _WINDOW_SEC):
        self.window_sec = window_sec
        self._edges: List[Tuple[float, str, str, str]] = []  # (ts, src, dst, kind)
        self._nodes: Dict[str, float] = {}
        self._events: List[Tuple[float, str, float, Tuple[str, ...]]] = []  # (ts, event_id, severity, tokens)

    # ------------------------------------------------------------------ #
    def add_event(self, event: Dict[str, Any]) -> None:
        ts = time.time()
        ent = event.get("entities", {}) or {}
        chain = [ent[k] for k in ENTITY_PATH if ent.get(k)]
        for node in chain:
            self._nodes[str(node)] = ts
        for a, b in zip(chain, chain[1:]):
            self._edges.append((ts, str(a), str(b), "linked"))
        tokens = tuple(sorted({str(v) for v in ent.values() if v}))
        try:
            severity = float(event.get("severity", 0.0))
        except (TypeError, ValueError):
            severity = 0.0
        self._events.append((ts, str(event.get("event_id") or f"evt_anon_{int(ts * 1000)}"),
                             severity, tokens))
        self.prune(ts)

    def prune(self, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        cutoff = now - self.window_sec
        self._edges = [e for e in self._edges if e[0] >= cutoff]
        self._nodes = {n: t for n, t in self._nodes.items() if t >= cutoff}
        self._events = [e for e in self._events if e[0] >= cutoff]

    # ------------------------------------------------------------------ #
    def campaigns(self) -> List[Dict[str, Any]]:
        """Union-find over events sharing >= 1 entity token.

        Deterministic: campaign_id is the hash of sorted member event_ids.
        Singleton events form their own single-event campaign — honest v0.
        """
        self.prune()
        parent = list(range(len(self._events)))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i: int, j: int) -> None:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[ri] = rj

        token_owner: Dict[str, int] = {}
        for idx, (_, _, _, tokens) in enumerate(self._events):
            for tok in tokens:
                if tok in token_owner:
                    union(idx, token_owner[tok])
                else:
                    token_owner[tok] = idx

        groups: Dict[int, List[int]] = {}
        for idx in range(len(self._events)):
            groups.setdefault(find(idx), []).append(idx)

        out: List[Dict[str, Any]] = []
        for members in groups.values():
            ids = sorted(self._events[m][1] for m in members)
            ents = sorted({tok for m in members for tok in self._events[m][3]})
            sev = max(self._events[m][2] for m in members)
            first = min(self._events[m][0] for m in members)
            last = max(self._events[m][0] for m in members)
            cid = "cmp_" + hashlib.sha256(",".join(ids).encode()).hexdigest()[:10]
            out.append({"campaign_id": cid, "size": len(members),
                        "event_ids": ids, "entities": ents[:50],
                        "severity_max": round(sev, 3),
                        "first_ts": first, "last_ts": last})
        out.sort(key=lambda c: (c["size"], c["severity_max"]), reverse=True)
        return out

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
