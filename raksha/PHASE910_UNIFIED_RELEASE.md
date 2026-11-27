# Phases Nine and Ten — unified release

> Final report for the combined-system closeout. The ten-phase board is frozen.
> This report is historical closeout evidence; the live entry point is
> [`../README.md`](../README.md) and the single status board is
> [`../docs/STATUS.md`](../docs/STATUS.md).

## Phase Nine — one measurement story

- One deterministic corpus generator at [`../evals/corpus.py`](../evals/corpus.py)
  owns MessageGuard fixture references, Citizen cases, organ fixture bundles,
  governance topology and the sandbox replay steps.
- One replay player at [`../evals/replay.py`](../evals/replay.py) POSTs the
  committed sandbox corpus through the active Infra API, then reads state,
  ledger verification, decisions, quarantine and metrics.
- One eval runner at [`../evals/run_evals.py`](../evals/run_evals.py) computes
  Citizen, MessageGuard, organs, governance and end-to-end replay sections.
- One generated [`../EVALS.md`](../EVALS.md) has a section per capability. It is
  produced from [`../evals/results.json`](../evals/results.json) and is never
  hand-edited.
- One claims ledger at
  [`../evals/claims_ledger.json`](../evals/claims_ledger.json) gives every
  measured number a conditioned source row. Hand-authored documentation rows
  live in [`../evals/claims_sources.json`](../evals/claims_sources.json).
- One drift check is `make eval`: it regenerates nothing when invoked with
  `--check`, compares corpus, results, generated documents and ledger, and
  verifies the capability gates.

`run_evals --check` is green for Citizen, MessageGuard, organs, governance and
end-to-end replay. Every number carries fixture / synthetic / sandbox /
hand-authored / real-world UNMEASURED conditions. No number in a README, status
page, changelog or pitch lacks a claims-ledger source row. No real-world
accuracy, latency, uptime, recall or false-positive claim is made from sandbox
fixtures. VoiceGuard evals stay out of this runner.

## Phase Ten — one maintainable repository

- One install command, one test command, one eval command and one process
  launcher are defined in [`../Makefile`](../Makefile) and
  [`../tools/launch_apps.py`](../tools/launch_apps.py).
- CI gates in [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml) cover
  Python suites, browser suites, eval drift, ledger verify, boot manifests, no
  secrets and no live-executor imports.
- [`../README.md`](../README.md), [`../docs/STATUS.md`](../docs/STATUS.md),
  [`../CHANGELOG.md`](../CHANGELOG.md) and
  [`../docs/README.md`](../docs/README.md) describe the two-app system, not
  historical uploads.
- The root [`../summary.md`](../summary.md) is the AI handoff and
  future-integration playbook; it is covered by the claims ledger and the
  unified integration checker.
- Retired standalone projects, historical root documents and legacy standalone
  eval/corpus/replay sources are indexed under
  [`../archive/provenance/INTEGRATED.md`](../archive/provenance/INTEGRATED.md)
  with integration notes. Active runtime has no duplicate implementation outside
  provenance.
- The ten-phase board is frozen. A separate future Phase Eleven: VoiceGuard
  integration opens only when the written re-entry gate in the status board is
  satisfied.

## Safety and non-goals

No AI model, Commander, SLM, Ollama endpoint, frozen VoiceGuard/MAYA inference,
live executor, real containment, session revocation, host action, clone
detection claim, real-speech accuracy claim, real-network detection claim or
field false-positive claim was introduced. Dry-run remains the only executor
mode. The Commander card stays disabled and the append-only ledger remains
verified. VoiceGuard / MAYA assets remain frozen and unchanged.

## Validation snapshot

All deterministic no-AI gates are green: root no-AI pytest 212 passed;
legacy-cwd no-AI pytest 171 passed; browser tests 60 passed; local Markdown
links 628/628; frozen VoiceGuard/MAYA assets 28 unchanged; shared config pins 5;
two boot manifests; 22 skipped model-dependent Python test files and 2 provenance
test dirs ignored; unified eval 5 capability sections, 14 sandbox replay steps
and 538 hand-authored MessageGuard fixtures. `make ci`, `make test` and
`make eval` all exit zero. Unified eval drift, claims-ledger verification,
runtime-ledger verify, boot-manifest checks, no-secrets and no-live-executor
checks, compile and diff checks are green. A two-app live preview was started
and stopped: Infra console, health and state plus Citizen PWA, health and
manifest returned healthy no-AI, dry-run responses. Every count here is a fixture /
sandbox repository check, not a field measurement; real-world accuracy,
latency, uptime, recall and false-positive rate remain UNMEASURED. The generated
evaluation document and claims ledger are the only sources for measured figures.
No commit or push was performed as part of this closeout.
