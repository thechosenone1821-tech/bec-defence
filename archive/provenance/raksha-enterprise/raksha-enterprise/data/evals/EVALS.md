# raksha-enterprise — EVALS

> Generated 2026-11-26T09:29:23Z · corpora seed 20261126 (deterministic) · scope: **MEASURED ON FIXTURES in a sandbox — not a deployment measurement**

## 1. Per-organ detection rates (attack corpus)

| Organ | Attack rows | Flagged | Detection rate | Clean rows | FP | FP rate |
|---|---|---|---|---|---|---|
| docguard | 50 | 46 | 92.0% | 150 | 1 | 0.67% |
| fileguard | 45 | 44 | 97.8% | 150 | 0 | 0.00% |
| idguard | 35 | 31 | 88.6% | 150 | 0 | 0.00% |
| netguard | 50 | 47 | 94.0% | 150 | 0 | 0.00% |
| quorumguard | 30 | 29 | 96.7% | 150 | 0 | 0.00% |
| sessionguard | 40 | 34 | 85.0% | 150 | 0 | 0.00% |
| tier0guard | 25 | 24 | 96.0% | 150 | 0 | 0.00% |
| voiceguard | 60 | 53 | 88.3% | 150 | 0 | 0.00% |
| **aggregate** | **335** | **308** | **91.9%** | **1200** | **1** | **0.08%** |

Detectors are the frozen threshold rules shipped in `raksha.organs` — the same modules the service runs.

## 2. Stage latency (p50 / p95)

| Stage | unit | p50 | p95 | n |
|---|---|---|---|---|
| verify_event | us/event | 7.8 | 8.9 | 46050 |
| organ.detect | us/event | 0.6 | 0.8 | 46050 |
| fusion.add | us/detection | 0.6 | 0.7 | 46050 |
| planner.proposals_for | ms/campaign | 9.05 | 9.09 | 30 |
| governor.decide | us/proposal | 2.7 | 2.8 | 600 |
| ledger.append | ms/block | 0.02 | 0.04 | 30 |

SQLite-backed append, WAL mode, one fsync-batched commit per block — not a distributed-ledger claim.

## 3. End-to-end campaign (embedded pipeline, c2247 scenario)

Full pipeline incl. SQLite writes, 50 fresh-state repeats: **p50 2.5 ms / p95 3.7 ms** for 18 events (sign -> verify -> detect -> fuse -> plan -> decide -> seal).

## 4. Integrity self-check

- signed events verify: 34 / tampered flagged: 6 / unsigned flagged: 10 (expected 40 / 5 / 10)

## 5. Claims ledger

| Claim | Status |
|---|---|
| Per-organ detection rate | MEASURED (fixture corpora, section 1) |
| False-positive rate on clean traffic | MEASURED (fixture corpora, section 1) |
| Stage latencies (real components) | MEASURED (section 2) |
| End-to-end campaign time | MEASURED (embedded pipeline, section 3) |
| Governor latency under production load | UNMEASURED — do not claim |
| Detection rates against a live adversary | UNMEASURED — RAAVAN replays signed fixtures |
| Containment disruption cost in a real network | UNMEASURED — topology is a demo deployment |

## 6. Reproduce

```
python3 tools/gen_corpus.py --out ./data/evals
python3 tools/run_evals.py --out ./data/evals
```

Detectors, fusion, planner, Governor and ledger are imported from the installed package — evals cannot drift from the service.

