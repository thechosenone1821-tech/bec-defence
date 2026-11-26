"""sentinel/shields — Ring 1, Organ 2: Fluid Boundary-Layer Cookie Killer.

Models an authenticated user's micro-scrolling / cursor inertia / pause cadence
as a laminar 1-D viscous flow. A rolling Behavioral Reynolds number

    Re_beh = 1000 * rho_cadence * v_norm * L_norm / mu_baseline
    v_norm = v_cursor / 1000 px/s   (screen-widths per second)
    L_norm = l_nav    / 500 px      (scroll depth units)

is the direct analog of pipe-flow transition: laminar humans Re_beh < ~1400,
turbulent replays Re_beh >> Re_crit (default 2300 — the pipe-flow constant,
kept deliberately so the physics reads honestly).

On transition the session is revoked and FIDO2 re-auth is forced (< 5 ms).
``calibrate_baseline`` fits mu_baseline per user from benign history, since a
power user's laminar ceiling is higher than a casual user's.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import numpy as np

from sentinel.shields.base_organ import BaseOrgan


def _reynolds(rho_cadence: float, v_cursor: float, l_nav: float, mu: float) -> float:
    v_norm = v_cursor / 1000.0
    l_norm = l_nav / 500.0
    return float(1000.0 * rho_cadence * v_norm * l_norm / max(mu, 1e-6))


class CookieFluidTurbulence(BaseOrgan):
    ring = "RING_1_PERIMETER_IDENTITY"
    organ = "COOKIE_FLUID_TURBULENCE"

    def __init__(self, re_crit: float = 2300.0, window: int = 32, **kwargs: Any):
        super().__init__(**kwargs)
        self.re_crit = re_crit
        self.window = window
        self._baseline_viscosity: Optional[float] = None
        self._cursor_vel: list[float] = []
        self.register_rpc("revoke_turbulent_session", self._rpc_revoke)

    # ------------------------------------------------------------------ #
    def behavioral_reynolds(self, rho_cadence: float, v_cursor: float,
                            l_nav: float, mu_baseline: Optional[float] = None) -> float:
        mu = mu_baseline if mu_baseline is not None else (self._baseline_viscosity or 1.0)
        return _reynolds(rho_cadence, v_cursor, l_nav, mu)

    def calibrate_baseline(self, samples: list[Dict[str, float]]) -> Dict[str, float]:
        """Fit mu_baseline from >= 8 benign samples.
        Each sample: rho_cadence, v_cursor (px/s), l_nav (px), optional re_observed
        (defaults to a mid-laminar 1100)."""
        if len(samples) < 8:
            raise ValueError("need >= 8 benign samples to calibrate")
        visc = []
        for s in samples:
            re_obs = float(s.get("re_observed", 1100.0))
            visc.append(1000.0 * s["rho_cadence"] * (s["v_cursor"] / 1000.0)
                        * (s["l_nav"] / 500.0) / max(re_obs, 1e-6))
        self._baseline_viscosity = float(np.median(visc))
        return {"mu_baseline": self._baseline_viscosity, "n": len(samples)}

    def observe(self, rho_cadence: float, v_cursor: float, l_nav: float,
                session_id: str = "sess_unknown", user_id: str = "USER_UNKNOWN",
                host_id: Optional[str] = None) -> Dict[str, Any]:
        """Feed one telemetry sample; returns regime + revocation decision."""
        self._cursor_vel.append(v_cursor)
        if len(self._cursor_vel) > self.window:
            self._cursor_vel = self._cursor_vel[-self.window:]

        re_beh = self.behavioral_reynolds(rho_cadence, v_cursor, l_nav)
        if re_beh < 0.6 * self.re_crit:
            regime = "laminar"
        elif re_beh < self.re_crit:
            regime = "transitional"
        else:
            regime = "turbulent"

        result: Dict[str, Any] = {
            "session_id": session_id,
            "user_id": user_id,
            "re_beh": re_beh,
            "re_crit": self.re_crit,
            "regime": regime,
            "ts": time.time(),
        }

        if regime == "turbulent":
            result["action"] = "SESSION_REVOKED_FIDO2_REQUIRED"
            self.emit(
                "TURBULENT_SESSION_REPLAY",
                severity=min(1.0, re_beh / (2 * self.re_crit)),
                # Part 4 Phase 3: this organ observes *behaviour*, not
                # location. It genuinely does not know the host, so it says so
                # with ``None`` rather than stamping a plausible-looking
                # HOST_UNKNOWN that downstream code then treats as a real
                # target. The Commander skips host-scoped actions when the
                # entity is absent (see Orchestrator.plan_actions).
                entities={"session_id": session_id, "user_id": user_id,
                          "host_id": host_id, "vlan_id": "VLAN_CORP_IT"},
                metrics={"re_beh": round(re_beh, 1), "re_crit": self.re_crit},
                reason=(f"Re_beh {re_beh:.0f} over critical {self.re_crit:.0f} "
                        f"(ratio {re_beh / self.re_crit:.2f}): cursor velocity "
                        f"{v_cursor:.0f} px/s with navigation length {l_nav:.0f} px "
                        f"departed the calibrated baseline, so the session is "
                        f"replayed rather than driven by a person"),
            )
        return result

    # ------------------------------------------------------------------ #
    def _rpc_revoke(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "SESSION_REVOKED",
            "session_id": args.get("session_id"),
            "user_id": args.get("user_id"),
            "require_fido2": bool(args.get("require_fido2", True)),
        }
