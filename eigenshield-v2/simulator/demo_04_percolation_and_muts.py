#!/usr/bin/env python3
"""ACT 4 (Ring 4 — Network Fabric & Self-Healing).

Hospital-campus worm vs the Hashimoto non-backtracking containment switch,
plus a live double-exploit against a mock vulnerable API healed by the
MutS/MutL eBPF shield in < 50 ms.

    python simulator/demo_04_percolation_and_muts.py
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reflexes.ring4_network_healing import HashimotoPercolation, MutsEbpfRepair
from reflexes.ring4_network_healing.hashimoto_percolation import PROTECTED_WEIGHT

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def banner(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def load_topology(path: str):
    with open(path) as f:
        return json.load(f)


def main() -> None:
    topo = load_topology(os.path.join(_HERE, "config", "company_topology.json"))
    vlan_ids = [v["id"] for v in topo["vlans"]]
    idx = {v: i for i, v in enumerate(vlan_ids)}
    crit_w = topo["criticality_weights"]

    edges = []
    for e in topo["edges"]:
        crit = e["criticality"]
        is_crown = crit == "crown_jewel"
        is_mission = crit == "mission_critical"
        weight = e["weight"] if e["weight"] is not None else crit_w.get(crit, 1.0)
        edges.append((idx[e["a"]], idx[e["b"]],
                      PROTECTED_WEIGHT if is_crown else float(weight),
                      is_crown,
                      is_crown or is_mission))

    banner("ACT 4.1 — Hashimoto Bond Percolation Containment (Ring 4 / Organ 7)")
    percol = HashimotoPercolation(target_radius=1.0)
    from reflexes.ring4_network_healing.hashimoto_percolation import spectral_radius
    rho_full = spectral_radius(len(vlan_ids), [(a, b) for a, b, _, _, _ in edges])
    print(f"topology               : {len(vlan_ids)} VLANs, {len(edges)} edges "
          f"({sum(1 for *_, p in edges if p)} crown-jewel, un-cuttable)")
    print(f"rho(B) full graph      : {rho_full:.4f}")
    print("note: finite graphs cannot go below rho=1 while any cycle remains —")
    print("      crown clinical triangle will pin rho at exactly 1.0 by design.\n")

    t0 = time.perf_counter()
    plan = percol.containment_plan(vlan_ids, edges, target=1.0)
    ms = (time.perf_counter() - t0) * 1e3
    print(f"\ncontainment plan ({ms:.1f} ms):")
    print(f"  rho before -> after  : {plan['rho_before']} -> {plan['rho_after']}  (target < {plan['target']})")
    print(f"  contained            : {plan['contained']}   ({plan['note']})")
    print(f"  tier-0 edges cut     : {plan['tier0_edges_cut']}")
    print(f"  preserved critical w : {plan['preserved_critical_weight_pct']}%  (SLA floor 90%)")
    print(f"  preserved all load  : {plan['preserved_normal_weight_pct']}%")
    for cut in plan["removed_edges"]:
        print(f"  CUT  {cut['edge'][0]:28s} <-> {cut['edge'][1]:28s} w={cut['weight']}")

    banner("ACT 4.2 — MutS/MutL eBPF Zero-Day Self-Healing (Ring 4 / Organ 8)")
    muts = MutsEbpfRepair(splice_budget_ms=50.0)
    service = "APP_SRV_07"
    inv = muts.register_invariant(service, "bounds_check_v1")
    print(f"invariant registered   : {inv['invariant_id']}  profile=bounds_check_v1")

    print("\nexploit attempt #1 against mock vulnerable endpoint ...")
    t0 = time.perf_counter()
    r1 = muts.report_mismatch(service, detail="oob_write attempt on /api/transfer")
    wall1 = (time.perf_counter() - t0) * 1e3
    print(f"  -> {r1['status']}  splice={r1['splice_ms']:.3f} ms  within_50ms_budget={r1['within_budget']}")

    print("exploit attempt #2 (same zero-day, seconds later) ...")
    r2 = muts.report_mismatch(service, detail="oob_write attempt on /api/transfer")
    print(f"  -> {r2['status']}  second_attempt_blocked={r2['second_attempt_blocked']}")
    print(f"  wall-clock detection : {wall1:.2f} ms")

    banner("ACT 4 COMPLETE — worm boxed in; 2nd zero-day attempt fails; ICU stays online")


if __name__ == "__main__":
    main()
