> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../../docs/STATUS.md); see the [retired code note](../../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# ADR-014 — Phase 6–8 unified Infra integration

**Status:** accepted, implemented 2026-11-26
**Supersedes:** Phase 2/3 statements that `apps/infra/backend/app.py` is a facade
over the legacy `spine.bus`. It does not supersede ADR-001…ADR-013.
**Related:** [ADR-001](ADR-001-single-bus.md),
[ADR-003](ADR-003-single-governor.md), [ADR-004](ADR-004-single-planner.md),
[ADR-005](ADR-005-single-organ-registry.md),
[retired-code note](../../archive/provenance/RETIRED.md),
[ADR-013](ADR-013-messageguard-single-source.md).

## Context

Phases 1–5 froze the architecture, created the two-app layout, unified shared
contracts, consolidated Citizen and made MessageGuard single-source. The active
Infra app still imported the legacy `spine.bus`, which could instantiate an
SLM/Commander path, and the detection organs, Governor/planner/executor, ledger
runtime, `/v1` API and SOC console were compatibility seams rather than one
operational path. The maintainer asked for Phases 6–8 to be integrated quickly,
with important deterministic tests and no AI models.

## Decision

1. **One detector contract.** `apps/infra/detectors/registry.py` owns eight organ
   records and `detect(event, *, key)`; the legacy eight shield classes remain
   lazy compatibility attributes. Validation and quarantine happen before any
   rule executes; missing features produce `no_detection`.
2. **One deterministic safety brain.** `packages/governance/safety.py` owns one
   exhaustive/blast-radius planner, one Governor, one dry-run executor and one
   Proposal type with crown/Tier-0 exclusion enforced in construction. The
   optional Commander is a disabled status card and is never invoked.
3. **One runtime and ledger write path.** `packages/spine/runtime.py` owns the
   only active ingest → detect → fuse → plan → decide → seal → broadcast path.
   `SafetyRuntime._seal` is the only caller of `RuntimeLedger.append`. Decisions,
   including refusals, are ledgered before API/WS broadcast.
4. **One app/API/WS/console surface.** `apps/infra/backend/app.py` delegates to
   the runtime and serves a read-only console. Canonical `/v1` routes and Phase 3
   compatibility aliases share one implementation; one WebSocket function serves
   `/v1/telemetry/stream` and `/ws/telemetry`.
5. **No AI, no real action.** No LLM/Commander/SLM/Ollama/MAYA/VoiceGuard model
   endpoint or inference is run. Frozen voice assets are untouched. The executor
   is dry-run and all seeded events are synthetic fixtures.

## Consequences

- The legacy `spine.bus` is no longer imported by the active app;
  `packages/spine/bus.py` is a compatibility facade that requires the one
  detector contract.
- Admin override remains impossible; decisions are append-only. Refusals are
  first-class ledger records visible in `/v1/decisions` and the console.
- Token scopes, dedupe, per-source rate limits and quarantine semantics are
  preserved in the unified runtime.
- The console can display a full campaign without `curl`, but cannot mutate
  safety state.
- Phase 9/10 remain out of scope. VoiceGuard/MAYA remain future Phase 11 work.
- Verification is deterministic/no-AI only; see
  [`../PHASE678_UNIFIED_INTEGRATION.md`](../PHASE678_UNIFIED_INTEGRATION.md),
  [`../../tools/check_phase678_integration.py`](../../tools/check_phase678_integration.py)
  and [`../../tests/test_phase678_integration.py`](../../tests/test_phase678_integration.py).
