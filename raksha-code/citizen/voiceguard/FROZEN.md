# FROZEN SEAM — VoiceGuard / MAYA

> **Status:** parked by Phase 1 of the combined-system plan · **Date:** 2026-11-26
> **Branch:** `arena/3b136fd9-bec-defence`
> **Authority:** [`../../../raksha/PHASE1_ARCHITECTURE_FREEZE.md`](../../../raksha/PHASE1_ARCHITECTURE_FREEZE.md),
> [`../../../raksha/adr/ADR-009-voiceguard-frozen-seam.md`](../../../raksha/adr/ADR-009-voiceguard-frozen-seam.md),
> and [`../../../raksha/COMBINED_SYSTEM_ROADMAP.md`](../../../raksha/COMBINED_SYSTEM_ROADMAP.md) §8.

---

## What this means

This directory remains inside the canonical runtime tree for provenance, but it
is **not integrated into the combined-system 10-phase plan**. VoiceGuard is still
being built and was explicitly left out by the maintainer.

Phase 1 added this Markdown marker only. It did **not**:

- edit any `.py`, `.js`, `.json`, config, fixture or test file;
- add or change a feature flag;
- disable the existing PWA "Check Voice" tab or `POST /api/citizen/screen_voice`;
- change the model card, model artefact, capture code, reasons, i18n or training code;
- introduce any new accuracy, real-speech or clone-detection claim.

## Frozen surface

The following remain parked as shipped / historical:

- this directory and its existing model, contract, capture, corpus, features,
  reasons, i18n and training modules;
- `MODEL_CARD.md` and `maya_lr_v1.json`;
- `../../../raksha-code/evals/run_maya.py`;
- `../../../raksha-code/citizen/app/maya-capture*.js` and existing Check Voice UI references;
- `../../../VOICEGUARD_ROADMAP.md`, `../../../MAYA_BUILD.md`, and
  `../../../specs/02_citizen_voiceguard.md`.

## Re-entry condition

VoiceGuard becomes a separate **Phase 11** only after the re-entry gate in the
combined-system roadmap is met: frozen verdict/reason/retention contract,
consent-gated capture proof, honest model card, en/hi/te copy, synthetic-vs-real
corpus separation, measured degradation curves, tests, disabled-by-default
feature flag, and an explicit maintainer decision to replace this seam.

Until then: **parked, not integrated; documented, not claimed.**
