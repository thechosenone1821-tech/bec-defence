# EIGENSHIELD v2.0 — Work Split: Two Backend Owners + UI/UX Team

This document is the coordination contract for building EIGENSHIELD with **two
backend developers** working in parallel and a **separate UI/UX team** building
the SOC dashboard. Read this first, then the doc for your part:

| Doc | Audience |
| --- | --- |
| `docs/WORK_SPLIT.md` (this file) | Everyone — who owns what, how the seam works |
| `docs/INTERFACE_CONTRACT.md` | Both backend devs + UI/UX — the frozen A↔B API |
| `docs/BACKEND_PART_A.md` | **Backend Developer A** — "Sense & Sanitize" (Planes 1+2) |
| `docs/BACKEND_PART_B.md` | **Backend Developer B** — "Decide & Contain" (Planes 3+4) |
| `docs/UI_UX_BRIEF.md` | **UI/UX team** — the SOC Command Dashboard |
| `dashboard/README.md` | Pointer for the UI/UX team |

---

## 1. The one-sentence architecture

Reflexes (Plane 1) detect in microseconds → the Zero-Trust Bus (Plane 2)
sanitizes and brokers → the Small AI Commander (Plane 3) proposes → the
Hard Safety Governor (Plane 4) disposes. The dashboard only *observes*; it is
never in the decision path.

## 2. Why the split falls exactly between Plane 2 and Plane 3

That seam is the only place where the trust boundary, the data shape and the
failure domains all change at once:

* Everything **left** of the seam talks in raw microarchitectural signals and
  can act alone (reflexes are autonomous by design, even if the AI is down).
* Everything **right** of the seam talks only in opaque tokens, fixed enums
  and bounded numerics, and can never act without the Governor's approval.

That makes it a clean, testable, one-way contract with no shared state to
manage — the ideal split point for two people who must not step on each
other.

## 3. Ownership map (file-level, no overlap)

```text
 eigenshield-v2/
 ├─ reflexes/…                    PART A   (8 reflex organs, Plane 1)
 ├─ bus/sanitizer.py              PART A   (trust boundary)
 ├─ bus/entity_graph.py           PART A   (sliding-window graph)
 ├─ bus/event_server.py           PART A*  (telemetry ingest + WS; see §6)
 ├─ config/company_topology.json  PART A   (VLAN/host/user graph; demo + tests)
 ├─ simulator/demo_01..03         PART A   (Ring 1–3 stage acts)
 ├─ simulator/demo_04             PART A   (Ring 4 organs demo — read-only for B)
 ├─ scripts/mock_plane_b.py       PART A   (develop without B)
 ├─ tests/test_organs.py          PART A
 ├─ tests/test_page_curve.py      PART A
 ├─ tests/test_hashimoto.py       PART A
 ├─ tests/test_sanitizer.py       PART A
 │
 ├─ commander/…                   PART B   (SLM client, orchestrator, tool schemas)
 ├─ governor/…                    PART B   (policy engine, watchdog, audit ledger)
 ├─ config/policy.yaml            PART B   (crown jewels, budgets, rollback)
 ├─ simulator/demo_05_…py         PART B   (Governor-vs-hallucination act)
 ├─ scripts/mock_plane_a.py       PART B   (develop without A)
 ├─ tests/test_orchestrator.py    PART B
 ├─ tests/test_policy_engine.py   PART B
 ├─ tests/test_audit_ledger.py    PART B
 │
 ├─ bus/event_server.py §wire     SHARED   integration seam (see §6)
 ├─ dashboard/                    UI/UX TEAM (never edit; backend frozen for them)
 ├─ docs/INTERFACE_CONTRACT.md    SHARED   changes need BOTH devs' sign-off
 ├─ docs/… (this file)            SHARED
 ├─ Dockerfile, docker-compose.yml SHARED  integration build
 └─ README.md                     SHARED
```

\* `bus/event_server.py` is **owned by A**, but the block clearly marked
`# ---- Plane 3/4 wiring ----` inside `create_app()` is the integration seam:
B reviews it, A merges it. Nobody else edits that file without the other's
review. The executor table in it maps B's 10 tools → A's organ RPC surface.

## 4. The two parts at a glance

### Part A — "Sense & Sanitize" (Planes 1 + 2) — Backend Developer A

**Mission:** own every microsecond-scale decision and the trust boundary.

* 8 reflex organs with real math: SVD condensation (BEC), Reynolds-style
  turbulence (cookie killer), FFT + Fiedler gates (Bragg), curvature/ jerk
  steering (Lyapunov), 4 KB parity honey-blocks (Page-Curve), power-vs-IPC
  residual (Landauer), non-backtracking min-cut containment (Hashimoto),
  mock-eBPF mismatch repair (MutS/MutL).
* Telemetry sanitizer + sliding-window entity graph + FastAPI/WebSocket
  broker (`event_server`).
* Stage acts 1–4.
* **Must work with the AI fully offline.** Plane 1 never blocks on Plane 3.

### Part B — "Decide & Contain" (Planes 3 + 4) — Backend Developer B

**Mission:** own every AI-adjacent decision and the hard safety shell.

* Local SLM client (Ollama/llama.cpp) with JSON-grammar lock, plus the
  deterministic rule-based fallback commander; cross-ring orchestrator and
  executive-brief writer.
* Deterministic Governor: 10-tool schema lock, crown-jewel lock, blast-radius
  budgeter (5-min windows), human step-up gate, 15-second uptime watchdog,
  SHA-256 hash-chained audit ledger.
