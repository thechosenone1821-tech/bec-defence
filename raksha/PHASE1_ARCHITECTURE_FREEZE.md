> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../docs/STATUS.md); see the [retired code note](../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# RAKSHA — Phase 1 Architecture Freeze

> **Status:** Phase 1 documentation complete; Phase 2, Phase 3 and Phase 4 code later authorized · **Date:** 2026-11-26 · **Branch:** `arena/3b136fd9-bec-defence`
>
> **Later-state note:** this file is the Phase 1 planning snapshot. Statements
> below such as "Phase 2 implementation has not started" describe that snapshot,
> not the current repo. Phase 2 separation code and Phase 3 shared contracts are
> recorded in [`PHASE2_CODE_LAYOUT.md`](PHASE2_CODE_LAYOUT.md),
> [`PHASE3_CONTRACT_SPINE.md`](PHASE3_CONTRACT_SPINE.md) and
> [`PHASE4_CITIZEN_CONSOLIDATION.md`](PHASE4_CITIZEN_CONSOLIDATION.md).
>
> **Authority:** planning freeze only. Runtime source of truth remains
> `../raksha-code/`. Current verified build state remains
> [`../BUILD_STATE.md`](../docs/STATUS.md). This phase moved no code, renamed no
> directory, changed no configuration, and disabled no feature.
>
> **Trigger:** the maintainer asked to continue with Phase 1 of
> [`COMBINED_SYSTEM_ROADMAP.md`](COMBINED_SYSTEM_ROADMAP.md). That request is
> treated as authorization for **Phase 1 documentation work**, not as
> authorization for Phase 2 file moves or implementation. A later maintainer
> request explicitly authorized Phase 2 code work with the additional
> "separate but integrated" constraint; see
> [`PHASE2_CODE_LAYOUT.md`](PHASE2_CODE_LAYOUT.md) and
> [`adr/ADR-010-separation-boundaries.md`](adr/ADR-010-separation-boundaries.md).
>
> **Companion artifacts:** [`PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](PHASE1_SOURCE_OF_TRUTH_MATRIX.md),
> [`adr/README.md`](adr/README.md), and
> [`../raksha-code/citizen/voiceguard/FROZEN.md`](../raksha-code/citizen/voiceguard/FROZEN.md).

---

## 1. Frozen architecture decision

The entire repository is planned as **one combined system with exactly two apps**:

| App | Protects | Allowed surface |
| --- | --- | --- |
| **RAKSHA Citizen** | People on their phones | `apps/citizen/` after Phase 2; today `../raksha-code/citizen/` |
| **RAKSHA Infra / Sentinel** | Critical-infrastructure estates | `apps/infra/` after Phase 2; today `../raksha-code/spine/` + `../raksha-code/sentinel/` |

Both apps sit on **one shared spine**: contracts, telemetry bus, evidence ledger,
Governor, configuration and reproducible evals. There is no third app for
governance, enterprise backend, MessageGuard, console, or red-team tooling.

**Frozen rules**

1. One implementation per capability.
2. One canonical home per directory.
3. One diagram, one ownership matrix, one status board.
4. AI proposes; the Governor disposes.
5. Dry-run remains the only executor mode.
6. No path bypasses signature verification or the deterministic Governor.
7. VoiceGuard is a **frozen seam**, not a Phase 1–10 deliverable.
8. Phase 2 implementation has not started.

---

## 2. The one system diagram

```text
                         ┌──────────────────────────────────────────┐
                         │            ONE SHARED SPINE               │
                         │  contracts · event envelope · reason codes │
                         │  bus · ledger · Governor · config · evals  │
                         └───────────────────┬──────────────────────┘
                                             │
                  ┌──────────────────────────┴──────────────────────────┐
                  │                                                     │
        ┌─────────▼─────────┐                               ┌──────────▼──────────┐
        │   APP 1: CITIZEN  │                               │ APP 2: INFRA /      │
        │  phone-first PWA   │                               │ SENTINEL backend    │
        │  + thin local API  │                               │ + read-only console  │
        └─────────┬─────────┘                               └──────────┬──────────┘
                  │                                                     │
       MessageGuard · risk fusion · i18n            8 organs · campaign fusion · planner
       report rail · offline queue · panic          Governor · dry-run executor · WS/API
       1930 / helpline copy · no raw score          RAAVAN replay · metrics · ledger view
                  │                                                     │
                  └────────────── signed, sanitized events ─────────────┘

        ┌──────────────────────────────────────────────────────────────────────┐
        │  PORT SOURCES / HISTORICAL ARCHIVE — not independent apps             │
        │  archive/provenance/raksha-enterprise/ · archive/provenance/raksha-governance/ · raksha-messageguard/      │
        │  random project…/ · specs/ · root build logs · root EIGENSHIELD doc  │
        └──────────────────────────────────────────────────────────────────────┘

        ┌──────────────────────────────────────────────────────────────────────┐
        │  FROZEN SEAM — VoiceGuard / MAYA                                     │
        │  parked by explicit request; no migration, no phase exit criterion,   │
        │  no new claim, no code change, future Phase 11 re-entry gate only     │
        └──────────────────────────────────────────────────────────────────────┘
```

The diagram is the Phase 1 planning authority for repository shape. Older
diagrams remain as historical/target context; where they imply a separate
VoiceGuard integration path or a second spine, they are superseded by this file
and the source-of-truth matrix.

---

## 3. Maintainer decisions recorded, not executed

| # | Decision from the 10-phase roadmap | Phase 1 planning status | Implementation gate |
| --- | --- | --- | --- |
| 1 | `raksha-code/` is the canonical runtime source | Frozen in the matrix | No directory moves performed |
| 2 | `apps/citizen/` + `apps/infra/` + `packages/` is the target layout | Frozen as target only | Phase 2 still requires explicit go-ahead |
| 3 | One implementation per duplicated capability | Frozen in ADR-001…ADR-008 | No duplicate removed yet |
| 4 | VoiceGuard is a parked seam, not a phase | Frozen in ADR-009 + `FROZEN.md` | Future Phase 11 only |
| 5 | `archive/provenance/` is the final home for retired standalone projects | Frozen as target only | Deletion/archiving deferred to Phase 10 |

**Judgment call:** "continue with phase 1" was interpreted as permission to
complete Phase 1 documentation. It was **not** interpreted as permission to
move code, create the target `apps/` / `packages/` directories, or weaken any
safety rail. The maintainer is notified here and in the final response.

---

## 4. Phase 1 artifacts

| Artifact | Purpose |
| --- | --- |
| `PHASE1_ARCHITECTURE_FREEZE.md` | one diagram, frozen decisions, phase boundary, exit gate |
| `PHASE1_SOURCE_OF_TRUTH_MATRIX.md` | every top-level directory and duplicate capability assigned one owner |
| `adr/README.md` | ADR register and status vocabulary |
| `adr/ADR-001…ADR-008` | one ADR per duplicate capability |
| `adr/ADR-009` | VoiceGuard frozen-seam decision |
| `../raksha-code/citizen/voiceguard/FROZEN.md` | in-tree marker that the seam is parked |
| Synced doc headers | historical docs point to the combined-system plan instead of acting as current owners |

---

## 5. Exit gate

| Gate | Result |
| --- | --- |
| One system diagram published | **Yes** — §2 |
| Every project-controlled top-level directory assigned one owner category | **Yes** — source-of-truth matrix §2 |
| No directory has two owners | **Yes** — matrix §2, with nested VoiceGuard seam explicitly excluded from Phase 1–10 deliverables |
| Every duplicate capability has one ADR | **Yes** — ADR-001…ADR-008 |
| No capability has two canonical homes | **Yes** — matrix §5 + ADR decisions |
| VoiceGuard appears only as a parked seam | **Yes** — ADR-009, `FROZEN.md`, and parked-doc headers |
| Phase 2 implementation started | **No** — deliberately deferred |

---

## 6. Honesty and safety notes

- **Docs-only change.** No `.py`, `.js`, `.json`, `.yaml`, fixture, test, config,
  CI file, or generated artifact was modified. New files are Markdown; edited
  files are Markdown.
- **Runtime state unchanged.** The verified state in `../BUILD_STATE.md` remains
  the current build-state authority. This phase introduces no new test count,
  accuracy number, latency figure, or deployment claim.
- **No safety rail relaxed.** Governor, ledger, signature checks, canary
  semantics, dry-run defaults, and append-only decisions remain binding.
- **No real-world claim.** Fixture and synthetic-corpus measurements keep their
  existing conditions. Real-world VoiceGuard / MessageGuard / detection claims
  remain out of scope.
- **Next phase is gated.** Phase 2 must not begin until the maintainer explicitly
  authorizes implementation or ratifies the five decisions in §3.
