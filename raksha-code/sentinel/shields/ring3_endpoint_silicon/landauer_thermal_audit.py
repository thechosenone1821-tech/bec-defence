"""sentinel/shields — Ring 3, Organ 6: Landauer Thermodynamic Spyware Auditor.

Single-bit Landauer dissipation (E >= k_B T ln 2) sits below ambient thermal
noise, so we audit *macroscopic* silicon telemetry instead: a linear observer
fitted on benign baselines predicts package power from retired-instruction
rate (IPC) and die temperature. Persistent

    delta_Q_unaccounted = E_silicon - f_SSM(IPC_visible, T_die)

flags covert rootkit threads even when every userspace hook is blinded.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from sentinel.shields.base_organ import BaseOrgan

# Landauer limit at ~310 K, shown for context in reports.
K_BOLTZMANN = 1.380649e-23
LANDAUER_LIMIT_J = K_BOLTZMANN * 310.0 * np.log(2.0)


class LandauerThermalAudit(BaseOrgan):
    ring = "RING_3_ENDPOINT_SILICON"
    organ = "LANDAUER_THERMAL_AUDITOR"

    def __init__(self, residual_threshold_w: float = 8.0, sustain_samples: int = 5,
                 **kwargs: Any):
        super().__init__(**kwargs)
        self.residual_threshold_w = residual_threshold_w
        self.sustain_samples = sustain_samples
        self._coef: np.ndarray | None = None
        self._unaccounted_window: List[float] = []
        self.register_rpc("isolate_thermal_anomaly_host", self._rpc_isolate)

    # ------------------------------------------------------------------ #
    def calibrate(self, samples: List[Dict[str, float]]) -> Dict[str, Any]:
        """Fit power ~= a*IPC + b*T_die + c on >= 10 benign samples."""
        if len(samples) < 10:
            raise ValueError("need >= 10 benign samples to calibrate")
        A = np.array([[s["ipc"], s["temp_c"], 1.0] for s in samples])
        y = np.array([s["power_w"] for s in samples])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        self._coef = coef
        resid = y - A @ coef
        return {"coef_ipc_w": float(coef[0]), "coef_temp_w_per_c": float(coef[1]),
                "intercept_w": float(coef[2]), "baseline_residual_std_w": float(resid.std())}

    def landauer_floor(self, bit_ops_per_sec: float) -> float:
        """Theoretical floor (watts) for bit erasures at 310 K. Context only."""
        return float(bit_ops_per_sec * LANDAUER_LIMIT_J)

    def audit(self, power_w: float, ipc: float, temp_c: float,
              host_id: str = "HOST_042") -> Dict[str, Any]:
        if self._coef is None:
            raise RuntimeError("calibrate() first")
        predicted = float(self._coef @ np.array([ipc, temp_c, 1.0]))
        residual = float(power_w - predicted)
        self._unaccounted_window.append(residual)
        self._unaccounted_window = self._unaccounted_window[-self.sustain_samples:]

        sustained = (len(self._unaccounted_window) >= self.sustain_samples
                     and all(r > self.residual_threshold_w for r in self._unaccounted_window))

        result: Dict[str, Any] = {
            "host_id": host_id,
            "power_w": power_w,
            "predicted_w": predicted,
            "unaccounted_w": residual,
            "sustained_anomaly": sustained,
            "window": list(self._unaccounted_window),
        }
        if sustained:
            self.emit(
                "UNACCOUNTED_POWER_RESIDUAL",
                severity=min(1.0, residual / (3 * self.residual_threshold_w)),
                entities={"host_id": host_id, "vlan_id": "VLAN_CORP_IT"},
                metrics={"unaccounted_watts": round(residual, 2),
                         "sustain_samples": self.sustain_samples},
            )
            result["action"] = "ISOLATE_HOST_RECOMMENDED"
        return result

    # ------------------------------------------------------------------ #
    def _rpc_isolate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "HOST_ISOLATED", "host_id": args.get("host_id"),
                "dump_hardware_trace": bool(args.get("dump_hardware_trace", True))}
