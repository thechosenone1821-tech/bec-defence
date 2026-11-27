> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../../docs/STATUS.md); see the [retired code note](../../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# ADR-011 — One shared contract layer, no signature or Governor bypass

> **Status:** Accepted for Phase 3 code scaffold; Phase 4 later added shared i18n/Citizen copy · **Date:** 2026-11-26
> **Decision owner:** repo maintainer (human) · **Recorded by:** AI-assisted maintainer session
> **Related:** [`../PHASE3_CONTRACT_SPINE.md`](../PHASE3_CONTRACT_SPINE.md), [`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) Phase 3

## Context

Phase 2 created two separate app roots and a shared `packages/` layer, but
Citizen, Infra, RAAVAN, eval harnesses, enterprise I1 code, governance code and
the shipped spine still owned overlapping canonical JSON, envelope, ledger,
sanitizer and config definitions. Phase 3's roadmap goal is to make both apps
speak one language before feature consolidation.

The maintainer's standing correction is that "combined" must not mean one
blended app, and VoiceGuard / MAYA must be left alone.

## Decision

Create `packages/contracts/` as the single source for:

1. canonical JSON (`canonical.py`);
2. signed-envelope validation (`envelope.py`) with three compatibility profiles;
3. verdict/legacy bands (`bands.py`) and the `MSG-*` reason catalogue
   (`reasons.py`);
4. sanitizer/entity rules (`entities.py`);
5. config pins and auth scopes (`config.py`);
6. backend route mapping (`backend.py`);
7. a reserved VoiceGuard slot (`voiceguard.py`) with no logic import;
8. a signature + Governor action gate (`guard.py`).

Create `packages/ledger/interface.py` and `packages/ledger/cli.py` as one
`append / verify` interface and one CLI. Make shipped compatibility modules
delegate to the shared canonical/config contracts rather than duplicating them.
Expose the event/backend contract from both app health/contract endpoints.

Forbid app-level imports of legacy bus, Governor, ledger, sanitizer, graph,
planner and private RPC bypass roots. Enforce this with AST checks.

## Consequences

**Positive**

- One envelope validates identically for Citizen, Infra, RAAVAN and eval events.
- One CLI verifies one append-only chain from both new and legacy entrypoints.
- Signature verification and the Governor are explicit gates on the new action
  path.
- Config, auth scopes, sanitizer rules and entity tokens have one owner.
- VoiceGuard/MAYA remain parked and hash-pinned.
- Legacy imports/tests keep working through facades and compatibility aliases.

**Costs / work deferred**

- `raksha-code/` remains the compatibility/provenance layer.
- Full Governor/TCB/FIDO2 implementation merge remains Phase 7.
- Full organ registry move remains Phase 6.
- Unified eval/corpora/archive/packaging remain Phases 9–10.
- Root README consolidation remains Phase 10.

## Safety and honesty gates

- No raw score, SAFE verdict, PII forwarding, real containment, or real-world
  accuracy claim was introduced.
- Dry-run defaults, Governor veto, ledger append-only semantics and signature
  verification remain binding.
- No VoiceGuard/MAYA asset content changed; the 28-asset hash checker remains
  green.
- No commit or push was requested.

## Verification

- `python tools/check_phase3_contracts.py` — **OK**.
- `python -m packages.contracts` — **OK, 5 config pins unchanged**.
- `python tools/check_frozen_assets.py` — **OK, 28 assets unchanged**.
- `python -m packages.ledger.cli verify` and `python -m spine.ledger_cli verify`
  produce the same report against one populated chain.
- Phase 3 snapshot full pytest: **1271 passed** root / **1263 passed** legacy
  cwd; Node **90 passed**; MessageGuard eval `--check`, `compileall`,
  `git diff --check`, local links, import smoke and entrypoint help clean.
  Historical total **1361 passing checks**.
- These are Phase 3 snapshot results. Phase 4's deterministic counts and
  no-AI-model skip policy are in
  [`../PHASE4_CITIZEN_CONSOLIDATION.md`](../PHASE4_CITIZEN_CONSOLIDATION.md)
  and [`../../BUILD_STATE.md`](../../docs/STATUS.md).
