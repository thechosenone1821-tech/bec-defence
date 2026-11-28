> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../../docs/STATUS.md); see the [retired code note](../../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# ADR-012 — One Citizen service, app-owned copy, frozen VoiceGuard seam

> **Status:** Accepted for Phase 4 code scaffold · **Date:** 2026-11-26
> **Decision owner:** repo maintainer (human) · **Recorded by:** AI-assisted maintainer session
> **Related:** [`../PHASE4_CITIZEN_CONSOLIDATION.md`](../PHASE4_CITIZEN_CONSOLIDATION.md),
> [`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) Phase 4

## Context

Phase 3 unified shared event/backend contracts but Citizen still used frozen
VoiceGuard i18n for active message, risk and report copy, and the voice endpoint
could reach the MAYA classifier. The maintainer then asked to proceed to the
next phase **without running any AI models**.

Phase 4's roadmap goal is one phone-first app with all non-voice citizen
features, i18n/reason rendering in shared contracts, citizen-facing sentences in
the app, VoiceGuard behind a disabled feature flag, and an honest voice tab.

## Decision

1. Keep exactly one Citizen service (`apps/citizen/api.py`) and one physical PWA
   shell. Compatibility aliases are symlinks, not duplicate services.
2. Put rendering logic in `packages/contracts/i18n.py` and all citizen sentences
   in `apps/citizen/copy.py`. Shared contracts must not import app or model code.
3. Make `apps/citizen/risk/{engine,fusion}.py`, `apps/citizen/api.py`, and the
   Citizen report/message paths use the app copy module; leave frozen
   `citizen.voiceguard.i18n` unchanged for historical tests.
4. Hard-disable VoiceGuard/MAYA and the Commander/SLM in
   `apps/citizen/features.py`. Provide a documented `DisabledVoiceGuard`
   interface with no model import. Keep the single read-only legacy adapter for
   future Phase 11 only.
5. Replace active frozen-package imports with a model-free retention/consent
   gate. `/api/citizen/screen_voice` returns an honest `NOT_INTEGRATED` response
   and never processes, stores, echoes or scores samples.
6. Inject a runtime-only voice-status overlay into the single frozen shell and
   serve an honest manifest. Do not edit frozen PWA/VoiceGuard/MAYA files.
7. Enforce the boundary with `tools/check_phase4_citizen.py`, root acceptance
   tests, legacy-cwd compatibility tests, and a clean-process import probe that
   fails if any frozen VoiceGuard or SLM module is loaded.

## Consequences

**Positive**

- MessageGuard, risk fusion, reporting and multilingual copy work through one
  service and one app-owned copy catalogue.
- The shared i18n contract owns logic; the app owns sentences; neither imports
  the other app or a model.
- Voice tab says "not integrated yet"; no clone-detection claim or AI-model
  claim is added by Phase 4.
- No AI model inference, LLM/Commander call, MAYA classifier call, or
  model-dependent test file was run during validation.
- VoiceGuard/MAYA assets remain hash-pinned and untouched.

**Costs / work deferred**

- Alternative MessageGuard tree port/corpus unification remains Phase 5.
- Full runtime organ/Governor/eval/archive/packaging moves remain Phases 6–10.
- VoiceGuard/MAYA integration remains future Phase 11.
- `raksha-code/` remains the compatibility/provenance layer.

## Safety and honesty gates

- No raw score, SAFE verdict, PII forwarding, real containment, or real-world
  accuracy claim was introduced.
- Report events remain signed; Governor and signature requirements remain
  binding through the Phase 3 shared contract.
- Dry-run defaults and append-only ledger semantics are unchanged.
- Frozen assets remain verified by 28 SHA-256 pins.
- No commit or push was requested.

## Verification

`tools/check_phase4_citizen.py`, `tools/check_phase3_contracts.py`, frozen
asset checks, `python -m packages.contracts`, deterministic no-AI pytest, Node
tests, MessageGuard eval `--check`, compileall, `git diff --check`, local links,
import smoke and five model-free entrypoint helps are recorded in
[`../PHASE4_CITIZEN_CONSOLIDATION.md`](../PHASE4_CITIZEN_CONSOLIDATION.md) and
[`../../BUILD_STATE.md`](../../docs/STATUS.md).

Phase 5 revalidation produced the current deterministic counts: **186** root
Python checks, **171** legacy-cwd Python checks, **60** Node checks, **246**
total passing checks, **279/279** local links, 5 config pins, 28 frozen assets;
see [ADR-013](ADR-013-messageguard-single-source.md). `tools/run_phase4_pytest.py`
skips 23 model-dependent Python test files, `tools/run_phase4_node_tests.py`
skips one MAYA capture Node test file, and `tools/phase4_no_ai_plugin.py`
asserts that no forbidden model module loads. No AI model was invoked.

> **Historical Phase 4/5 counts:** the numbers above are preserved as-of that
> phase. Current verified counts and the Phase 6–8 implementation are in
> [`ADR-014`](ADR-014-phase6-8-unified-integration.md) and [`../../BUILD_STATE.md`](../../docs/STATUS.md).
