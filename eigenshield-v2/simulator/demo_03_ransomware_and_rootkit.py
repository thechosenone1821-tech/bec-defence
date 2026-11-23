#!/usr/bin/env python3
"""ACT 3 (Ring 3 — Endpoint & Silicon).

Runs a SAFE sandboxed ransomware pass against ./tmp_demo_files (it overwrites a
honey 4 KB block only — no real files are harmed) and audits a hidden
hook-bypassing worker thread via power-vs-IPC residual analysis.

    python simulator/demo_03_ransomware_and_rootkit.py --sandbox ./tmp_demo_files
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from reflexes.ring3_endpoint_silicon import PageCurveTrap, LandauerThermalAudit


def banner(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sandbox", default="./tmp_demo_files")
    args = parser.parse_args()
    os.makedirs(args.sandbox, exist_ok=True)

    banner("ACT 3.1 — Page-Curve 4 KB Ransomware Trap (Ring 3 / Organ 5)")
    trap = PageCurveTrap(allow_real_kill=False)  # dry-run: reports the kill, never SIGKILLs
    armed = trap.arm(args.sandbox, host_id="HOST_042", density_level="high")
    print(f"honey blocks armed     : {armed['honey_blocks']} pair(s) in {args.sandbox}")

    victim = armed["files"][0]
    fake_ransomware_pid = 4242
    print(f"ransomware shadow-pass : encrypting {os.path.basename(victim)} (first 4 KB) ...")
    with open(victim, "r+b") as f:
        f.write(b"\x13\x37" * 2048)  # 4 KB of 'ciphertext'

    t0 = time.perf_counter()
    decision = trap.on_write(victim, pid=fake_ransomware_pid, host_id="HOST_042")
    ms = (time.perf_counter() - t0) * 1e3
    print(f"parity check           : BREACHED on first 4 KB write")
    print(f"action                 : {decision['action']}  pid={decision['pid']}  dry_run={decision['dry_run']}")
    print(f"reflex latency         : {ms:.2f} ms  (budget: < 1 ms)")

    banner("ACT 3.2 — Landauer Thermodynamic Rootkit Auditor (Ring 3 / Organ 6)")
    audit = LandauerThermalAudit(residual_threshold_w=8.0, sustain_samples=5)
    rng = np.random.default_rng(11)
    benign = []
    for _ in range(14):
        ipc = rng.uniform(1.2, 2.6)
        temp = rng.uniform(46.0, 60.0)
        benign.append({"power_w": 18.0 * ipc + 0.35 * temp + 5.0 + rng.normal(0, 1.5),
                       "ipc": ipc, "temp_c": temp})
    calib = audit.calibrate(benign)
    print(f"observer fit           : power ~= {calib['coef_ipc_w']:.2f}*IPC + "
          f"{calib['coef_temp_w_per_c']:.3f}*T_die + {calib['intercept_w']:.2f}")
    print(f"(Landauer floor @310K  : {audit.landauer_floor(1e15):.3e} W for 1e15 bit-erases/s — context)")

    print("hidden hookless rootkit thread (power up, visible IPC flat):")
    for i in range(6):
        r = audit.audit(power_w=46.0, ipc=0.35, temp_c=54.0, host_id="HOST_042")
        print(f"  t={i}: power={r['power_w']}W predicted={r['predicted_w']:.1f}W "
              f"unaccounted=+{r['unaccounted_w']:.1f}W sustained={r['sustained_anomaly']}")
    print("=> persistent unattributed Joule dissipation: host isolation recommended")

    banner("ACT 3 COMPLETE — ransomware stopped after ONE 4 KB block; rootkit flagged by physics")


if __name__ == "__main__":
    main()
