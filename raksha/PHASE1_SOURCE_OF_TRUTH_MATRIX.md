# RAKSHA — Phase 1 Source-of-Truth Matrix

> **Status:** frozen for Phase 1 planning; Phase 2 layout, Phase 3 contracts and Phase 4 Citizen consolidation recorded separately · **Date:** 2026-11-26 · **Branch:** `arena/3b136fd9-bec-defence`
>
> **Phase 3/4 note:** `../packages/contracts/` now owns the shared canonical JSON,
> envelope, band, reason, config, backend, reserved VoiceGuard and i18n-rendering
> contracts; Citizen sentences live in `../apps/citizen/copy.py`. This matrix
> remains the Phase 1 ownership authority; see
> [`../raksha/PHASE3_CONTRACT_SPINE.md`](PHASE3_CONTRACT_SPINE.md) and
> [`../raksha/PHASE4_CITIZEN_CONSOLIDATION.md`](PHASE4_CITIZEN_CONSOLIDATION.md).
>
> **Phase 2 note:** `apps/` and `packages/` now exist as the visible code
> layout, with `raksha-code/` retained as a compatibility/provenance layer.
> This matrix remains the ownership authority; see
> [`PHASE2_CODE_LAYOUT.md`](PHASE2_CODE_LAYOUT.md) for implementation details.
>
> This matrix is the ownership companion to
> [`PHASE1_ARCHITECTURE_FREEZE.md`](PHASE1_ARCHITECTURE_FREEZE.md). It does not
> move files. It assigns exactly one owner category to every project-controlled
> top-level directory and exactly one canonical home to every duplicated
> capability. Runtime status remains in [`../BUILD_STATE.md`](../docs/STATUS.md).

---

## 1. Owner vocabulary

| Category | Meaning | May be imported / treated as current source of truth? |
| --- | --- | --- |
| **CANONICAL** | Current runtime source of truth | Yes, until Phase 2 reorganisation |
| **DOCS-SOURCE** | Current documentation authority | Yes, for program documentation |
| **PORT-SOURCE** | Code/content to be ported into a canonical home | No — not a runtime authority |
| **HISTORICAL-ARCHIVE** | Retained provenance or historical build log | No — read for context only |
| **FROZEN-SEAM** | Explicitly parked future work | No — not a Phase 1–10 deliverable |
| **EXCLUDED-SYSTEM** | Git, virtualenv, cache, or tool-managed directory | No product owner; outside the architecture |

`EXCLUDED-SYSTEM` rows are not project trees. They cannot own a capability and
cannot become canonical. This avoids pretending that `.git` or `.venv` is an app.

---

## 2. Every top-level directory

| Directory | Owner category | One-line reason | Target after Phase 2+ |
| --- | --- | --- | --- |
| `.git/` | EXCLUDED-SYSTEM | Git metadata; never a product tree | remains excluded |
| `.venv/` | EXCLUDED-SYSTEM | Local dependency environment; not tracked deliverable | remains excluded |
| `raksha/` | DOCS-SOURCE | Current RAKSHA program docs, changelog, evals, roadmap and Phase 1 artifacts | `docs/program/` + `docs/adr/` |
| `raksha-code/` | CANONICAL | Current shipped runtime: Citizen, spine, Sentinel organs, RAAVAN, corpora, evals, tests | `apps/` + `packages/` + `tools/` |
| `archive/provenance/raksha-enterprise/` | PORT-SOURCE | Part 6 backend with FastAPI/WS, auth, scoped tokens, SQLite ledger, metrics, RAAVAN and 8 organs | `apps/infra/` + selected `packages/` |
| `archive/provenance/raksha-governance/` | PORT-SOURCE | Part 5 governance: five invariants, TCB twins, FIDO2, commander, planner, dry-run executor | `packages/governance/` |
| `raksha-messageguard/` | PORT-SOURCE | Alternative Part 3 MessageGuard: CLI, legacy organ adapter, i18n, Hinglish corpus, extra tests | `apps/citizen/messageguard/` |
| `random project that ew need to integrate/` | HISTORICAL-ARCHIVE | Already-integrated standalone Part 3 snapshot; `INTEGRATED.md` marks it provenance-only | `archive/provenance/` |
| `specs/` | HISTORICAL-ARCHIVE | Superseded 7-part build split; useful lineage, not the new architecture | `docs/specs/` rewritten at Phase 10 |

**Gate:** no project-controlled top-level directory has two categories. The
`raksha-code/citizen/voiceguard/` frozen seam is a nested exception documented in
§4; it is not a second top-level owner.

---

## 3. Root-level files

| File(s) | Owner category | Reason |
| --- | --- | --- |
| `.gitignore` | CANONICAL (repo config) | Current ignore rules for caches and local environments |
| `BUILD_STATE.md` | DOCS-SOURCE (status authority) | Current verified whole-app state; Phase 1 docs must point back here |
| `README.md` | HISTORICAL-ARCHIVE | EIGENSHIELD v2.0 reference, not the combined-system README; Phase 10 will replace it |
| `CITIZEN_APP_BUILD.md` | HISTORICAL-ARCHIVE | Historical Citizen build snapshot |
| `INFRA_BUILD.md` | HISTORICAL-ARCHIVE | Historical Sentinel build snapshot |
| `MAYA_BUILD.md` | HISTORICAL-ARCHIVE + FROZEN-SEAM | VoiceGuard deep spec; parked by Phase 1 |
| `VOICEGUARD_ROADMAP.md` | HISTORICAL-ARCHIVE + FROZEN-SEAM | VoiceGuard 5-phase roadmap; not one of the combined-system 10 phases |

