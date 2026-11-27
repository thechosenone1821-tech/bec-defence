# Status — frozen combined-system board

> This is the single status document. It supersedes historical build logs and
> upload snapshots. The ten-phase board is frozen; no further phase is open in
> this repository.

## Current release

- One repository, exactly two apps: Citizen and Infra.
- One shared contract spine, one MessageGuard scorer, one detector registry, one
  planner, one Governor, one dry-run executor, one organ registry and one ledger
  write path.
- One Python suite, one browser suite, one eval runner, one claims ledger and
  one drift check.
- One install command, one test command, one eval command and one process
  launcher.
- Deterministic and no-AI: Commander is disabled, no model endpoint is loaded,
  and dry-run remains the only executor mode.
- VoiceGuard / MAYA remains frozen and is not integrated.

## Frozen phase board

| Phase | State | Meaning |
|---|---|---|
| One through Five | FROZEN | Source-of-truth freeze, layout, shared contracts, Citizen consolidation and MessageGuard single source |
| Six through Eight | FROZEN | One Infra runtime, unified detectors, governance, ledger, API, WebSocket and read-only console |
| Nine | FROZEN | One corpus generator, replay player, eval runner, generated EVALS.md, claims ledger and drift check |
| Ten | FROZEN | One install/test/eval command, process launcher, CI gates, canonical docs, provenance archive and release board |
| Eleven | NOT OPEN | VoiceGuard integration; re-entry gate below |

## Definition of done

- A new engineer can clone, install, test, run both apps and find status without
  reading historical logs.
- No duplicate runtime implementation outside `archive/provenance/`.
- Every measured number is conditioned and has a claims-ledger source row.
- No real-world offensive or containment action is performed.
- No real-world accuracy, latency, uptime, recall or false-positive claim is made
  from sandbox fixtures.
- No third app, live model Commander, session revocation, host action or clone
  detection claim is introduced.

## VoiceGuard re-entry gate — future Phase Eleven only

A separate VoiceGuard integration phase may open only when all of the following
are true:

- The voice build is ready and its frozen assets are still unchanged.
- Consent, retention and on-device deletion policies are written and tested.
- Signed-envelope validation, reason codes and i18n coverage are wired through
  the shared contracts without importing a model into the Commander path.
- Measurements are labelled synthetic-only; real-speech accuracy, real-network
  detection and field false-positive rate remain UNMEASURED until properly
  measured under their own conditions.
- Deterministic no-AI tests, the unified eval runner, the claims ledger, the
  Governor and the append-only ledger all remain green.
- A new ADR records the integration and a new re-entry gate supersedes this one.

Until then: VoiceGuard evals stay out of `make eval`, the frozen VoiceGuard/MAYA
assets are not edited, and no voice result is used as evidence of completion.

## Where to look

- Root entry point: [`README.md`](../README.md).
- AI handoff and future-integration playbook: [`summary.md`](../summary.md).
- Document map: [`README.md`](README.md).
- Measurements: [`EVALS.md`](../EVALS.md).
- Claims ledger: [`evals/claims_ledger.json`](../evals/claims_ledger.json).
- Release history: [`CHANGELOG.md`](../CHANGELOG.md).
- Phase Nine and Ten report:
  [`raksha/PHASE910_UNIFIED_RELEASE.md`](../raksha/PHASE910_UNIFIED_RELEASE.md).
- Provenance index: [`archive/provenance/INTEGRATED.md`](../archive/provenance/INTEGRATED.md).
