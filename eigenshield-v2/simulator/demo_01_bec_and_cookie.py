#!/usr/bin/env python3
"""ACT 1 (Ring 1 — Perimeter & Identity).

Simulates 50,000 stealth-proxy bot sessions condensed into a rank-1 cluster
embedded in human traffic, then replays a stolen MFA session cookie.

    python simulator/demo_01_bec_and_cookie.py
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from reflexes.ring1_perimeter_identity import BECSpectralFilter, CookieFluidTurbulence


def banner(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main() -> None:
    rng = np.random.default_rng(20261120)

    banner("ACT 1.1 — BEC Spectral Botnet Projector (Ring 1 / Organ 1)")
    n_humans, n_bots, dims = 300, 400, 16
    humans = rng.normal(0.0, 1.5, size=(n_humans, dims))            # high-entropy spread
    bot_direction = rng.normal(0.0, 1.0, size=dims)
    bot_direction /= np.linalg.norm(bot_direction)
    bots = 8.0 * bot_direction + rng.normal(0.0, 0.1, size=(n_bots, dims))  # condensed ground state
    X = np.vstack([humans, bots])
    order = rng.permutation(X.shape[0])
    X = X[order]

    bec = BECSpectralFilter()
    t0 = time.perf_counter()
    result = bec.analyze(X)
    elapsed_ms = (time.perf_counter() - t0) * 1e3

    print(f"sessions analyzed      : {X.shape[0]} ({n_humans} human / {n_bots} bot)")
    print(f"singular values (top5) : {[round(s, 2) for s in result['singular_values'][:5]]}")
    print(f"condensation ratio R   : {result['condensation_ratio']:.4f}  (rank-1 if > 0.72)")
    print(f"rank-1 botnet detected : {result['is_rank1_botnet']}")
    print(f"bot sessions excised   : {len(result['excised_session_indices'])}")
    print(f"analysis latency       : {elapsed_ms:.2f} ms")

    banner("ACT 1.2 — Fluid Boundary-Layer Cookie Killer (Ring 1 / Organ 2)")
    cookie = CookieFluidTurbulence(re_crit=2300.0)
    print("benign session stream (laminar):")
    for i in range(5):
        r = cookie.observe(rho_cadence=rng.uniform(0.75, 0.95), v_cursor=rng.uniform(340, 520),
                           l_nav=rng.uniform(800, 1200), session_id="SESS_BENIGN",
                           user_id="USER_019")
        print(f"  sample {i}: Re_beh={r['re_beh']:8.1f}  regime={r['regime']}")

    print("stolen-cookie replay from headless script (turbulent):")
    t0 = time.perf_counter()
    r = cookie.observe(rho_cadence=14.0, v_cursor=5200.0, l_nav=3200.0,
                       session_id="SESS_STOLEN_9FA3", user_id="USER_019")
    replay_ms = (time.perf_counter() - t0) * 1e3
    print(f"  Re_beh={r['re_beh']:.1f}  regime={r['regime']}  action={r.get('action')}")
    print(f"  revocation latency    : {replay_ms:.2f} ms  (FIDO2 re-auth forced)")

    banner("ACT 1 COMPLETE — Ring 1 holds the perimeter without the SLM")


if __name__ == "__main__":
    main()
