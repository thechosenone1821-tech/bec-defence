"""sentinel/shields — Ring 2, Organ 4: Hessian-Curvature Lyapunov Guardrail.

Aligned inference trajectories stay inside a flat, stable valley of the
activation landscape; jailbreaks shove hidden states onto sharp, high-curvature
cliffs. We estimate *directional curvature* along the activation velocity with
a finite-difference Hessian-vector-product proxy:

    v_t   = h_t - h_{t-1}
    a_t   = v_t - v_{t-1}                    (second-order step)
    kappa = (a_t . v_t) / ||v_t||^2          (directional curvature proxy)

When |kappa| crosses the cliff threshold, a Lyapunov restoring vector nudges
the state back toward the aligned manifold (mid-inference steering). This is an
engineering approximation of the spec's HVP probe, honest about its limits: it
detects *trajectory jerk*, not true second-order geometry of the model's loss.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from sentinel.shields.base_organ import BaseOrgan


class HessianLyapunovGuard(BaseOrgan):
    ring = "RING_2_AI_DEFENSE"
    organ = "HESSIAN_LYAPUNOV_GUARD"

    def __init__(self, cliff_threshold: float = 2.5, stiffness_gain: float = 0.35,
                 max_history: int = 64, **kwargs: Any):
        super().__init__(**kwargs)
        self.cliff_threshold = cliff_threshold
        self.stiffness_gain = stiffness_gain
        self.max_history = max_history
        self._history: List[np.ndarray] = []
        self.register_rpc("clamp_lyapunov_steering", self._rpc_clamp)

    def reset(self) -> None:
        self._history = []

    # ------------------------------------------------------------------ #
    def directional_curvature(self, v_t: np.ndarray, v_prev: np.ndarray) -> float:
        denom = float(np.dot(v_t, v_t))
        if denom < 1e-12:
            return 0.0
        a_t = v_t - v_prev
        return float(np.dot(a_t, v_t) / denom)

    def step(self, h_t: Any, model_id: str = "agent_llm_local") -> Dict[str, Any]:
        h = np.asarray(h_t, dtype=np.float64).ravel()
        self._history.append(h)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

        result: Dict[str, Any] = {"model_id": model_id, "kappa": 0.0, "action": "STEER_NONE",
                                  "deflected": False}
        if len(self._history) < 3:
            return result

        v_t = self._history[-1] - self._history[-2]
        v_prev = self._history[-2] - self._history[-3]
        kappa = self.directional_curvature(v_t, v_prev)
        result["kappa"] = kappa

        if abs(kappa) > self.cliff_threshold:
            # Lyapunov restoring vector: pull state back along the velocity,
            # scaled by curvature excess (sign opposes the adversarial push).
            v_norm = np.linalg.norm(v_t)
            if v_norm > 1e-12:
                restore = -np.sign(kappa) * self.stiffness_gain * (abs(kappa) / self.cliff_threshold) * (v_t / v_norm)
                result["restored_state"] = (h + restore).tolist()
                result["deflected"] = True
                result["action"] = "LYAPUNOV_RESTORED"
                self.emit(
                    "JAILBREAK_TRAJECTORY_DEFLECTED",
                    severity=min(1.0, abs(kappa) / (2 * self.cliff_threshold)),
                    entities={"host_id": "HOST_APP_SRV_07", "vlan_id": "VLAN_CORP_IT",
                              "agent_id": model_id},
                    metrics={"kappa": round(kappa, 4), "cliff_threshold": self.cliff_threshold},
                )
        return result

    def kappa_series(self, hidden_states: Any) -> List[float]:
        self.reset()
        out = []
        for h in hidden_states:
            out.append(self.step(h)["kappa"])
        return out

    # ------------------------------------------------------------------ #
    def _rpc_clamp(self, args: Dict[str, Any]) -> Dict[str, Any]:
        self.stiffness_gain = float(args.get("stiffness_gain", self.stiffness_gain))
        return {"status": "STEERING_CLAMPED", "model_id": args.get("model_id"),
                "stiffness_gain": self.stiffness_gain}
