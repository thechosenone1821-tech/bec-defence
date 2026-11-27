# INTEGRATED — retired standalone projects and historical uploads

This is the Phase 10 integration index. Every tree listed here is provenance,
not an active runtime, app, test suite, measurement source or deployment unit.
The canonical repository entry point is [`../../README.md`](../../README.md);
the root [`../../summary.md`](../../summary.md) is the AI handoff and
future-integration playbook; current status is
[`../../docs/STATUS.md`](../../docs/STATUS.md); current measurements are
generated in [`../../EVALS.md`](../../EVALS.md).

| Provenance tree | Retired source | Integrated into |
|---|---|---|
| `raksha-enterprise/` | standalone enterprise RAAVAN/eval/bus project | `apps/infra/`, `packages/spine/`, `evals/` |
| `raksha-governance/` | standalone governance project | `packages/governance/`, `packages/ledger/` |
| `messageguard-alternative/` | `raksha-messageguard/` | `apps/citizen/messageguard/`, `evals/messageguard.py` |
| `messageguard-snapshot/` | `random project that ew need to integrate/` | canonical corpus and provenance only |
| `eigenshield-root-readme/` | historical root `README.md` | new root `README.md` |
| `legacy-build-state/` | historical root `BUILD_STATE.md` | `docs/STATUS.md` |
| `raksha-evals-historical/` | historical `raksha/EVALS.md` | generated root `EVALS.md` |
| `legacy-evals-runner/` | `raksha-code/evals/run_evals.py` | `evals/run_evals.py` |
| `legacy-evals/` | legacy `raksha-code/evals/` implementation | root `evals/` package and thin compatibility wrappers |
| `legacy-corpora/` | legacy `raksha-code/corpora/` | `evals/corpus.py` and thin compatibility shim |
| `legacy-raavan/` | legacy `raksha-code/raavan/` | `evals/replay.py` and thin compatibility shim |
| `raksha-messageguard-evals/` | historical generated MessageGuard report | generated `EVALS.md` and compatibility pointer |
| `historical-build-logs/` | root Citizen/Infra build logs | canonical docs and phase reports |
| `historical-design-docs/` | early architecture, build guide, roadmap | frozen `raksha/COMBINED_SYSTEM_ROADMAP.md` and ADRs |

## Rules

- No AI model, Commander/SLM/Ollama endpoint, frozen VoiceGuard/MAYA inference,
  live executor, real containment action or network service was added.
- `raksha-code/evals/run_maya.py` remains at its original path because it is a
  hash-pinned frozen asset; it is not part of the unified runner.
- Thin compatibility shims under `raksha-code/` contain no duplicate runtime
  implementation; they only point historical imports at provenance or the root
  `evals/` package.
- Every measured number is conditioned and sourced in
  [`../../evals/claims_ledger.json`](../../evals/claims_ledger.json). Phase
  numbers and historical counts in this index are identifiers, not measurements;
  real-world accuracy, latency, uptime, recall and FPR are UNMEASURED.
- The ten-phase board is frozen. VoiceGuard / MAYA integration is a separate
  future Phase Eleven with the re-entry gate in `docs/STATUS.md`.

Each provenance tree carries its own `INTEGRATED.md` note.

See the [retired code note](RETIRED.md) for the executable-code purge boundary.
