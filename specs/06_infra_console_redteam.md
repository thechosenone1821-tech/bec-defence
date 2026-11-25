# PART 6 — INFRA: CONSOLE, RED-TEAM & OBSERVABILITY
## (SOC console · RAAVAN kill chain · eval harness)

> **What this is.** How anyone *sees* the company platform, how it is attacked on
> purpose, and how it is measured.
>
> **Team size.** 2–3 people (1 frontend, 1 red-team, 1 measurement).
> **Depends on:** Parts 4, 5 and 7.
>
> **This part contains the single largest visible gap in the project.**

---

## 1. The console ❌ NOT BUILT

There is **no company-side UI at all.** The bus serves JSON and a websocket, and
its root endpoint literally says:

> `"dashboard": "served separately — see raksha/ROADMAP.md (SOC console owned by UI/UX team)"`

Everything Parts 4, 5 and 7 do — eight organs detecting, a planner cutting, a
Governor refusing, a ledger sealing — is currently only visible through `curl`.

### 1.1 Why this is the highest-value work in the repo

Roughly **80% of the engine is finished and 20% of it is presented.** Judges and
stakeholders cannot evaluate a rate limiter they cannot see. A working console
turns existing tested code into a demonstrable product without inventing anything
new.

### 1.2 What it must show

| Panel | Reads from |
|---|---|
| Live telemetry feed (signed events only, unsigned shown greyed) | `WS /ws/telemetry` |
| Attack graph — nodes, typed edges, campaign labels | `GET /api/state` |
| Campaign cards — citizen leg + infra leg joined by `campaign_id` | `/api/state` |
| Planner proposal — the cut, and what it costs | `POST /api/containment` |
| **Governor decisions — including refusals** | ledger |
| Ledger verifier — chain status, "verify now" button | `spine.ledger_cli verify` |
| Tier-0 crown icons, visibly protected | topology |

**The refusal panel is not optional.** A console that only shows successful blocks
is a marketing page. The most persuasive screen in the whole demo is the ICU cut
being **refused** and the refusal appearing in an append-only log.

### 1.3 Constraints

- Must work offline (no CDN, no external fonts)
- Must render the graph without a heavy framework — vanilla or a small library
- Must never show an unsigned event as actionable
- Must label every figure fixture vs measured

**Estimated effort: ~400–600 lines.** This is the best effort-to-impact ratio in
the entire project.

---

## 2. RAAVAN — the adversary ✅ built

A red-team player that replays the canonical campaign:

```
voice-clone scam call → poisoned vendor invoice → session replay
      → ransomware → governor probing
```

Every step is emitted as **signed organ telemetry** through the same verification
path a real sensor uses. RAAVAN never bypasses the pipeline — if it could, the demo
would prove nothing.

**Design honesty:** RAAVAN emits *detections of its own attacks*, the way real
organs would see them. That is the only end-to-end path a sandbox can honestly
exercise, and it must be described that way rather than as "we stopped a real
attack".

**The case-token point:** campaign fusion works via an opaque `case_id` shared by
the citizen leg and the infrastructure leg, because the sanitizer HMACs unknown
entity keys into stable tokens. In the sandbox these tokens are low-entropy
fixtures — dictionary-able. Any real deployment must use high-entropy random case
tokens.

---

## 3. Measured evaluation ✅ partial

`evals/run_evals.py` produces a real baseline × metric table from fixtures.
`raksha/EVALS.md` holds the numbers.

**What is measured:** the voiceguard's synthetic-corpus performance and its six
degradation conditions.

**What is NOT measured, and must not be claimed:**

| Missing measurement | Consequence |
|---|---|
| Per-organ detection rate | "8 organs" is a count, not a result |
| False-positive rate under normal load | unknown; the number that kills a deployment |
| Containment disruption cost in a real network | fixture-only |
| Governor latency under load | unmeasured |
| End-to-end campaign time | unmeasured |
| p50/p95 for any part other than voiceguard | absent |

---

## 4. Build order

1. **Console** — live feed, then graph, then Governor refusals
2. RAAVAN run-through with the console attached (this is the demo)
3. Per-organ fixture corpora + detection rates
4. False-positive characterisation
5. Latency harness across the pipeline

---

## 5. Definition of done

- [ ] Console shows live signed telemetry within 2 seconds of ingest
- [ ] Attack graph renders a campaign spanning both the citizen and infra legs
- [ ] A Governor **refusal** is visible on screen without opening a terminal
- [ ] Ledger verify button works and shows the chain height
- [ ] RAAVAN drives the whole demo unattended
- [ ] Every organ has a detection rate in `EVALS.md`
- [ ] False-positive rate measured on clean traffic

**Today: zero of these are true.** Part 6 is the least-complete part, and it is
also the one that determines what the project is worth to anyone watching.

---

## 6. What this part does not do

- It does not detect or decide anything; it observes and attacks.
- It does not own the ledger (Part 7 does) — it only verifies and displays it.
- It must never be the only place a number appears. If a figure is not in
  `EVALS.md`, the console may not display it.
