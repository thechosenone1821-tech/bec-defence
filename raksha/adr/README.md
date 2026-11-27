# RAKSHA — ADR Register

ADR numbers, dates and phase labels in this register are identifiers, not
performance measurements. Current measured numbers are generated in
[`../../EVALS.md`](../../EVALS.md) and conditioned in
[`../../evals/claims_ledger.json`](../../evals/claims_ledger.json); real-world
accuracy, latency, uptime, recall and FPR are UNMEASURED. For the full AI
handoff and future-integration playbook, see [`../../summary.md`](../../summary.md).

> **Status:** Phase 1 planning freeze + Phase 2 separation + Phase 3 contracts + Phase 4 Citizen consolidation + Phase 5 MessageGuard single-source · **Date:** 2026-11-26 · **Branch:** `arena/3b136fd9-bec-defence`
>
> ADR-001…ADR-009 froze **one canonical home per duplicated capability** before
> Phase 2. ADR-010 records the maintainer's Phase 2 code requirement: separate
> apps, shared packages, and VoiceGuard/MAYA left untouched. ADR-011 records the
> Phase 3 decision: one shared contract layer, one ledger interface, and no
> signature/Governor bypass. ADR-012 records the Phase 4 decision: one Citizen
> service, app-owned copy, shared rendering logic, and a hard-disabled
> VoiceGuard seam with **no AI models run**. ADR-013 records the Phase 5
> decision: one MessageGuard scorer/interface, corpus, reason catalogue and
> generated eval document. Implementation details are in
> [`../PHASE2_CODE_LAYOUT.md`](../PHASE2_CODE_LAYOUT.md),
> [`../PHASE3_CONTRACT_SPINE.md`](../PHASE3_CONTRACT_SPINE.md),
> [`../PHASE4_CITIZEN_CONSOLIDATION.md`](../PHASE4_CITIZEN_CONSOLIDATION.md)
> and [`../PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md`](../PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md)
and [`../PHASE678_UNIFIED_INTEGRATION.md`](../PHASE678_UNIFIED_INTEGRATION.md).
>
> **Status vocabulary:** `Frozen for Phase 1 planning` = architecture fixed on
> paper; `Accepted for Phase 2 code scaffold` = separation layout implemented with
> compatibility seams; `Accepted for Phase 3 code scaffold` = shared contracts
> and compatibility delegation implemented with boundary tests;
> `Accepted for Phase 4 code scaffold` = Citizen consolidation implemented with
> app-owned copy and a disabled, model-free VoiceGuard seam;
> `Accepted for Phase 5 code scaffold` = MessageGuard single-source implemented
> with archived provenance and no AI models run.

---

## Register

