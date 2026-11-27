# Document map

This is the canonical map. Start with the root [`summary.md`](../summary.md)
for the AI handoff, then the root README, status board or generated evaluations.
Everything not listed here as canonical is historical, a specification, a
decision record or provenance.

## Canonical entry points

| Document | Purpose |
|---|---|
| [`summary.md`](../summary.md) | Root AI handoff, reading order and future-integration playbook |
| [`README.md`](../README.md) | One repository entry point and quick-start commands |
| [`docs/STATUS.md`](STATUS.md) | Single frozen status board and VoiceGuard re-entry gate |
| [`CHANGELOG.md`](../CHANGELOG.md) | Current release notes; links to historical detail |
| [`EVALS.md`](../EVALS.md) | Generated, conditioned measurements for every capability |
| [`evals/claims_ledger.json`](../evals/claims_ledger.json) | Source row for every outward number |
| [`evals/claims_sources.json`](../evals/claims_sources.json) | Hand-authored documentation claim rows |
| [`evals/run_evals.py`](../evals/run_evals.py) | One eval runner and drift check |
| [`Makefile`](../Makefile) | One install, test, eval, run and CI command set |
| [`tools/launch_apps.py`](../tools/launch_apps.py) | One process launcher for the two apps |
| [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | CI gates |

## Architecture and decisions

| Document | Purpose |
|---|---|
| [`apps/citizen/`](../apps/citizen/) | Citizen app |
| [`apps/infra/`](../apps/infra/) | Infra app and read-only SOC console |
| [`packages/contracts/`](../packages/contracts/) | Shared contracts |
| [`packages/spine/`](../packages/spine/) | Unified runtime |
| [`packages/governance/`](../packages/governance/) | Planner, Governor and dry-run executor |
| [`packages/ledger/`](../packages/ledger/) | Append-only ledger |
| [`raksha/adr/README.md`](../raksha/adr/README.md) | ADR register |
| [Unified evals decision](../raksha/adr/ADR-015-unified-evals.md) | Unified evals and claims decision |
| [Packaging and release decision](../raksha/adr/ADR-016-release-packaging.md) | Packaging, CI and provenance decision |
| [`raksha/COMBINED_SYSTEM_ROADMAP.md`](../raksha/COMBINED_SYSTEM_ROADMAP.md) | Frozen phase board and historical roadmap |

## Historical and provenance

| Location | Status |
|---|---|
| [`archive/provenance/`](../archive/provenance/) | Retired standalone projects, historical uploads and integration notes |
| [`raksha/CHANGELOG.md`](../raksha/CHANGELOG.md) | Historical phase-by-phase changelog |
| [`raksha/PHASE910_UNIFIED_RELEASE.md`](../raksha/PHASE910_UNIFIED_RELEASE.md) | Final Phase Nine and Ten report |
| [`specs/`](../specs/) | Historical design specifications, not runtime authority |
| [`raksha/`](../raksha/) | Historical phase reports and ADRs unless linked above |

Generated documents — `EVALS.md`, `evals/results.json`, `evals/corpus.json`,
`evals/claims_ledger.json`, the MessageGuard compatibility pointer and the
legacy MessageGuard results copy — are never hand-edited. Regenerate them with
`make eval-generate` and verify drift with `make eval`. All numbers in this map
are file names or phase identifiers, not field measurements; real-world
accuracy, latency, uptime, recall and false-positive rate are UNMEASURED.
