"""sentinel/shields — Ring 1, Organ 1: BEC / botnet Spectral Traffic Projector.

Maps a sliding window of active sessions into a behavioural state matrix
X in R^{N x d} and extracts the leading singular values. Scripted botnets
condense into a rank-1 ground state; humans stay spread out.

    R = sigma_1^2 / sum_i sigma_i^2      (Condensation Order Ratio)

R > ``rank1_threshold`` (default 0.72) flags a condensed cluster. The matrix is
MEAN-CENTERED (not feature-scaled): condensation is a statement about
*variance concentration*, and per-feature z-scoring would erase exactly that
signal while amplifying human noise along quiet features.

Excision: project rows onto the leading right singular vector v1. When a
rank-1 cluster is present, the two sides of the projection split at ~0 and the
TIGHTER side is the condensed botnet (condensation == low variance). Excised
session ids are returned for the perimeter drop — high-entropy human sessions
sharing the same NAT stay online.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from sentinel.shields.base_organ import BaseOrgan


class BECSpectralFilter(BaseOrgan):
    ring = "RING_1_PERIMETER_IDENTITY"
    organ = "BEC_SPECTRAL_PROJECTOR"

    def __init__(self, rank1_threshold: float = 0.72, **kwargs: Any):
        super().__init__(**kwargs)
        self.rank1_threshold = rank1_threshold
        self.register_rpc("drop_bec_cluster", self._rpc_drop_cluster)

    # ------------------------------------------------------------------ #
    def analyze(self, session_matrix: Any, session_ids: Optional[List[str]] = None,
                k: int = 5) -> Dict[str, Any]:
        """Analyze one window. Returns condensation ratio, singular values and
        the excised bot-cluster indices."""
        X = np.asarray(session_matrix, dtype=np.float64)
        if X.ndim != 2 or X.shape[0] < 4:
            raise ValueError("need an (n_sessions >= 4, n_features) matrix")
        if not np.isfinite(X).all():
            raise ValueError("session matrix contains non-finite values")

        Z = X - X.mean(axis=0)  # center only — see module docstring
        U, sigma, Vt = np.linalg.svd(Z, full_matrices=False)
        k = max(1, min(k, sigma.shape[0]))
        s2 = sigma[:k] ** 2
        total = float(s2.sum())
        ratio = float(s2[0] / total) if total > 0 else 0.0
        is_rank1 = ratio > self.rank1_threshold

        excised: List[int] = []
        projection_gap = 0.0
        if is_rank1:
            proj = Z @ Vt[0]
            pos = proj >= 0
            neg = ~pos
            var_pos = float(proj[pos].var()) if pos.any() else np.inf
            var_neg = float(proj[neg].var()) if neg.any() else np.inf
            bot_mask = pos if var_pos <= var_neg else neg
            excised = np.where(bot_mask)[0].tolist()
            projection_gap = abs(float(proj[bot_mask].mean()) - float(proj[~bot_mask].mean())) \
                if (bot_mask.any() and (~bot_mask).any()) else 0.0

        event = None
        if is_rank1:
            event = self.emit(
                "RANK1_CONDENSATION_DETECTED",
                severity=min(1.0, ratio),
                entities={"host_id": "HOST_GATEWAY_01", "vlan_id": "VLAN_CORP_IT",
                          "cluster_id": "CLUS_RANK1_ACTIVE"},
                metrics={"condensation_ratio": round(ratio, 4),
                         "sessions_excised": len(excised),
                         "projection_gap": round(projection_gap, 3)},
                # Part 4 Phase 2: the event's own reason. The generic fallback
                # said "BEC_SPECTRAL_PROJECTOR reported RANK1_CONDENSATION_DETECTED
                # at severity 0.773" — true, and useless to an analyst who wants
                # to know why the organ believed it. This states the measurement.
                reason=(f"{len(excised)} of {X.shape[0]} sessions collapse onto one "
                        f"direction (sigma1 share {ratio:.3f}, threshold "
                        f"{self.rank1_threshold}); mean projection gap "
                        f"{projection_gap:.2f} between the two groups"),
            )

        ids = session_ids or [f"sess_{i:04d}" for i in range(X.shape[0])]
        return {
            "condensation_ratio": ratio,
            "singular_values": sigma.tolist(),
            "is_rank1_botnet": bool(is_rank1),
            "excised_session_indices": excised,
            "excised_session_ids": [ids[i] for i in excised],
            "projection_gap": projection_gap,
            "event": event,
        }

    # ------------------------------------------------------------------ #
    def _rpc_drop_cluster(self, args: Dict[str, Any]) -> Dict[str, Any]:
        ttl = int(args.get("ttl_seconds", 3600))
        return {"status": "CLUSTER_DROPPED", "cluster_id": args.get("cluster_id"), "ttl_seconds": ttl}

    def drop_cluster(self, cluster_id: str, ttl_seconds: int = 3600) -> Dict[str, Any]:
        return self._rpc_drop_cluster({"cluster_id": cluster_id, "ttl_seconds": ttl_seconds})
