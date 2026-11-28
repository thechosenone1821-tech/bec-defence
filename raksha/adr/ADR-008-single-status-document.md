> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../../docs/STATUS.md); see the [retired code note](../../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# ADR-008 — One build-state / status document

> **Status:** Frozen for Phase 1 planning · **Date:** 2026-11-26
> **Decision owner:** repo maintainer (human) · **Recorded by:** AI-assisted maintainer session
> **Related:** [`../PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](../PHASE1_SOURCE_OF_TRUTH_MATRIX.md) §5, [`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) Phase 10

## Context

Several files contain status-like information:

- `../../BUILD_STATE.md` — current whole-app verified state, explicitly produced by running checks.
- `../../raksha/README.md` — verified counts and MessageGuard status in the header.
- `../../raksha/AI_HANDOFF.md` — current-status table for AI agents.
- `../../specs/00_INDEX.md` — 7-part status board and percentage estimates.
- Root `CITIZEN_APP_BUILD.md`, `INFRA_BUILD.md`, `MAYA_BUILD.md`, `VOICEGUARD_ROADMAP.md` — historical build snapshots and roadmaps.
- `../COMBINED_SYSTEM_ROADMAP.md` and the Phase 1 artifacts — planning documents.

If all of these are treated as equally current, the repo has several conflicting
status boards. Phase 1 needs one authority without deleting history.

## Decision

There is **one current build-state authority**.

- **Canonical status document (Phase 1):** `../../BUILD_STATE.md`.
- **Planning authority:** `../COMBINED_SYSTEM_ROADMAP.md`,
  `../PHASE1_ARCHITECTURE_FREEZE.md`, `../PHASE1_SOURCE_OF_TRUTH_MATRIX.md` and
  this ADR register. These describe future shape and ownership; they do not
  replace runtime status.
- **Supporting status views:** `../README.md`, `../AI_HANDOFF.md`,
  `../ROADMAP.md`, `../../specs/00_INDEX.md` and historical root docs are synced
  with headers that point back to the canonical status and planning authorities.
- **Future target:** `docs/STATUS.md` after Phase 10, with root `README.md`
  rewritten as one repository entry point.
- **Archive rule:** old status boards remain labelled historical; they are not
  silently deleted or treated as current.

## Consequences

**Positive**

- One place to check current verified test counts and engine strings.
- One place to check current combined-system phase status: the Phase 1 artifacts.
- Historical estimates and old phase boards stay available but cannot mislead.
- Phase 10 has a clear docs-freeze target.

**Costs / work deferred**

- Phase 10 must rewrite `README.md` and move status into `docs/STATUS.md`.
- Phase 10 must point all historical docs to the new status authority.
- CI must eventually check that generated eval docs and status references do not drift.

## Safety and honesty gates

- Phase 1 planning docs introduce no new test count, accuracy figure or deployment claim.
- Historical percentages are not promoted to current status.
- VoiceGuard roadmap status is not promoted into the 10-phase plan.
- No safety rail is relaxed.

## Verification

- Source-of-truth matrix names exactly one current status document.
- Phase 1 architecture freeze points runtime status back to `../../BUILD_STATE.md`.
- Headers in stale docs are synced by this Phase 1 change.
