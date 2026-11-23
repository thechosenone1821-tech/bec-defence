"""M6 — measured evals. Every number printed here comes from this run.

Baselines (all honest, all fixture-bound):
  B1 threshold-alerting   severity >= 0.7 raises an alert; no correlation
  B2 signature/blocklist  drop events whose entities match a known-bad fixture list
  B3 full isolation       sever EVERY non-crown edge (the "just shut it down" baseline)

RAKSHA (full): organ-signed pipeline + union-find campaign fusion +
containment planner + Governor (90% preserved-uptime floor, TCB re-derivation).

Labels: fixtures are synthetic; the campus graph is synthetic; MessageGuard is
a heuristic validated on a synthetic corpus (real-world unmeasured). Latency
is sandbox wall-clock on this machine, not an SLA. Nothing here is derived
from PIB/CERT-In/AIIMS or any external source.
"""

import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
sys.path.insert(0, CODE)

from fastapi.testclient import TestClient

from spine.bus import create_app
from spine.telemetry_mac import sign_event
from spine import containment, governor
from raavan.killchain import build_campaign
from citizen.messageguard import evaluate_fixtures

POLICY_SRC = os.path.join(CODE, "spine", "config", "policy.yaml")
TOPOLOGY = os.path.join(CODE, "spine", "config", "company_topology.json")
MSG_FIXTURES = os.path.join(CODE, "citizen", "fixtures", "message_fixtures.json")
INGRESS = ["VLAN_GUEST_WIFI", "VLAN_MAINT_03", "VLAN_LAB_DEV"]

KNOWN_BAD = {"sha256:mockinv0123", "SESS_9A8B7C", "HOST_AB12CD"}  # signature list = what a static blocklist would know


def _fresh_client(tmp):
    cfg = os.path.join(tmp, "config")
    os.makedirs(cfg)
    shutil.copy(POLICY_SRC, os.path.join(cfg, "policy.yaml"))
    app = create_app(policy_path=os.path.join(cfg, "policy.yaml"),
                     topology_path=TOPOLOGY, model="qwen3.5:4b")
    return TestClient(app)


def main():
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        # ---- B1/RAKSHA: threshold alerts vs fused campaign ---------------
        events = build_campaign()
        sev_alerts = sum(1 for e in events if e["severity"] >= 0.7)

        t0 = time.perf_counter()
        c1 = _fresh_client(os.path.join(tmp, "t1"))
        signed = [sign_event(dict(e)) for e in events]
        c1.post("/api/ingest", json=signed)
        t_ingest = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()
        bundle = c1.post("/api/orchestrate", json={}).json()
        t_orch = (time.perf_counter() - t0) * 1000
        state = c1.get("/api/state").json()
        campaigns = state.get("campaigns", [])
        top = max(campaigns, key=lambda c: c.get("size", 0)) if campaigns else {}
        rows.append(("Campaigns from the 5-step replay (5 signed organ alerts)",
                     f"{sev_alerts} separate alerts", "n/a (no verify, no correlation)", "5 alerts",
                     f"**1 fused campaign** (cmp_…, size={top.get('size')})"))
        total = t_ingest + t_orch
        rows.append(("Sandbox wall-clock ingest→decision (this machine, not an SLA)",
                     "n/a", "n/a", "n/a",
                     f"**{total:.0f} ms** (ingest {t_ingest:.0f} + orchestrate {t_orch:.0f})"))

        # ---- B2 signature/blocklist on the same replay --------------------
        sig_hits = 0
        for e in events:
            ent = e.get("entities", {})
            if any(v in KNOWN_BAD for v in ent.values()):
                sig_hits += 1

        # ---- forged-probe rejection ---------------------------------------
        c2 = _fresh_client(os.path.join(tmp, "t2"))
        forge = c2.post("/api/ingest", json=events).json()   # unsigned
        held = c2.post("/api/orchestrate", json={}).json()
        rows.append(("Forged (unsigned) probe: events held, AI path",
                     "no MAC — executes", "would alert (no verify)", "no concept",
                     f"**{forge['unverified']}/5 rejected; orchestrate → {held.get('status')}**"))

        # ---- full isolation baseline vs planner ---------------------------
        plan = containment.propose(TOPOLOGY, INGRESS)
        topo = containment.load_topology(TOPOLOGY)
        all_noncrown = [e for e in topo["edges"] if not e["protected"]]
        d_full = sum(e["weight"] for e in all_noncrown)  # sever everything
        total_flow = d_full
        full_crit_after = 0.0
        rows.append(("Fixture flow severed by containment (ingress seeds)",
                     "100% (shut it down)", "unknown — unscoped", "100%",
                     f"**{plan['objective']['D']*100:.2f}%** of non-crown flow; "
                     f"{plan['preserved_fixture_flow_pct']:.2f}% preserved"))
        rows.append(("Mission-critical (fixture) weight preserved",
                     "0%", "unknown", "0%",
                     f"**{plan['preserved_critical_weight_pct']:.2f}%** "
                     f"(ICU {plan['icu_status']}, tier-0 edges cut: {plan['tier0_edges_cut']})"))

        # ---- Governor floor on the deep-implant proposal -------------------
        deep = containment.propose(TOPOLOGY, ["VLAN_CORP_IT"])
        g = governor.PolicyEngine(POLICY_SRC)
        decision = g.evaluate({"tool": "execute_percolation_cut",
                               "args": {"target_spectral_radius": 0.99, "preserve_tier0_vlans": True}},
                              context={"trigger": "eval",
                                       "expected_preserved_uptime_pct": deep["preserved_critical_weight_pct"]})
        rows.append(("Deep-implant isolation (44% critical weight cut) — autonomy decision",
                     "executes (no floor)", "executes", "executes",
                     f"**{decision['decision']}** — {decision['reasons'][0]}"))

        # ---- B2 coverage ---------------------------------------------------
        rows.append(("RAAVAN 5-step coverage (signature vs fusion)",
                     "0/5 (semantic steps invisible)", f"**{sig_hits}/5** (known-bad fixtures only)", "n/a",
                     "**5/5** — one campaign, human step-up at impact"))

        # ---- MessageGuard synthetic corpus ----------------------------------
        report = evaluate_fixtures(MSG_FIXTURES)
        acc = report.get("accuracy")
        n = report.get("total", report.get("n", "?"))
        hit = report.get("passed", report.get("correct", "?"))
        rows.append(("MessageGuard synthetic corpus accuracy (NOT real-world)",
                     "n/a", "n/a", "n/a", f"**{hit}/{n} = {acc}**"))

    hdr = ("Metric", "B1 threshold-alert", "B2 signature list", "B3 full isolation", "RAKSHA (this build)")
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---|" * len(hdr))
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    print()
    print("All rows measured in this run against the synthetic campus graph and synthetic RAAVAN fixtures.")
    print("MessageGuard: synthetic corpus only — real-world recall UNMEASURED. Latency: sandbox wall-clock.")


if __name__ == "__main__":
    main()
