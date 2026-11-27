# ADR-016 — one maintainable repository and frozen release board

**Status:** Accepted / implemented in Phase 10
**Date:** 2026-11-26
**Scope:** packaging, CI, canonical docs, provenance archive and release handoff

## Decision

The repository has one entry point, one status board and one command surface:

- `README.md` is the single root entry point.
- `docs/STATUS.md` is the single frozen status board.
- `docs/README.md` is the document map.
- `CHANGELOG.md` is the current release changelog; `raksha/CHANGELOG.md` keeps
  historical detail.
- `Makefile` defines `make install`, `make test`, `make eval`, `make run` and
  `make ci`.
- `tools/launch_apps.py` is the one process launcher for exactly two apps.
- `.github/workflows/ci.yml` gates Python suites, browser suites, eval drift,
  ledger verify, boot manifests, no secrets and no live-executor imports.
- `apps/citizen/` and `apps/infra/` are the only app roots; boot manifests make
  that mechanically checkable.

Retired standalone projects, historical root documents and legacy standalone
eval/corpus/replay sources are moved or indexed under `archive/provenance/`
with `INTEGRATED.md` notes. No duplicate runtime implementation remains outside
provenance. The ten-phase board is frozen.

## Consequences

- A new engineer can clone, install, test, run both apps and find status without
  reading historical build logs.
- CI refuses secrets, live-executor imports, duplicate apps, stale generated
  eval documents, broken claims rows, stale boot manifests and broken ledger
  chains.
- VoiceGuard / MAYA stays a frozen seam. A separate future Phase 11 opens only
  through the written re-entry gate in `docs/STATUS.md`.
- No real-world offensive or containment action, session revocation, host action,
  clone detection claim, real-speech accuracy claim, real-network detection claim
  or field false-positive claim is introduced. Dry-run remains the only executor
  mode.

## Validation

`make test`, `make eval`, `make ci-checks` and `make ci` are the command gates.
`tools/check_phase910_integration.py` proves one canonical doc set, one eval
runner, one claims ledger, one launcher, the CI gates, the provenance notes, the
frozen board and the VoiceGuard re-entry gate. Live preview verifies the Infra
root redirect, console and state surface plus the Citizen PWA.

See [`../PHASE910_UNIFIED_RELEASE.md`](../PHASE910_UNIFIED_RELEASE.md) and
[`../../docs/STATUS.md`](../../docs/STATUS.md).
