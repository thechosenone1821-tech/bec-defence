# RAKSHA — Build Split into 7 Independently-Workable Parts

> **Purpose.** Split the entire project into 7 parts that separate teams can own
> without blocking each other. Each part has its own file, its own definition of
> done, and its own honest status.
>
> **Derived from:** `raksha/ARCHITECTURE.md` §§1–4 (the canonical shield taxonomy),
> `PROBLEM_STATEMENT.md`, `CONTEXT.md`, `BUILD_GUIDE.md`, `README.md` (the 8-organ
> ring definition), and the actual code in `raksha-code/`.
>
> **Start here for current state:** [`../BUILD_STATE.md`](../docs/STATUS.md)
> — one page, every figure produced by running the code today.
> **Phase 3/4 note:** shared contracts/spine and the Citizen consolidation are
> described in [`../raksha/PHASE3_CONTRACT_SPINE.md`](../raksha/PHASE3_CONTRACT_SPINE.md)
> and [`../raksha/PHASE4_CITIZEN_CONSOLIDATION.md`](../raksha/PHASE4_CITIZEN_CONSOLIDATION.md);
> the seven-part build split below remains the historical work breakdown.
>
> **Phase 1 supersession (2026-11-26):** the 7-part split below is historical.
> The combined-system freeze uses **two apps + one shared spine** and one
> canonical implementation per capability; see
> [`../raksha/PHASE1_ARCHITECTURE_FREEZE.md`](../raksha/PHASE1_ARCHITECTURE_FREEZE.md)
> and [`../raksha/PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](../raksha/PHASE1_SOURCE_OF_TRUTH_MATRIX.md).
> The phrase "Two spines, as requested" below is historical language and is not
> the Phase 1 architecture. VoiceGuard is parked by ADR-009.
>
> **`features.md` has still never been supplied**, so this taxonomy is derived from
> the docs above. When it arrives, reconcile — do not rebuild.

---

## The split

```
RAKSHA
├── CITIZEN APP
│   ├── Part 1 — Citizen Spine        risk engine · i18n · capture · report
│   ├── Part 2 — VoiceGuard  (Maya)   synthetic-speech screening
│   └── Part 3 — MessageGuard         scam-script detection
│
├── INFRASTRUCTURE
│   ├── Part 4 — Detection Rings      the 8 shield organs
│   ├── Part 5 — Response & Governance planner · Governor · commander
│   └── Part 6 — Console & Red-team   SOC UI · RAAVAN · evals
│
└── Part 7 — THE SPINE                bus · graph · ledger · governor · planner
```

**Two spines, as requested:** the Citizen spine is **Part 1** (the risk engine
that all citizen features plug into), and the shared spine is **Part 7** (the bus,
ledger and Governor that both apps depend on).

---

## The seven files

| # | File | Owns | Team |
|---|---|---|---|
| 1 | [`01_citizen_spine.md`](01_citizen_spine.md) · [roadmap](01a_citizen_spine_roadmap.md) · [phase 3](01b_citizen_spine_phase3.md) | Risk fusion, three languages, privacy, report rail | 2 |
| 2 | [`02_citizen_voiceguard.md`](02_citizen_voiceguard.md) | Maya — the voice model | 2 |
| 3 | [`03_citizen_messageguard.md`](03_citizen_messageguard.md) | Scam-text scorer · reason codes · measured fixture corpus | 2 |
| 4 | [`04_infra_detection_rings.md`](04_infra_detection_rings.md) | The 8 organs | 4 |
| 5 | [`05_infra_response_governance.md`](05_infra_response_governance.md) | Planner, Governor, commander | 3 |
| 6 | [`06_infra_console_redteam.md`](06_infra_console_redteam.md) | Console, RAAVAN, measurement | 3 |
| 7 | [`07_spine.md`](07_spine.md) | Bus, graph, ledger, safety core | 3 |

**Total: ~19 people**, or ~7 people working one part each with longer timelines.

---

## Status at a glance

| Part | Built | Honest verdict |
|---|---|---|
| 1 · Citizen spine | **100% + rebuilt** | 3 phases done, then rebuilt in 4 parts (fusion · explanation · capture · delivery). **+196 tests over 626, 822 total.** |
| 2 · VoiceGuard | **65%** | Real pipeline, real measurements — on fake data. |
| 3 · MessageGuard | **100% (spec DoD)** | Phase 5 single-source; 538 hand-authored fixtures, measured FPR and accuracy, shared `MSG-*` i18n. Real-world field performance still UNMEASURED. |
| 4 · Detection rings | **70%** | 8/8 organs coded; none seen real traffic. |
| 5 · Response & governance | **75%** | The strongest part. No live model; dry-run executor. |
| 6 · Console & red-team | **30%** | **No UI at all.** RAAVAN works. |
| 7 · Spine | **85%** | Solid. Campaign fusion is the weak seam. |
| **Overall** | **~72%** | Engine far ahead of presentation; Part 3 no longer the measurement gap. |

---

## What needs model training (only three things)

| Thing | Part | Blocking what |
|---|---|---|
| **Voice model on real speech + real clones** | 2 | Any accuracy claim; the word "clone" |
| **Message evaluation on a consent-cleared real corpus** | 3 | Any field accuracy / FPR claim beyond the hand-authored fixture measurement |
| **On-device quantisation** | 2 | Shipping to a phone |

Everything in Parts 4, 5, 6 and 7 is **deterministic mathematics by design**. That
is the safety story, not a shortcut. The commander in Part 5 uses a *pre-trained*
local model — it needs **running**, not training.

---

## The three rules that bind all seven parts

1. **The AI proposes, the Governor disposes.** No part may create a path around
   Part 7's Governor.
2. **No unverified number.** A figure appears only if a harness in this repo
   produced it, and it carries its condition (fixture / synthetic / measured).
3. **Nothing found is not nothing wrong.** No part may emit a reassuring verdict
   from an absence of evidence.

---

## Where to start, by goal

| If the goal is… | Start with |
|---|---|
| A demo that impresses judges | **Part 6 console** — biggest visible gap |
| Credibility of the AI claim | **Part 2 real corpus** |
| Technical depth | **Part 5** — already strongest; add adversarial tests |
| Broadest contributor surface | **Part 4** — 8 organs, parallelisable |
| Not breaking what works | **Part 7** — everything depends on it |

## Current integration status (Phases 6–8)

Phases 6–8 are implemented: one 8-organ detector registry, one deterministic
Governor/planner/executor/ledger path and one unified Infra backend/API/WS with
an operable read-only SOC console. See
[`../raksha/PHASE678_UNIFIED_INTEGRATION.md`](../raksha/PHASE678_UNIFIED_INTEGRATION.md)
and [`../BUILD_STATE.md`](../docs/STATUS.md). VoiceGuard/MAYA remain frozen;
Phase 9/10 are not started.