---

## 4. Frozen VoiceGuard seam

| Path / document | Status | Phase 1 treatment |
| --- | --- | --- |
| `raksha-code/citizen/voiceguard/` | FROZEN-SEAM | Parked; `FROZEN.md` added, no Python changed |
| `raksha-code/citizen/voiceguard/MODEL_CARD.md` | FROZEN-SEAM | Historical model card; no new claim introduced |
| `raksha-code/evals/run_maya.py` | FROZEN-SEAM | Excluded from the combined eval runner until Phase 11 |
| `raksha-code/citizen/app/maya-capture*.js` | FROZEN-SEAM | Existing browser artefacts remain as shipped; no integration work |
| `raksha-code/citizen/app/index.html` / `app.js` "Check Voice" references | FROZEN-SEAM | Existing UI seam only; not a Phase 1–10 deliverable |
| `VOICEGUARD_ROADMAP.md` | FROZEN-SEAM | Header now marks it parked |
| `MAYA_BUILD.md` | FROZEN-SEAM | Header now marks it parked; stale Maya name-status line fixed |
| `specs/02_citizen_voiceguard.md` | HISTORICAL-ARCHIVE | Historical Part 2 spec, superseded for combined-system planning |
| `archive/provenance/raksha-enterprise/raksha-enterprise/raksha/organs/voiceguard.py` | PORT-SOURCE / FROZEN-SEAM | Enterprise-side organ named VoiceGuard; not a Citizen VoiceGuard integration path |

**Gate:** VoiceGuard appears in Phase 1 only as a parked seam, historical context,
or future re-entry condition. It is not a phase deliverable and not an accuracy
claim.

---

## 5. Capability ownership — one canonical home each

| Capability | Current canonical home | Port / provenance sources, NOT canonical | Future target | ADR |
| --- | --- | --- | --- | --- |
| Telemetry bus / API / WS boundary | `raksha-code/spine/bus.py`; `raksha-code/citizen/api.py` is a thin app adapter | `archive/provenance/raksha-enterprise/.../raksha/bus/`, `archive/provenance/raksha-enterprise/.../pipeline/runner.py` | `packages/spine/bus.py` + thin `apps/*/api.py` adapters | [ADR-001](adr/ADR-001-single-bus.md) |
| Evidence ledger | `raksha-code/spine/ledger.py`, `ledger_anchor.py`, `ledger_cli.py` | `archive/provenance/raksha-governance/.../raksha/ledger.py`; `archive/provenance/raksha-enterprise/.../raksha/ledger/` | `packages/ledger/` | [ADR-002](adr/ADR-002-single-ledger.md) |
| Governor / safety core | `raksha-code/spine/governor.py`, `tcb_core.py`, `tcb_mirror.py`, `watchdog.py`, `approval_token.py` | `archive/provenance/raksha-governance/.../raksha/governor.py` + invariants; `archive/provenance/raksha-enterprise/.../pipeline/governor.py` | `packages/governance/` | [ADR-003](adr/ADR-003-single-governor.md) |
| Containment planner | `raksha-code/spine/containment.py` | `archive/provenance/raksha-governance/.../raksha/planner.py`; `archive/provenance/raksha-enterprise/.../pipeline/planner.py` + `topology.py` | `packages/governance/planner.py` | [ADR-004](adr/ADR-004-single-planner.md) |
| Infra detection organs | `raksha-code/sentinel/shields/` | `archive/provenance/raksha-enterprise/.../raksha/organs/` | `apps/infra/detectors/` | [ADR-005](adr/ADR-005-single-organ-registry.md) |
| Citizen MessageGuard | `raksha-code/citizen/messageguard/` | `archive/provenance/messageguard-alternative/raksha/`; `archive/provenance/messageguard-snapshot/raksha/` (provenance only) | `apps/citizen/messageguard/` | [ADR-006](adr/ADR-006-single-messageguard.md), [ADR-013](adr/ADR-013-messageguard-single-source.md) |
| Eval runner / claims ledger | `raksha-code/evals/run_evals.py` + `evals/messageguard/` sub-runner | `archive/provenance/raksha-enterprise/.../tools/`; `raksha-messageguard/.../evals/`; standalone `evals/`; `evals/run_maya.py` frozen | `evals/runners/` + `evals/corpora/` + `evals/results/` | [ADR-007](adr/ADR-007-single-eval-runner.md) |
| Build-state / status document | `../BUILD_STATE.md` | `raksha/README.md` status header, `raksha/AI_HANDOFF.md` status table, `specs/00_INDEX.md` status board, root build logs, this Phase 1 plan | `docs/STATUS.md` | [ADR-008](adr/ADR-008-single-status-document.md) |

**Gate:** each capability has one canonical home. Thin app adapters, generated
reports, archived snapshots and port sources are explicitly not canonical.

---

## 6. Verification of the Phase 1 invariants

- [x] One diagram exists in `PHASE1_ARCHITECTURE_FREEZE.md`.
- [x] Every project-controlled top-level directory has exactly one owner category.
- [x] System directories are excluded rather than falsely assigned an app owner.
- [x] Every duplicate capability has one ADR and one canonical home.
- [x] VoiceGuard has a frozen-seam ADR and an in-tree `FROZEN.md` marker.
- [x] Status authority remains `../BUILD_STATE.md`; planning docs do not become a second status board.
- [x] No implementation, file move, config change, generated artifact edit, or safety-rail change is included.
