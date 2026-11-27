# ADR-010 — Separate apps, shared packages, no single blended app

> **Status:** Accepted for Phase 2 code scaffold · **Date:** 2026-11-26
> **Decision owner:** repo maintainer (human) · **Recorded by:** AI-assisted maintainer session
> **Related:** [`../PHASE2_CODE_LAYOUT.md`](../PHASE2_CODE_LAYOUT.md), [`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) Phase 2

## Context

Phase 1 described two apps and one shared spine. The maintainer then clarified
that "combined" must not mean "one single app": Citizen and Infra/Sentinel must
stay visibly separate, and editing one must not require changing the other's
code. VoiceGuard / MAYA must be left untouched.

The repo had all runtime code under `raksha-code/` with flat package names
(`citizen`, `spine`, `sentinel`, `raavan`, `corpora`, `evals`). That shape made
the two apps hard to see and allowed app code to import shared runtime directly.

## Decision

Create `apps/citizen/` and `apps/infra/` as independent app roots, and
`packages/` as the only cross-app integration layer.

1. Move editable Citizen Python modules (`api.py`, `messageguard/`, `risk/`)
   into `apps/citizen/`.
2. Keep frozen VoiceGuard/MAYA code, PWA/Maya assets, and measurement fixtures
   under `raksha-code/citizen/`; expose them to the new app with symlinks and one
   `legacy_voiceguard.py` adapter.
3. Add `apps/infra/backend/`, `apps/infra/detectors/`, and `apps/infra/console/`
   as Infra-owned surfaces. Shared runtime is reached through `packages/`
   facades, not through Citizen code.
4. Add `packages/contracts/separation.py` as a machine-readable boundary
   contract and enforce it with AST-based pytest checks.
5. Keep `citizen.*`, `spine.*`, `sentinel.*`, `raavan.*`, `corpora.*` and
   `evals.*` import compatibility so existing tests/eval runners do not break.
6. Pin VoiceGuard/MAYA assets by SHA-256 and fail the suite if any are edited,
   moved, added, or removed.

## Consequences

**Positive**

- The separation is visible in the filesystem, not just in prose.
- Citizen and Infra can be edited independently.
- Apps integrate only through `packages/`.
- VoiceGuard/MAYA remains parked and untouched.
- Legacy commands keep working during the staged migration.

**Costs / work deferred**

- `raksha-code/` remains a compatibility/provenance layer until Phase 10.
- `packages/spine`, `packages/governance`, and `packages/ledger` are facades
  today; Phase 3 and 7 will move implementation behind them.
- `apps/infra/detectors` re-exports legacy organs until Phase 6.
- Root README consolidation remains Phase 10.

## Safety and honesty gates

- No direct app-to-app imports in new app/package code.
- No VoiceGuard/MAYA file content changes; hash manifest enforces this.
- No safety rail relaxed; dry-run and Governor/ledger semantics remain intact.
- No claim that Phase 2 is a full migration; compatibility seams are explicit.

## Verification

> Historical Phase 2 snapshot. Current Phase 4 deterministic counts are in
> [`../PHASE4_CITIZEN_CONSOLIDATION.md`](../PHASE4_CITIZEN_CONSOLIDATION.md) and
> [`../../BUILD_STATE.md`](../../docs/STATUS.md).

- `pytest -q` from repo root: **1259 passed**, 1 skipped, 1 xfailed.
- `pytest -q` from `raksha-code/`: **1257 passed**, 1 skipped, 1 xfailed.
- Node browser tests: **90 passed**, 0 fail.
- `python tools/check_frozen_assets.py`: **OK** — 28 assets unchanged.
- `python -m apps.citizen --help` and `python -m apps.infra.backend --help` work.
- Legacy `python -m citizen.api`, `evals/messageguard/run_evals.py --check`, and
  Node tests remain green.
