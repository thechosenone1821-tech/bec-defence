# ADR-009 — VoiceGuard is a frozen seam

> **Status:** Frozen for Phase 1 planning · **Date:** 2026-11-26
> **Decision owner:** repo maintainer (human) · **Recorded by:** AI-assisted maintainer session
> **Related:** [`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) §8, [`../PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](../PHASE1_SOURCE_OF_TRUTH_MATRIX.md) §4

## Context

The maintainer explicitly asked to leave VoiceGuard out of the combined-system
10-phase roadmap because it is still being built. The repo nevertheless contains
a substantial VoiceGuard/MAYA surface:

- `../../raksha-code/citizen/voiceguard/` — model, contract, capture, corpus, features, reasons, i18n and training code.
- `../../raksha-code/evals/run_maya.py` and VoiceGuard model-card/corpus artefacts.
- `../../raksha-code/citizen/app/maya-capture*.js` and the existing "Check Voice" PWA tab / `POST /api/citizen/screen_voice` seam.
- `../../VOICEGUARD_ROADMAP.md`, `../../MAYA_BUILD.md`, `../../specs/02_citizen_voiceguard.md`.
- `../../archive/provenance/raksha-enterprise/raksha-enterprise/raksha/organs/voiceguard.py` — an enterprise-side organ with the same word in its name.

Without an explicit freeze, later phases could accidentally treat these as
integration deliverables or evidence of completion.

## Decision

VoiceGuard is a **frozen seam**, not a Phase 1–10 deliverable.

- **No integration:** do not migrate, merge, or expand VoiceGuard as part of Phases 1–10.
- **No phase exit criterion:** no combined-system phase may depend on VoiceGuard accuracy, capture, model artefacts, or UI.
- **No accuracy claim:** synthetic-corpus and model-card statements remain historical; real-speech / clone-detection claims remain blocked.
- **No code change in Phase 1:** no feature flag is added, no Python/JS/config file is edited, and no existing tab or endpoint is disabled by this ADR.
- **In-tree marker:** [`../../raksha-code/citizen/voiceguard/FROZEN.md`](../../raksha-code/citizen/voiceguard/FROZEN.md) records the parked state next to the code.
- **Historical docs:** `VOICEGUARD_ROADMAP.md` and `MAYA_BUILD.md` are marked parked; `specs/02_citizen_voiceguard.md` is historical.
- **Enterprise organ:** `archive/provenance/raksha-enterprise/.../organs/voiceguard.py` is an Infra organ name only; it is not authority to integrate Citizen VoiceGuard.

VoiceGuard becomes a separate **Phase 11** only when the re-entry gate in the
combined-system roadmap §8 is satisfied and the maintainer explicitly replaces
this frozen seam.

## Consequences

**Positive**

- The 10-phase plan stays exactly as requested: two apps, no voice integration.
- Existing synthetic-only honesty labels remain intact.
- A future integration has a written contract seam and a clear gate.
- No duplicate VoiceGuard roadmap can masquerade as a combined-system phase.

**Costs / work deferred**

- The combined Citizen app will ship with the existing voice seam parked, not integrated.
- Phase 9 excludes VoiceGuard evals from the combined claims ledger.
- Phase 11 must reconcile contracts, consent, retention, model card, corpora, i18n, tests and feature flags before any integration.

## Safety and honesty gates

- No clone-detection claim.
- No real-speech accuracy claim.
- No consent-gated capture work is started here.
- No safety rail is relaxed and no code is changed.
- VoiceGuard appears in Phase 1 only as a parked seam or historical context.

## Verification

- Source-of-truth matrix §4 lists the frozen artifacts.
- `../../raksha-code/citizen/voiceguard/FROZEN.md` exists.
- `../../VOICEGUARD_ROADMAP.md` and `../../MAYA_BUILD.md` headers point to this decision.
- Phase 1 exit gate "VoiceGuard appears only as a parked seam" is satisfied.
