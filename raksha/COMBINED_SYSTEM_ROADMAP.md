# RAKSHA — Entire-Repo Combined System: 10-Phase Roadmap

> **Status:** FROZEN — ten-phase board complete through Phase 10 · **Date:** 2026-11-26 · **Branch:** `arena/3b136fd9-bec-defence`
> **Canonical status:** [`../docs/STATUS.md`](../docs/STATUS.md) · **Entry point:** [`../README.md`](../README.md) · **Measurements:** [`../EVALS.md`](../EVALS.md)
> **Phase 11:** NOT OPEN. VoiceGuard integration remains a separate future phase
> with the written re-entry gate in [`../docs/STATUS.md`](../docs/STATUS.md).
> **Phase 1:** documentation complete; implementation was gated at that time. See
> [`PHASE1_ARCHITECTURE_FREEZE.md`](PHASE1_ARCHITECTURE_FREEZE.md),
> [`PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](PHASE1_SOURCE_OF_TRUTH_MATRIX.md) and
> [`adr/README.md`](adr/README.md).
>
> **Request:** turn the whole GitHub repository into one combined system with exactly
> **two apps** — **RAKSHA Citizen** and **RAKSHA Infra / Sentinel** — through a
> **10-phase roadmap**. **VoiceGuard is deliberately left out** of these 10 phases
> because it is still being built; it gets a contract seam, not an integration.
>
> **Authorization history:** this roadmap and its Phase 1 artifacts were
> documentation-only. Later maintainer requests explicitly authorized Phase 2
> separation-preserving code, Phase 3 shared-contract code, and Phase 4 Citizen
> consolidation **with no AI models run**. See
> [`PHASE2_CODE_LAYOUT.md`](PHASE2_CODE_LAYOUT.md),
> [`PHASE3_CONTRACT_SPINE.md`](PHASE3_CONTRACT_SPINE.md),
> [`PHASE4_CITIZEN_CONSOLIDATION.md`](PHASE4_CITIZEN_CONSOLIDATION.md), and
> [`adr/ADR-012-citizen-consolidation.md`](adr/ADR-012-citizen-consolidation.md).
> **Phase 5 through Phase 10 are implemented and frozen.** The historical
> gating language below is retained only as provenance; the current board is
> [`../docs/STATUS.md`](../docs/STATUS.md).

---

## 1. What "combined system" means

The target is **not** a folder of many mini-projects. It is:

```text
                         ┌──────────────────────────────┐
                         │      ONE SHARED SPINE        │
                         │  contracts · bus · ledger    │
                         │  Governor · config · evals   │
                         └──────────────┬───────────────┘
                                        │
              ┌─────────────────────────┴─────────────────────────┐
              │                                                   │
     ┌────────▼─────────┐                               ┌────────▼─────────┐
     │  APP 1: CITIZEN  │                               │ APP 2: INFRA /    │
     │  phone-first PWA  │                               │ SENTINEL backend  │
     │  + local API      │                               │ + read-only SOC   │
     └────────┬─────────┘                               └────────┬─────────┘
              │                                                   │
   MessageGuard · risk engine · i18n         8 organs · campaign fusion · planner
   report rail · offline queue · panic      Governor · dry-run executor · WS/API
   [VoiceGuard seam — PARKED]               RAAVAN replay · metrics · console
```

**Rules of the target shape**

1. **Two apps, one spine.** Citizen and Infra/Sentinel share contracts, evidence,
   configuration and the Governor. They are not two separate products with two
   safety models.
2. **No third app.** `archive/provenance/raksha-enterprise/`, `archive/provenance/raksha-governance/`,
   `raksha-messageguard/` and the old standalone folders are **source material**,
   not independent deliverables. Each capability is ported into one canonical home.
3. **One implementation per capability.** One MessageGuard, one Governor, one
   ledger, one bus, one containment planner, one eval runner, one status document.
4. **AI proposes, Governor disposes.** No path may bypass the deterministic gate.
5. **Dry-run by default.** No real host, VLAN, session or phone action is taken.
6. **VoiceGuard is parked.** The existing `citizen/voiceguard/` area stays frozen
   behind a clearly labelled interface. It is not merged, not used as a phase exit
   criterion, and not part of any accuracy claim in this roadmap.

---

## 2. Current repo → target home

| Current area | What it is today | Target home in combined system | Consolidation decision |
| --- | --- | --- | --- |
| `raksha/` | Program docs, architecture, changelog, evals | `docs/program/` + `docs/adr/` | Keep as documentation source of truth; add this roadmap and one system map |
| `specs/` | Old 7-part build split | `docs/specs/` | Rewrite into a **2-app + shared-spine** contract set; keep old files as historical specs |
| `raksha-code/` | Main application tree: `citizen/`, `sentinel/`, `spine/`, `raavan/`, `corpora/`, `evals/`, `tests/` | Canonical code root, reorganised into `apps/` + `packages/` + `tools/` | Primary source of truth for runtime code |
| `raksha-code/citizen/` | Citizen PWA, API, MessageGuard v1, risk engine, i18n, report rail | `apps/citizen/` | Keep; exclude VoiceGuard from integration |
| `raksha-code/citizen/voiceguard/` | MAYA / synthetic-speech placeholder | `apps/citizen/voiceguard/` **frozen seam** | No migration, no new tests, no accuracy claims in these 10 phases |
| `raksha-code/sentinel/` | 8 shield organs | `apps/infra/detectors/` | Canonical organ registry after comparison with enterprise organs |
| `raksha-code/spine/` | Bus, ledger, Governor, TCB, containment, sanitizer, config | `packages/spine/` | Reconcile with governance and enterprise implementations; one of each wins |
| `raksha-code/raavan/`, `corpora/`, `evals/` | Red-team replay, corpora, measurement | `tools/raavan/`, `evals/corpora/`, `evals/runners/` | One reproducible eval entry point |
| `archive/provenance/raksha-enterprise/raksha-enterprise/` | Part 6 enterprise backend: FastAPI + WS, auth, 8 organs, fusion, planner, Governor G1–G4, SQLite ledger, metrics, RAAVAN, 79 tests | `apps/infra/backend/` + selected `packages/spine/` capabilities | Port stronger API/WS/auth/metrics/SQLite features; retire duplicate bus and organ copies |
| `archive/provenance/raksha-governance/raksha-governance/` | Part 5 governance: five invariants, TCB twins, FIDO2, planner, commander, dry-run executor, 82 tests | `packages/governance/` | Merge with existing `spine/governor.py`, `containment.py`, `tcb_*`; one Governor, one planner, one executor |
| `archive/provenance/messageguard-alternative/raksha/` (formerly `raksha-messageguard/raksha/`) | Alternative Part 3 MessageGuard: reasons/i18n, CLI, legacy adapter, 431 fixtures, historical tests | `apps/citizen/messageguard/` | ✅ Phase 5: compared, ported 46 unique Hinglish rows + adapter/CLI value, archived duplicate |
| `archive/provenance/messageguard-snapshot/raksha/` (formerly `random project that ew need to integrate/raksha/`) | Part 3 MessageGuard snapshot, already integrated in the previous change | `archive/provenance/` | ✅ Phase 5: provenance only; `INTEGRATED.md` marks it non-runtime |
| Root `BUILD_STATE.md`, `CITIZEN_APP_BUILD.md`, `INFRA_BUILD.md`, `MAYA_BUILD.md`, `VOICEGUARD_ROADMAP.md`, root `README.md` | Historical build logs and EIGENSHIELD lineage | `docs/status/` + `docs/archive/` | Replace "many status boards" with one `docs/STATUS.md`; keep originals labelled historical |

**Current anchor:** Phases 6–8 are the current implementation state. Under the
maintainer's no-AI-models instruction, the deterministic suite reports **196
root Python checks**, **171 legacy-cwd Python checks**, **60 Node checks** and
**256 total passing checks**; 23 model-dependent Python test files, one frozen
MAYA capture Node test file and two archived MessageGuard provenance test
directories were skipped/ignored. No AI model module loaded in the pytest
process. Exact commands, skip list and further checks are in
[`../BUILD_STATE.md`](../docs/STATUS.md), [`EVALS.md`](../EVALS.md),
[`../specs/07_spine.md`](../specs/07_spine.md),
[`PHASE4_CITIZEN_CONSOLIDATION.md`](PHASE4_CITIZEN_CONSOLIDATION.md) and
[`PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md`](PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md).
Phase 2/3/4 numbers in their own reports are historical snapshots. All such
numbers are fixture/sandbox measurements, never field claims.

---

## 3. North-star layout

This is the conceptual destination, not an instruction to implement it now:

```text
bec-defence/
├── README.md                  # one entry point: two apps, one spine
├── docs/
│   ├── STATUS.md              # one living build-state document
│   ├── COMBINED_SYSTEM_ROADMAP.md
│   ├── program/               # architecture, context, changelog, evals
│   ├── specs/                 # 2-app contracts, rewritten from specs/
│   ├── adr/                   # one decision record per duplicate resolved
│   └── archive/               # historical build logs, clearly labelled
├── apps/
│   ├── citizen/               # APP 1
│   │   ├── api/               # same-origin FastAPI service
│   │   ├── pwa/               # offline shell, 1930, queue, family mode
│   │   ├── messageguard/      # single canonical detector
│   │   ├── risk/              # bounded fusion, no SAFE verdict
│   │   ├── i18n/              # en/hi/te reason sentences
│   │   └── voiceguard/        # FROZEN SEAM — integrate later
│   └── infra/                 # APP 2
│       ├── backend/           # one FastAPI + WS + metrics service
│       ├── detectors/         # one 8-organ registry
│       ├── console/           # read-only SOC UI; cannot override Governor
│       └── raavan/            # sandbox replay player
├── packages/
│   ├── contracts/             # event envelope, verdicts, reason codes, bands
│   ├── spine/                 # bus, sanitizer, entity graph, config pinning
│   ├── governance/            # Governor, TCB, FIDO2, planner, executor
│   └── ledger/                # append-only hash chain + verify CLI
├── evals/
│   ├── corpora/               # one labelled corpus per detector
│   ├── runners/               # one reproducible measurement command
│   └── results/               # generated, never hand-edited
├── tools/                     # seeding, ledger verify, corpus generators
├── tests/                     # one Python suite + one browser suite
└── archive/provenance/        # retired standalone projects, read-only
```

---

## 4. The 10 phases

### Phase 1 — Freeze the two-app architecture and source-of-truth matrix

**Goal:** stop ambiguity before moving anything.

**Work**
- Publish one system diagram: Citizen, Infra/Sentinel, shared spine.
- Inventory every top-level directory and assign exactly one of: canonical,
  port source, docs source, historical archive, or frozen seam.
- Write an ADR for every duplicate capability: bus, ledger, Governor, planner,
  organs, MessageGuard, eval runner, status doc.
- Mark `citizen/voiceguard/` as **frozen / future integration**.

**Exit gate**
- No directory has two owners.
- No capability has two canonical homes.
- VoiceGuard appears only as a parked seam, never as a phase deliverable.

---

### Phase 2 — Create the canonical monorepo layout

> **Phase 2 code status (2026-11-26):** implemented as a
> **separation-preserving scaffold**, not a single blended app. See
> [`PHASE2_CODE_LAYOUT.md`](PHASE2_CODE_LAYOUT.md) and
> [`adr/ADR-010-separation-boundaries.md`](adr/ADR-010-separation-boundaries.md).
> VoiceGuard / MAYA were left untouched and are hash-pinned.

**Goal:** make the repository look like one system made of **separate apps**
rather than a collection of uploads. Editing one app must not require editing
the other app.

**Work**
- Introduced `apps/`, `packages/`, `tools/`, root `tests/`, and `pytest.ini`.
- Moved editable Citizen Python modules into `apps/citizen/`; left the frozen
  VoiceGuard/MAYA tree, PWA assets and fixtures in `raksha-code/citizen/` with
  compatibility symlinks.
- Added `apps/infra/backend/`, `apps/infra/detectors/`, and
  `apps/infra/console/` as Infra-owned surfaces.
- Added `packages/contracts`, `packages/spine`, `packages/governance`, and
  `packages/ledger` as the only shared integration layer.
- Added AST-based boundary tests and a frozen-asset hash checker.
- Deferred docs/build-log moves and root README rewrite to Phase 10.

**Exit gate**
- Two apps are visibly separate and independently editable. **Yes.**
- Shared integration goes through `packages/`, not app-to-app imports. **Yes.**
- VoiceGuard/MAYA untouched. **Yes** — 28 assets hash-pinned.
- One root `README.md` explains the whole repo in under one screen. **Deferred to Phase 10.**
- `raksha-code/` is explicitly a compatibility/provenance layer, not a second app. **Yes.**

---

### Phase 3 — Unify shared contracts and the spine

> **Phase 3 code status (2026-11-26):** implemented as a **shared-contract and
> compatibility-delegation scaffold**. See
> [`PHASE3_CONTRACT_SPINE.md`](PHASE3_CONTRACT_SPINE.md). The two app roots are
> still separate and VoiceGuard/MAYA remain untouched. Full runtime merges are
> deliberately deferred.

**Goal:** both apps speak one language before features are merged.

**Work — implemented**
- One canonical JSON rule in `packages/contracts/canonical.py`; one signed-event
  validator in `packages/contracts/envelope.py` for Citizen/Infra/RAAVAN/eval,
  sealed organ and enterprise I1 wire profiles.
- One verdict-band table, one legacy organ band map and one `MSG-*` / reason-code
  catalogue in `packages/contracts/`, re-exported by `apps/citizen/messageguard/`.
- One backend-route contract mapping spine-v2 and enterprise-i1 API/WS surfaces;
  Citizen health and Infra `/app/contract` expose the same contract card.
- One `append / verify` ledger interface and one CLI in `packages/ledger/`; legacy
  `spine.ledger_cli` delegates to it.
- One config-pin set, auth-scope list, boot-manifest path list, sanitizer rule set
  and entity-graph token path in `packages/`. Shipped compatibility modules import
  them rather than owning duplicates.
- One reserved VoiceGuard contract slot with no VoiceGuard/MAYA logic import.
- One signature + Governor `SharedActionGate`; `tools/check_phase3_contracts.py`
  AST-checks app imports against `FORBIDDEN_APP_BYPASS_ROOTS`.

**Exit gate**
- One envelope validates identically in Citizen, Infra, RAAVAN, and eval harnesses.
  **Yes** — root and legacy-cwd tests also cover sealed organ and enterprise I1
  interop. Infra exposes the same event/backend contract.
- `ledger verify` works from one CLI against one chain. **Yes** —
  `packages.ledger.cli` and legacy `spine.ledger_cli` verify one populated chain
  with identical JSON.
- No app can bypass signature verification or the Governor. **Yes** — the new
  action path requires `validate_envelope()` plus Governor approval; app import
  bypass roots are rejected by the contract checker.

**Scope honesty:** this phase unifies contracts and compatibility seams, not all
runtime implementations. Full bus/WS, Governor, organ registry, eval/archive and
packaging moves remain Phases 6–10.

---

### Phase 4 — Consolidate the Citizen app, excluding VoiceGuard

> **Phase 4 code status (2026-11-26):** implemented. See
> [`PHASE4_CITIZEN_CONSOLIDATION.md`](PHASE4_CITIZEN_CONSOLIDATION.md).
> The maintainer explicitly required **no AI models** for this phase; no model
> inference, Commander call, MAYA classifier call, or model-dependent test file
> was run. VoiceGuard/MAYA remain untouched.

**Goal:** one phone-first app with all non-voice citizen features.

**Work — implemented**
- One Citizen service and one physical PWA shell; compatibility aliases remain
  symlinks. `/api/citizen/capabilities` enumerates `screen_message`, `assess`,
  `report`, offline queue, panic/1930, family mode and retention.
- Shared i18n/reason-rendering logic in `packages/contracts/i18n.py`;
  citizen-facing en/hi/te sentences in `apps/citizen/copy.py`. Risk engine,
  fusion, message explanations, report explanations, disclaimers and language
  lists now use that split.
- "No raw score to a citizen", "no SAFE verdict" and "no PII leaves the phone"
  preserved and enforced by `tools/check_phase4_citizen.py` plus acceptance tests.
- `VOICEGUARD_ENABLED=False`, `NO_AI_MODELS=True`, a documented
  `DisabledVoiceGuard` interface, a model-free retention/consent gate, and a
  single read-only legacy adapter for future Phase 11 only.
- Runtime-only shell overlay changes the voice tab to "not integrated yet" and
  disables frozen voice controls without editing any frozen PWA/VoiceGuard file.

**Exit gate**
- Exactly one Citizen service and one PWA shell. **Yes** — physical-path checker.
- MessageGuard, risk fusion, reporting and multilingual copy work end-to-end.
  **Yes** — en/hi/te API acceptance test.
- Voice tab honestly says "not integrated yet"; no clone-detection claim exists.
  **Yes** — runtime HTML/JS/manifest checks and active-text scan.

**Scope honesty:** Phase 5 MessageGuard single-source work is not started.

---

### Phase 5 — Make MessageGuard single-source — ✅ implemented

**Goal:** remove the last duplicate citizen detector.

**Work — done**
- Kept the integrated v1 in `apps/citizen/messageguard/` as the one runtime
  baseline and extended its interface with `detect_language`, a legacy organ
  adapter and a sanitized operator CLI.
- Compared `archive/provenance/messageguard-alternative/raksha/` against it:
  reason/i18n catalogue, legacy organ adapter, CLI, Hinglish corpus, historical
  tests and FP review.
- Ported 46 unique Hinglish rows, adapter/CLI value and negation/FP regression
  coverage; retired the second scorer, `msg.*` catalogue, corpus, eval runner and
  generated document.
- Produced one 538-row corpus, one generated eval document, one `MSG-*`
  catalogue and one detector interface.
- Archived both historical trees under `archive/provenance/` with provenance
  notes and import guards.

**Exit gate — met**
- ✅ `pytest` finds one MessageGuard suite; no second scorer is importable.
- ✅ One `run_evals.py --check` reproduces the published 538-row numbers.
- ✅ All published numbers remain explicitly hand-authored / in-distribution.
- Details: [`PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md`](PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md)
  and [`adr/ADR-013-messageguard-single-source.md`](adr/ADR-013-messageguard-single-source.md).

---

### Phase 6 — Consolidate Infra detection organs

**Goal:** one 8-organ detection ring inside Infra/Sentinel.

**Work**
- Compare `raksha-code/sentinel/shields/` with `archive/provenance/raksha-enterprise/raksha/organs/`.
- Choose one organ registry and one `detect(event) -> finding` contract.
- Keep the physics/biology names as documentation, not as separate services.
- Port per-organ fixtures, silent-case fixtures and boundary tests.
- Ensure missing features degrade to "no detection", never to a false accusation.

**Exit gate**
- Eight organs, one registry, one telemetry path.
- Forged/unsigned/tampered events are quarantined and never detected as real.
- Every organ has a firing fixture and a silent fixture.

**Phase 6–8 status: implemented.** The active one-registry detector, unified
runtime, deterministic safety brain, append-only ledger, `/v1` API/WS surface
and read-only console are described in
[`PHASE678_UNIFIED_INTEGRATION.md`](PHASE678_UNIFIED_INTEGRATION.md) and
[`adr/ADR-014-phase6-8-unified-integration.md`](adr/ADR-014-phase6-8-unified-integration.md).
`tools/check_phase678_integration.py` and `tests/test_phase678_integration.py`
enforce the exit gates below with no AI models.

---

### Phase 7 — Consolidate response, governance and containment

**Goal:** one deterministic safety brain for the whole system.

**Work**
- Merge `raksha-governance` (five invariants, TCB twins, FIDO2, commander,
  executor) with `spine/governor.py`, `spine/containment.py`, `spine/tcb_*`,
  and enterprise G1–G4 rules.
- Keep one exhaustive/blast-radius planner and one dry-run executor.
- Keep one 10-tool allowlist and one schema lock.
- Guarantee decisions are sealed to the ledger **before** API/WS broadcast.
- Keep the AI Commander optional and clearly labelled fallback-only until a model
  is actually run.

**Exit gate**
- One Governor, one planner, one executor, one ledger write path.
- Crown-jewel / Tier-0 cuts are impossible by construction.
- Admin override remains impossible; refusals are first-class ledger records.

**Phase 7 status: implemented.** `packages/governance/safety.py` owns the one
planner/Governor/executor; crown cuts raise `UnsafeProposal`; refusals are
ledgered; the optional Commander is disabled and not run.

---

### Phase 8 — Unify Infra backend, API, WebSocket and read-only console

**Goal:** one operable Infra app surface.

**Work**
- Port enterprise `/v1/telemetry`, `/v1/state`, `/v1/decisions`,
  `/v1/ledger/verify`, `/v1/metrics`, quarantine and WS stream into the canonical
  backend.
- Build the missing SOC console as a **read-only** view over state and decisions.
- Show detection → proposal → decision → ledger sequence, including refusals.
- Keep token scopes, rate limits, dedupe and quarantine semantics from the
  enterprise build.
- Ensure the console has no button that can override, approve, or re-run a
  Governor decision.

**Exit gate**
- One Infra base URL, one WS stream, one metrics endpoint.
- A judge can watch a full campaign without `curl`.
- The console cannot mutate safety state.

**Phase 8 status: implemented.** `/app/console` is an operable read-only SOC
view of the deterministic fixture campaign, with detection → proposal →
decision → ledger sequence, refusals, quarantine, ledger verification and
metrics. One WebSocket function serves both `/v1/telemetry/stream` and the
Phase 3 compatibility `/ws/telemetry` alias.

---

### Phase 9 — FROZEN / implemented

**Goal:** one measurement story for the entire combined system. **Delivered.**

- One corpus generator: [`../evals/corpus.py`](../evals/corpus.py).
- One replay player: [`../evals/replay.py`](../evals/replay.py).
- One eval runner and drift check: [`../evals/run_evals.py`](../evals/run_evals.py).
- One generated document: [`../EVALS.md`](../EVALS.md), with sections for
  Citizen, MessageGuard, organs, governance and end-to-end replay.
- One claims ledger: [`../evals/claims_ledger.json`](../evals/claims_ledger.json),
  sourced by [`../evals/claims_sources.json`](../evals/claims_sources.json).
- Retired RAAVAN, corpora, MessageGuard and root eval runners are indexed under
  [`../archive/provenance/INTEGRATED.md`](../archive/provenance/INTEGRATED.md).

**Exit gate met:** `run_evals --check` is green for all five capabilities; every
outward number has a conditioned source row; real-world accuracy, latency and
uptime remain UNMEASURED; VoiceGuard evals stay out of this runner. Generated
eval documents are never hand-edited.

---

### Phase 10 — FROZEN / implemented

**Goal:** leave one maintainable repo, not ten half-repos. **Delivered.**

- One install, test, eval and run command set in [`../Makefile`](../Makefile);
  one process launcher in [`../tools/launch_apps.py`](../tools/launch_apps.py).
- CI gates in [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml) for
  Python suites, browser suites, eval drift, ledger verify, boot manifests, no
  secrets and no live-executor imports.
- Canonical [`../README.md`](../README.md),
  [`../docs/STATUS.md`](../docs/STATUS.md), [`../CHANGELOG.md`](../CHANGELOG.md)
  and [`../docs/README.md`](../docs/README.md).
- Retired standalone projects and historical uploads moved under
  [`../archive/provenance/`](../archive/provenance/) with `INTEGRATED.md` notes.
- Ten-phase board frozen; future Phase Eleven is NOT OPEN and has a written
  re-entry gate in the status board.

**Exit gate met:** a new engineer can clone, install, test, run both apps and
find status without historical logs; no duplicate runtime implementation remains
outside provenance; no real-world offensive or containment action is performed;
VoiceGuard is explicitly deferred with a written re-entry gate.

---

## 5. Parallel workstreams after Phase 3

The phases are numbered for a clear roadmap, but after contracts are frozen they
can be staffed as two app tracks plus one cross-cutting track:

| Track | Phases | Owner shape |
| --- | --- | --- |
| Citizen | 4 → 5 | PWA/API + MessageGuard + i18n |
| Infra / Sentinel | 6 → 7 → 8 | organs + governance + backend/console |
| Cross-cutting | 9 → 10 | evals + packaging + docs + CI |
| Parked | — | VoiceGuard; no owner assigned in these 10 phases |

---

## 6. Whole-program definition of done

- [ ] One repository, one `README.md`, one `docs/STATUS.md`.
- [ ] Exactly two apps: `apps/citizen/` and `apps/infra/`.
- [ ] One shared spine: contracts, bus, ledger, Governor, config, eval.
- [ ] One MessageGuard, one Governor, one planner, one executor, one organ registry.
- [ ] All staging directories are either ported or under `archive/provenance/`.
- [ ] One Python suite, one browser suite, one eval runner, one drift check.
- [ ] Generated eval docs are never hand-edited.
- [ ] Every measured number carries its condition; real-world claims stay blocked.
- [ ] Dry-run remains the only executor mode.
- [ ] VoiceGuard is **not** integrated and is not used as evidence of completion.

---

## 7. Explicit non-goals for these 10 phases

1. Do **not** integrate VoiceGuard / MAYA / voice capture / voice model artefacts.
2. Do **not** create a third app for governance, enterprise backend, or MessageGuard.
3. Do **not** run a live model as Commander and call it production.
4. Do **not** enable real containment, session revocation, or host actions.
5. Do **not** claim clone detection, real-speech accuracy, real-network detection,
   or field FPR.
6. Do **not** delete historical folders until Phase 10 has archived them with
   provenance notes.
7. Do **not** weaken the Governor, ledger, signature checks, canary semantics, or
   dry-run defaults to make a demo smoother.

---

## 8. VoiceGuard re-entry gate — future, not one of the 10 phases

VoiceGuard becomes a separate **Phase 11** only when all of the following are
ready:

- a frozen verdict/reason/retention contract;
- consent-gated capture and zero-retention proof;
- a model card that states what the model has and has not seen;
- en/hi/te citizen copy and reason rendering;
- synthetic-vs-real corpus separation and measured degradation curves;
- browser + Python tests, API boundary tests, and honesty gates;
- a feature flag that keeps it disabled by default;
- a written maintainer decision to replace the frozen seam.

Until then, the combined system ships as **Citizen + Infra/Sentinel**, with the
voice tab honestly labelled as deferred.

---

## 9. Historical maintainer decision — resolved

The five decisions below were the original Phase 1 gate. They were subsequently
authorized and implemented through Phase 10; this section is retained only as
provenance. The current board is [`../docs/STATUS.md`](../docs/STATUS.md).

1. `raksha-code/` was the canonical runtime source for the legacy port.
2. `apps/citizen/` + `apps/infra/` + `packages/` became the target layout.
3. One implementation per duplicated capability is now enforced.
4. VoiceGuard remains a parked seam, not one of the ten phases.
5. `archive/provenance/` is the final home for retired standalone projects.

Phase 1 documentation is recorded in
[`PHASE1_ARCHITECTURE_FREEZE.md`](PHASE1_ARCHITECTURE_FREEZE.md),
[`PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](PHASE1_SOURCE_OF_TRUTH_MATRIX.md) and
[`adr/README.md`](adr/README.md). No further implementation phase is open in
this repository.