| ADR | Capability | Frozen decision | Implementation phase |
| --- | --- | --- | --- |
| [ADR-001](ADR-001-single-bus.md) | Telemetry bus / API / WS | One logical bus core; app APIs are thin adapters; enterprise bus is port source | 3 + 8 |
| [ADR-002](ADR-002-single-ledger.md) | Evidence ledger | One `append / verify` interface; no direct app writes | 3 + 7 |
| [ADR-003](ADR-003-single-governor.md) | Governor / safety core | One final veto, one allowlist, no bypass | 7 |
| [ADR-004](ADR-004-single-planner.md) | Containment planner | One planner/topology/objective; dry-run only | 7 |
| [ADR-005](ADR-005-single-organ-registry.md) | Infra detection organs | One 8-organ registry and one detect contract | 6 |
| [ADR-006](ADR-006-single-messageguard.md) | Citizen MessageGuard | Already-integrated v1 is canonical; alternatives are port/provenance sources | 5 |
| [ADR-007](ADR-007-single-eval-runner.md) | Eval runner / claims ledger | One reproducible runner, one claims ledger; generated docs never hand-edited | 9 |
| [ADR-008](ADR-008-single-status-document.md) | Status document | `../../BUILD_STATE.md` remains current authority; future `docs/STATUS.md` | 10 |
| [ADR-009](ADR-009-voiceguard-frozen-seam.md) | VoiceGuard seam | Parked; not a Phase 1–10 deliverable; future Phase 11 only | 11 |
| [ADR-010](ADR-010-separation-boundaries.md) | App boundaries | Separate apps, shared packages, no single blended app; VoiceGuard/MAYA untouched | 2 |
| [ADR-011](ADR-011-unified-contracts.md) | Shared contracts / spine | One canonical rule, envelope, table, ledger interface and no-bypass gate | 3 |
| [ADR-012](ADR-012-citizen-consolidation.md) | Citizen consolidation | One service/shell, app copy + shared renderer, VoiceGuard disabled, no AI models | 4 |
| [ADR-013](ADR-013-messageguard-single-source.md) | MessageGuard single-source | One scorer/interface, corpus, `MSG-*` catalogue and generated eval; alternatives archived | 5 |
| [ADR-014](ADR-014-phase6-8-unified-integration.md) | Phase 6–8 unified Infra | One detector registry, deterministic safety brain, runtime/ledger path, API/WS/read-only console | 6–8 |
| [ADR-015](ADR-015-unified-evals.md) | Unified evals and claims | One corpus, replay, runner, generated EVALS.md, claims ledger and drift check; VoiceGuard excluded | 9 |
| [ADR-016](ADR-016-release-packaging.md) | Packaging and release | One install/test/eval/run surface, CI gates, canonical docs, provenance archive and frozen board | 10 |

ADR-001…ADR-008 correspond exactly to the duplicate capabilities named in
[`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) Phase 1.
ADR-009 records the explicit parked-seam decision requested by the maintainer.
ADR-010 records the Phase 2 "separate but integrated" correction. ADR-011 records
Phase 3's unified-contract implementation. ADR-012 records Phase 4's Citizen
consolidation. ADR-013 records Phase 5's MessageGuard single-source implementation.
ADR-014 records the Phase 6–8 actual integration of detectors, deterministic
Governance, one runtime/ledger path and the read-only Infra console. ADR-015
records Phase 9's single measurement story. ADR-016 records Phase 10's packaging,
CI, canonical docs, provenance archive and frozen ten-phase board.

---

## Common decision constraints

1. **Decision owner:** repo maintainer (human).
2. **Recorded by:** AI-assisted maintainer session, 2026-11-26.
3. **Phase 2/3/4/5 authorization:** later maintainer requests authorized a code
   scaffold, Phase 3 contracts, Phase 4 Citizen consolidation, Phase 5
   MessageGuard single-source and Phase 6–8 unified Infra integration with no AI
   models run; no big-bang merge and no VoiceGuard/MAYA edits were performed.
4. **No safety rail relaxed:** Governor, ledger, signature checks, canary semantics,
   dry-run defaults and append-only decisions remain binding.
5. **No invented facts:** current verified numbers stay in
   [`../../EVALS.md`](../../EVALS.md) and
   [`../../evals/claims_ledger.json`](../../evals/claims_ledger.json); historical
   planning docs introduce no new measurements.
6. **One doctrine:** Citizen and Infra/Sentinel share one spine. Any future ADR
   that splits the spine must supersede this register explicitly.

See also [`../PHASE1_ARCHITECTURE_FREEZE.md`](../PHASE1_ARCHITECTURE_FREEZE.md),
[`../PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](../PHASE1_SOURCE_OF_TRUTH_MATRIX.md),
[`../PHASE3_CONTRACT_SPINE.md`](../PHASE3_CONTRACT_SPINE.md),
[`../PHASE4_CITIZEN_CONSOLIDATION.md`](../PHASE4_CITIZEN_CONSOLIDATION.md) and
[`../PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md`](../PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md)
and [`../PHASE678_UNIFIED_INTEGRATION.md`](../PHASE678_UNIFIED_INTEGRATION.md).
