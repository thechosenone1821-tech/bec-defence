# EVALS — measured, not adjectives

**Last updated:** 2026-11-20 · **Version:** docs v0.7.0 · **Status:** M6 measured-evals freeze.

Reproduce everything below in seconds:

```bash
cd raksha-code
pytest -q                       # 67 passed
python evals/run_evals.py       # prints the table below from this run
```

**Universe and honesty labels.** The campus graph is synthetic
(`spine/config/company_topology.json`). The RAAVAN campaign is a fixture
replay (5 signed organ events). MessageGuard is a keyword-heuristic scored on
a synthetic corpus — real-world recall is **UNMEASURED**. Latency is sandbox
wall-clock on the maintainer's machine. No number here is derived from
PIB/CERT-In/AIIMS or any external source; external claims stay `[VERIFY]`.

## Table (measured 2026-11-20 via `evals/run_evals.py`)

| Metric | B1 threshold-alert | B2 signature list | B3 full isolation | RAKSHA (this build) |
|---|---|---|---|---|
| Campaigns from the 5-step replay (5 signed organ alerts) | 5 separate alerts | n/a (no verify, no correlation) | 5 alerts | **1 fused campaign** (cmp_…, size=5) |
| Sandbox wall-clock ingest→decision | n/a | n/a | n/a | **~208 ms** (ingest ~185 + orchestrate ~22) |
| Forged (unsigned) probe: events held, AI path | no MAC — executes | would alert (no verify) | no concept | **5/5 rejected; orchestrate → HELD_UNVERIFIED_EVIDENCE** |
| Fixture flow severed (ingress seeds) | 100% (shut it down) | unknown — unscoped | 100% | **14.71%** of non-crown flow; 85.29% preserved |
| Mission-critical (fixture) weight preserved | 0% | unknown | 0% | **100.00%** (ICU INTACT, tier-0 edges cut: 0) |
| Deep-implant isolation (44% critical weight cut) — autonomy | executes (no floor) | executes | executes | **BLOCKED** — preserved uptime 55.56% < 90.0% floor → human step-up |
| RAAVAN 5-step coverage (signature vs fusion) | 0/5 | **4/5** (known-bad fixtures only) | n/a | **5/5** — one campaign, human step-up at impact |
| MessageGuard synthetic corpus accuracy | n/a | n/a | n/a | **20/20 = 1.00** (synthetic) |

Baselines honesty note: B1/B2/B3 are straw-man-but-real reference architectures,
not products. They exist so the deltas are *measured*, not adjectives. No
third-party product was benchmarked; none was available in the sandbox.

## The ₹-saved slide (illustrative — inputs are `[VERIFY]`, not claims)

Do NOT present external loss figures until checked against primary sources
the night before. The defensible form, computed live from the campaign ledger:

    ₹ saved     = (threats_stopped × ₹avg_loss_prevented [VERIFY])
                − (false_positives × ₹cost_per_containment_min [VERIFY])
    ₹ preserved = uptime_pct_kept × revenue_per_pct_point_per_hour [VERIFY]

Stage script: open `/api/state` (campaigns + last_containment), read the fused
`cmp_id` and the ingress cut (14.71% fixture flow severed, ICU INTACT), and
arithmetize with the night-before figure — never with an unverified one.

## What this eval does NOT claim

- Real-world detection accuracy in the wild (MessageGuard corpus is synthetic).
- Any production SLO (flows are fixture weights; latency is one laptop).
- Benchmarks against commercial products (none were run).
- Regulatory efficacy (no CERT-In/PIB/AIIMS figure is asserted).

## M6 stage checklist (human tasks — not doable in this sandbox)

- [ ] Stage run-through ×5 (Acts 1–4, incl. RAAVAN replay + `/api/containment`)
- [ ] Night-before: every `[VERIFY]` stat checked against primary sources
- [ ] Backup video of the full Act-2 sequence (Wi-Fi dies gracefully)
- [ ] Judges'-turn script ("add your attack to RAAVAN") with canned safe inputs
- [ ] Post-hackathon: docs → v1.0.0 with what actually shipped
