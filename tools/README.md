# Tools

Deterministic safety, boundary, eval and release gates live here. The canonical
command surface is the root [`Makefile`](../Makefile): `make install`,
`make test`, `make eval`, `make run` and `make ci`. For the full AI handoff and
future-integration playbook, see [`../summary.md`](../summary.md). Numbers in
this guide are phase identifiers, skipped historical test-file counts and
frozen-asset counts, not field measurements; real-world accuracy, latency,
uptime, recall and FPR are UNMEASURED. Current measured numbers are in
[`../EVALS.md`](../EVALS.md).

```bash
make test                                      # Python + browser suites + all deterministic checkers
make eval                                      # one eval drift and claims-ledger gate
make run                                       # one launcher for the two apps
python tools/check_frozen_assets.py            # frozen VoiceGuard/MAYA assets unchanged
python tools/check_phase3_contracts.py         # shared contracts consistent
python tools/check_phase4_citizen.py           # Citizen consolidation; no AI model
python tools/check_phase5_messageguard.py     # one MessageGuard scorer/corpus/eval
python tools/check_phase678_integration.py     # Phase 6-8 unified Infra gate
python tools/check_phase910_integration.py     # Phase 9-10 unified release gate
python tools/check_eval_drift.py               # one eval drift check
python tools/check_claims_ledger.py            # claims ledger and outward-number sources
python tools/verify_runtime_ledger.py          # runtime ledger + shared ledger CLI verify
python tools/check_boot_manifest.py            # exactly two bootable apps
python tools/check_no_secrets.py               # no committed secrets
python tools/check_no_live_executor.py         # no live executor / model / legacy bus imports
python tools/check_local_links.py              # local Markdown links resolve
python tools/run_phase4_pytest.py              # deterministic no-AI pytest subset
python tools/run_phase4_pytest.py --print-skips
python tools/run_phase4_node_tests.py          # deterministic browser/Node suite
python -m packages.contracts                   # shared config pins
python -m evals.run_evals --check              # canonical Phase 9 runner gate
python -m evals.corpus --check                 # one corpus generator drift
python -m evals.replay --check                 # one replay player drift
```

## No-AI policy

`run_phase4_pytest.py` skips 22 model-dependent Python test files, ignores the
two archived MessageGuard provenance test directories and registers
`phase4_no_ai_plugin.py`, which fails pytest if a VoiceGuard/MAYA/SLM/Commander
module loads. `run_phase4_node_tests.py` skips the frozen MAYA capture JS test.
`check_frozen_assets.py` reads [`frozen_assets.sha256`](frozen_assets.sha256)
and proves the frozen assets were not edited or moved. The active Phase 3 root
contract test now uses the canonical shared signer, so it is included in the
no-AI subset.

## Phase 6–8 integration gate

`check_phase678_integration.py` verifies one detector registry, quarantine
before detection, one safety/ledger path, sealed-before-broadcast decisions,
unified routes/WS, scoped auth, read-only console, prior phase checkers and a
clean no-AI import probe.

## Phase 9–10 unified release gates

`evals/run_evals.py` is the one measurement runner. `evals/corpus.py` is the one
corpus generator, `evals/replay.py` is the one replay player, `EVALS.md` is the
one generated evaluation document, `evals/claims_ledger.json` is the one claims
ledger, and `check_eval_drift.py` is the one drift gate. Generated eval documents
are never hand-edited; `make eval-generate` regenerates them.

`check_phase910_integration.py` proves the canonical docs, two boot-manifested
apps, CI gates, no secrets, no live-executor imports, ledger verification,
provenance `INTEGRATED.md` notes, the frozen ten-phase board and the future
Phase Eleven VoiceGuard re-entry gate. It runs no AI model, model-dependent
test, live executor, real containment action or network service.

See [`../docs/STATUS.md`](../docs/STATUS.md),
[`../docs/README.md`](../docs/README.md) and
[`../raksha/PHASE910_UNIFIED_RELEASE.md`](../raksha/PHASE910_UNIFIED_RELEASE.md).
