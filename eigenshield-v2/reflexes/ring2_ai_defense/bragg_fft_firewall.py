"""PLANE 1 — Ring 2, Organ 3: Bragg Crystallography Input Firewall.

Two sub-millisecond spectral gates for untrusted external text before it
reaches a corporate AI agent's tool loop:

1. 1-D reciprocal-lattice FFT ("Bragg diffraction"): tokens are embedded with a
   deterministic hashing projection; the channel-energy series is FFTed to find
   sharp periodic peaks created by adversarial repeated suffixes.
2. Attention-graph Fiedler eigenvalue (lambda_2): algebraic connectivity of the
   k-nearest-neighbour token graph. Plain-English injections fracture
   connectivity between system-prompt context and external document tokens,
   collapsing lambda_2.

Both checks are heuristic detectors with calibrated thresholds, not proofs.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List

import numpy as np

from reflexes.base_organ import BaseOrgan

_EMBED_DIM = 64
_TOKEN_RE = re.compile(r"[A-Za-z0-9_']+")


def _embed_token(token: str, dim: int = _EMBED_DIM) -> np.ndarray:
    digest = hashlib.sha256(token.lower().encode()).digest()
    rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
    return rng.standard_normal(dim)


def _embed_text(text: str) -> np.ndarray:
    tokens = _TOKEN_RE.findall(text)
    if not tokens:
        return np.zeros((0, _EMBED_DIM))
    return np.stack([_embed_token(t) for t in tokens])


def _fiedler_lambda2(A: np.ndarray) -> float:
    """Algebraic connectivity of a symmetric weighted adjacency matrix."""
    deg = A.sum(axis=1)
    D = np.diag(np.maximum(deg, 1e-12))
    L = D - A
    try:
        eigvals = np.linalg.eigvalsh(L)
    except np.linalg.LinAlgError:
        return 0.0
    eigvals = np.sort(eigvals)
    return float(max(0.0, eigvals[1])) if eigvals.size > 1 else 0.0


class BraggFFTFirewall(BaseOrgan):
    ring = "RING_2_AI_DEFENSE"
    organ = "BRAGG_FFT_FIREWALL"

    def __init__(self, bragg_peak_threshold: float = 0.32, fiedler_threshold: float = 0.05,
                 knn: int = 4, **kwargs: Any):
        super().__init__(**kwargs)
        self.bragg_peak_threshold = bragg_peak_threshold
        self.fiedler_threshold = fiedler_threshold
        self.knn = knn
        self.register_rpc("quarantine_ai_document", self._rpc_quarantine)

    # ------------------------------------------------------------------ #
    def bragg_peak_ratio(self, text: str) -> float:
        E = _embed_text(text)
        if E.shape[0] < 8:
            return 0.0
        series = np.linalg.norm(E, axis=1)
        series = series - series.mean()
        spectrum = np.abs(np.fft.rfft(series)) ** 2
        if spectrum.size <= 1:
            return 0.0
        ac = spectrum[1:]  # drop DC
        total = ac.sum()
        return float(ac.max() / total) if total > 0 else 0.0

    def fiedler_lambda2(self, text: str) -> float:
        E = _embed_text(text)
        n = E.shape[0]
        if n < 6:
            return 1.0  # too small to judge; do not flag
        E = E / np.maximum(np.linalg.norm(E, axis=1, keepdims=True), 1e-12)
        sim = E @ E.T
        A = np.zeros_like(sim)
        k = min(self.knn, n - 1)
        for i in range(n):
            idx = np.argsort(-sim[i])[1:k + 1]
            A[i, idx] = np.clip(sim[i, idx], 0.0, None)
        A = np.maximum(A, A.T)
        return _fiedler_lambda2(A)

    def screen(self, text: str, agent_id: str = "agent_unknown",
               doc_hash: str = "sha256:unknown") -> Dict[str, Any]:
        peak = self.bragg_peak_ratio(text)
        lam2 = self.fiedler_lambda2(text)
        flags: List[str] = []
        if peak > self.bragg_peak_threshold:
            flags.append("BRAGG_PEAK")
        if lam2 < self.fiedler_threshold:
            flags.append("FIEDLER_FRACTURE")
        allowed = not flags

        result: Dict[str, Any] = {
            "allowed": allowed,
            "bragg_peak_ratio": peak,
            "fiedler_lambda2": lam2,
            "flags": flags,
            "action": "PASS" if allowed else "BLOCK_AND_QUARANTINE",
        }
        if not allowed:
            self.emit(
                "INDIRECT_INJECTION_BLOCKED",
                severity=min(1.0, 0.5 + peak),
                entities={"doc_hash": doc_hash, "agent_id": agent_id,
                          "host_id": "HOST_APP_SRV_07", "vlan_id": "VLAN_CORP_IT"},
                metrics={"bragg_peak_ratio": round(peak, 4), "fiedler_lambda2": round(lam2, 4)},
            )
            result["quarantine"] = self._rpc_quarantine({"doc_hash": doc_hash, "agent_id": agent_id})
        return result

    # ------------------------------------------------------------------ #
    def _rpc_quarantine(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "DOCUMENT_QUARANTINED", "doc_hash": args.get("doc_hash"),
                "agent_id": args.get("agent_id")}
