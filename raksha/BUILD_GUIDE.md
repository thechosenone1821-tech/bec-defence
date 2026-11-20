# RAKSHA — Build Guide (what to build, how, in what order)

> **Last updated:** 2026-11-20 · Audience: engineers and AI coders.
> Read `CONTEXT.md` and `ARCHITECTURE.md` first. This file is the working
> plan — keep it honest and current.

---

## 1. Stack (decisions, not suggestions)

| Layer | Choice | Why |
| --- | --- | --- |
| Language | Python 3.11 | inherits eigenshield-v2 wholesale |
| Services | FastAPI + Uvicorn | existing bus pattern |
| Graph | NetworkX | existing; enough for stage scale |
| Math | numpy / scipy | existing organs |
| Local SLM | Ollama (`qwen3.5:4b` default) | offline district-hospital requirement |
| Citizen app | PWA (React-lite or vanilla + Service Worker) | Android-first, no store friction for pilots |
| Sentinel console | React dashboard (owned by UI/UX team per repo convention) | separation of concerns |
| Packaging | Docker Compose | one-command hospital install |
| Tests | pytest | existing 34 green baseline |

Avoid: any managed cloud dependency for the core path; any closed model API
in the critical path (Anthropic/OpenAI APIs may be used for *offline eval
analysis* only, never in the enforcement loop).

## 2. Repository layout (target)

```text
raksha/                    (this docs directory, permanent)
raksha-code/               (application code — created in Phase 1)
  spine/                   shared kernel: graph, ledger, governor, sanitizer,
                           containment, campaign correlator, canary tokens
  citizen/                 RAKSHA Citizen (PWA + local inference service)
    app/                   frontend
    inference/             VoiceGuard / MessageGuard models + wrappers
  sentinel/                RAKSHA Sentinel (on-prem stack)
    shields/               endpoint / identity / cloud / agent ingestors
    planner/               counterfactual containment engine
    console/               (handoff point for UI/UX team)
  raavan/                  sandboxed red team: playbook.yaml + executors
  evals/                   baselines, seeded scenarios, metric reports
  deploy/                  docker-compose profiles: hospital | payments | campus
  docs/                    links back into raksha/ (single source of truth)
tests/                     pytest, grows with code
```

## 3. Build order (do not improvise the sequence)

**M1 — Spine first (days 1):** extract from eigenshield-v2, with tests
carried over: sanitizer → ledger (+ anchor) → Governor (+ TCB twins) →
attack graph v2 (temporal + campaigns) → bus (verified-only ingest) →
ledger CLI for replay. **Exit:** one synthetic campaign flows bus→graph→
governor→ledger and back out via `/api/state`.

**M2 — Sentinel shields (days 1–2):** Endpoint (parity trap on fixture FS),
Identity (auth-log fixture → Ring-1 filter), Cloud (exfil heuristics on
fixture logs), AI-Agent (tool-call drift + canary-doc). Each ships with:
firing fixture, silent-case fixture, tests.

**M3 — Citizen app (days 2–3, parallel with M2):** MessageGuard first
(highest demo value per hour; embedding+regex ensemble), VoiceGuard second
(pretrained anti-spoof model via ONNX if available; deterministic spectral
fallback otherwise — never block the demo on model training). Report rail →
signed ingest into the same bus.

**M4 — RAAVAN + correlator (day 2):** playbook steps as idempotent scenario
functions writing into sandbox fixtures; correlator fingerprint = token
overlap + 5-minute temporal proximity + kill-chain stage progression.

**M5 — Containment + Governor integration (day 2):** candidate cuts from
graph neighborhood of attacker; evaluate C/D/R with fixture flows; planner
returns A*; Governor enforces; executor is a logging dry-run emitting
`action_plan` WS frames.

**M6 — Evals & stage (day 3):** run baselines; produce the table; rehearse;
record backup video; freeze docs.

## 4. Porting map (file-level)

See `CONTEXT.md §3` for the asset table. Order: spine first, shields next,
Citizen last-but-one. Do not port the stage-demo theatrics as-is; reimplement
on the spine with measurement built in from M1.

## 5. Safety rules (hard, audited)

1. RAAVAN runs only inside `evals/sandbox/` fixtures — never against
   localhost:80 of anything real, ever.
2. All "attacks" against production-like systems are **simulators**: fixture
   logs, fixture filesystems, loopback network namespaces.
3. No credentials committed; `.env` patterns only; CI has none.
4. Citizen app ships with zero-retention defaults; reports are tokenized
   before they leave the device.
5. VoiceGuard never records without the visible indicator; raw audio is
   processed in a ring buffer and discarded < 3 s.
6. Tier-0 (ICU, payments switch) demo cuts are always dry-run; the UI must
   show the word "DRY-RUN" on stage.
7. Any uncertainty about a safety rule ⇒ stop, ask the maintainer, propose
   the conservative default.

## 6. Testing & measurement

| Suite | Gate |
| --- | --- |
| `pytest` (inherited + new) | Every PR; 100% green before merge |
| Containment correctness | Cut set disconnects every seeded attacker; preserves ≥90% of fixture mission flows |
| Governor torture tests | 10,000 fuzzed action dicts; zero Tier-0 approvals without human step-up; zero TCB disagreements escape |
| Citizen accuracy | MessageGuard precision ≥90% on in-domain scripts, false-positive rate reported, multilingual parity tested |
| Ledger integrity | Golden-vector hashes; anchor cross-check; tamper test |
| Eval table | Baselines × metrics, per `ROADMAP.md` Phase 1 Day 3 |

Metrics to publish (measured): attack success rate, time-to-contain, %
sensitive data reached pre-containment, false-positive containment rate, %
legitimate flows preserved, mean time to recover. No adjectives as evidence.

## 7. Coding conventions

- Fail closed beats fail operational, every time — explicit exceptions only.
- Every autonomous path must be dry-runnable (`--dry-run` / `DRY_RUN=1`).
- Modules print their own "I exist and my contract is X" on boot.
- Docstrings state limits, not marketing.
- Comments reference ticket/doc IDs when non-obvious.
- No TODO without an issue link or `CHANGELOG.md` park note.

## 8. Commands (once code lands)

```bash
# install
pip install -r raksha-code/spine/requirements.txt
# spine smoke
pytest tests/ -q
# citizen message filter demo
python -m citizen.inference.messageguard --text "your KYC expires..." --lang te
# sentinel hospital sim
cd deploy/hospital && docker compose --profile sim up
# full raavan scenario
python -m evals.run --scenario raavan/killchain_01.yaml --baseline raksha
# stage rehearsal
python -m evals.stage --act 2 --dry-run
```

## 9. Definition of done (for every milestone)

Tests green · docs updated (`CHANGELOG.md` + touched file headers) ·
limits documented · dry-run verified · no secrets · no new [VERIFY] facts
left dangling in docs.