* Stage act 5. Contract tests for the whole seam.
* **Must fail safe.** If the SLM is down, garbage, or adversarial, actions
  degrade to "propose cautiously / escalate", never to "act boldly".

### UI/UX team — SOC dashboard only

* Owns `dashboard/` pixel-to-package. Consumes the contract in
  `INTERFACE_CONTRACT.md` (REST + WS). Zero backend edits. If something is
  missing from the API, they file an issue; a backend dev adds it behind the
  contract version bump.

## 5. Rules of engagement

1. **The contract is frozen at v1.0.0** (`docs/INTERFACE_CONTRACT.md`).
   Changes require a PR touching both halves + both devs' approval. Never
   "just add a field" unilaterally.
2. **No cross-edits.** B may `import` A's public organ classes (to call
   `handle_rpc`) but never edits `reflexes/**` or `bus/**`; A may import
   `commander/tool_schemas.json` via the Governor's loader but never edits
   `commander/**`/`governor/**`/`policy.yaml`.
3. **Sanitizer is sacred (A).** B consumes only what survived sanitization;
   if B finds a raw string leaking, that's an A bug — file it, don't filter
   it downstream.
4. **Governor is sacred (B).** A's organs can *propose* actions via their
   RPC surface; A never bypasses the Governor for host/VLAN-disrupting tools.
5. **Integration window**: agree two 2-hour slots/week where A+B pair on
   `event_server` wiring, contract tests and demo rehearsal. Outside of
   those, heads-down.
6. **Main stays green.** Merges to `main` only via PR with CI green
   (`pytest -q` ≥ 23 tests + all five demos run clean).

## 6. Integration seam (how A's bus calls B's decider)

`bus/event_server.py → create_app()` wires:

```text
POST /api/ingest
   └─ sanitize_event()            (A)
   └─ buffer + entity_graph       (A)
   └─ broadcast WS "event"        (A)
   └─ severity >= 0.8 ? background run_pipeline()
         └─ Orchestrator.plan_actions()   (B, fallback_rules if SLM absent)
         └─ PolicyEngine.evaluate()       (B — APPROVED/BLOCKED/ESCALATE)
         └─ executor(tool, args)          (A organ RPC, only if APPROVED)
         └─ AuditLedger.append()          (B)
         └─ broadcast WS "action_plan"    (A)
```

Executor table lives in A's file but each line maps 1:1 to B's 10 tools —
B must review any change to it. The shared demo rehearsal (ACT 1→5) is the
acceptance test for the seam.

## 7. Milestones (suggested 2-week plan)

| # | When | A delivers | B delivers | Joint |
| --- | --- | --- | --- | --- |
| **M1** | Day 3 | Organs green vs `pytest`; `demo_01..04` run | Governor + ledger green vs `pytest`; SLM+fallback plan on mock events (`scripts/mock_plane_a.py`) | Contract v1.0.0 read-through (30 min) |
| **M2** | Day 6 | Sanitizer fuzz pass (adversarial strings); WS reconnect handling; `/api/state` stable | Rule-parity review vs 10-tool schema; watchdog injectable tests; ledger tamper-proof demo | First live ingest→plan→decision loop |
| **M3** | Day 8 | ACT 1–4 rehearsed at < 2 ms reflex latencies | ACT 5 rehearsed; hash-chained ledger verified live | Full 5-act stage run; bug bash |
| **M4** | Day 10 | Perf pass (SVD on 50k sessions) | Rollback watchdog live drill | Dry-run show + handoff to UI/UX for dashboard plug-in |

Falling behind? Cut scope in this order: (1) Ollama→fallback_rules is fine
for the stage; (2) eBPF stays simulated (it already is); (3) spectral plots
in `/api/state` are dashboard work, not yours. Never cut: sanitizer,
crown-jewel lock, ledger, tests.

## 8. Definition of done (per part)

**Part A done** ⇔ `pytest tests/test_organs.py tests/test_page_curve.py tests/test_hashimoto.py tests/test_sanitizer.py -q` green;
`python simulator/demo_01..04_*.py` exit 0; sanitizer rejects every raw-string
injection fuzz case; WS broadcast verified with a CLI client; docs updated.

**Part B done** ⇔ `pytest tests/test_orchestrator.py tests/test_policy_engine.py tests/test_audit_ledger.py -q` green;
`demo_05_governor_hallucination.py` exit 0 with HARD_BLOCK + chain `valid: true`;
plan produced on mock Plane-A batch with SLM **and** with SLM killed;
watchdog auto-rollback test green; docs updated.

**Integration done** ⇔ single command boots the bus; all 7 mock events
in → plans → decisions → executor calls → ledger entries; `GET /api/state`
shows graph + last plan; UI/UX team confirms the dashboard renders the live
feed.

## 9. Escalation & ownership questions

* Merge conflicts in `event_server.py` / `docs/` → 15-minute sync, smallest
  diff wins, A+B review.
* Contract ambiguity discovered mid-sprint → A proposes, B approves (or vice
  versa), bump contract minor version, note in `INTERFACE_CONTRACT.md`
  changelog.
* Security disagreement (A wants organ X to auto-act vs B's governor saying
  no) → **the Governor wins every time.** That is the design.

---

## v2.1 note

FORTRESS (the resilience layer in `fortress/`, plus `demo_06`) is **shared
infrastructure**: A signs at emission, the bus verifies and gates, B's Governor
double-checks through the TCB twins and freezes under probing. Neither half may
disable a FORTRESS control in a feature PR — disabling/weakening any of them
requires the same sign-off as a contract change (see INTERFACE_CONTRACT.md,
v2.1 appendix).
