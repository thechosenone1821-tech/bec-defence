# raksha-code — RAKSHA application monorepo

> **Status: historical compatibility tree.** The canonical entry point is
> [`../README.md`](../README.md), the single status board is
> [`../docs/STATUS.md`](../docs/STATUS.md), the generated evaluation is
> [`../EVALS.md`](../EVALS.md), and the claims ledger is
> [`../evals/claims_ledger.json`](../evals/claims_ledger.json). Counts, paths
> and commands below are historical as-of earlier phases, not current release
> measurements; real-world accuracy, latency, uptime, recall and FPR are
> UNMEASURED. `tools/run_phase4_pytest.py` now skips 22 model-dependent Python
> test files and one frozen MAYA Node test. This tree is not a third app;
> VoiceGuard / MAYA stays frozen and the executor is dry-run by construction.
>
> **Phase 2/3/4 compatibility-layer note:** editable app code now lives in
> [`../apps/citizen/`](../apps/citizen/) and
> [`../apps/infra/`](../apps/infra/), with shared facades in
> [`../packages/`](../packages/). This tree remains the compatibility and
> provenance layer for legacy imports, frozen VoiceGuard/MAYA assets, PWA files,
> fixtures, and shipped spine/sentinel/raavan/corpora/evals modules. It is not
> a third app. See
> [`../raksha/PHASE2_CODE_LAYOUT.md`](../raksha/PHASE2_CODE_LAYOUT.md),
> [`../raksha/PHASE3_CONTRACT_SPINE.md`](../raksha/PHASE3_CONTRACT_SPINE.md),
> [`../raksha/PHASE4_CITIZEN_CONSOLIDATION.md`](../raksha/PHASE4_CITIZEN_CONSOLIDATION.md),
> and [`citizen/voiceguard/FROZEN.md`](citizen/voiceguard/FROZEN.md). Phase 3
> makes shipped canonical JSON, config pins, sanitizer rules and the ledger CLI
> delegate to `../packages/`. Phase 4 keeps this tree as the single frozen PWA
> shell and compatibility seam; active Citizen copy/rendering lives in
> `../apps/citizen/copy.py` and `../packages/contracts/i18n.py`.

## Layout

```text
spine/          shared kernel — ported from eigenshield-v2, then hardened for RAKSHA
spine/containment.py  M5: exhaustive min-disruption cut planner (J = C+λD+μR+νA)
evals/run_evals.py    M6: measured baseline × metric table (fixtures only)
evals/messageguard/   MessageGuard v1: reproducible measurement + generated docs
  run_evals.py        --check verifies results.json against scorer + fixtures
  gen_evals_md.py     writes ../raksha/MESSAGEGUARD_EVALS.md from results.json
  sanitizer.py      zero-trust input normalization (HMAC tokens, injection scrub)
  entity_graph.py   10-min attack graph + campaign correlator v0 (union-find)
  ledger.py         append-only SHA-256 hash-chained evidence ledger
  ledger_anchor.py  HMAC-sealed (seq, head) side anchor
  governor.py       deterministic Governor (schema lock, crown jewel, budgets, FIDO2)
  tcb_core.py / tcb_mirror.py   N-version stateless decision twins (fail closed)
  telemetry_mac.py  organ-signed telemetry (HMAC-SHA256) + replay cache
  tripwire.py       anti-probing AI freeze (human step-up to reset)
  boot_manifest.py  SHA-256 config pinning (--pin/--check)
  canaries.py       ESH_CANARY context tripwires
  sandbox_runner.py whitelist subprocess isolation
  bus.py            FastAPI + WS broker (verified-only ingest)
  orchestrator.py   local SLM planner (Ollama; deterministic fallback offline)
  ledger_cli.py     verify / tail / replay the evidence ledger
  config/           policy.yaml · company_topology.json · manifest.json (pinned)
tests/          pytest — 171 passed here / 186 from repo root (no-AI subset)
requirements.txt
```

```text
citizen/          RAKSHA Citizen (M3) — offline PWA + same-origin FastAPI
  messageguard/     v1 deterministic scorer · reason catalogue · normalize · bandmap
                    en/hi/te regex token sets · negation guards · API adapter
  voiceguard/       frozen MAYA/VoiceGuard seam; disabled on the Phase 4 path
  risk/             bounded noisy-OR fusion; no SAFE verdict exists
  fixtures/
    messageguard/   538 hand-authored labelled JSONL fixtures (402 scam / 136 genuine)
    message_fixtures.json   legacy 20-item M3 smoke corpus; NOT a measurement
  api.py            one Citizen service; screen_voice returns NOT_INTEGRATED
  app/              one PWA shell; runtime overlay says voice is not integrated yet
```

## Quickstart

```bash
cd raksha-code
python -m venv ../.venv && source ../.venv/bin/activate   # or reuse repo venv
pip install -r requirements.txt
make test                                       # canonical Python/browser/check gate
make eval                                       # canonical eval drift gate
make eval-generate                              # regenerate EVALS.md + claims ledger
make run                                        # one launcher for both apps
python -m evals.run_evals --check
python -m packages.ledger.cli verify --ledger spine/config/audit_ledger.jsonl
```

Verify a campaign flows: `pytest tests/test_m1_campaign_flow.py -q`.
Verify the integrated detector: `pytest tests/test_messageguard*.py -q`.

## Integration and porting notes (honesty log)

* The standalone Part 3 tree at
  `../archive/provenance/messageguard-snapshot/raksha/` has been folded into
  `citizen/messageguard/` and `evals/messageguard/`. The API's `score_message`
  contract is preserved; `analyze()` is the measured engine. The original
  staging tree is retained only for provenance and is no longer the runtime
  source of truth.
* MessageGuard v1 is rules-based, stdlib-only and offline. Its published
  99.2% detection, 10.3% false-positive rate and 96.8% accuracy are
  **in-distribution, hand-authored-fixture** measurements. Real-world recall
  and FPR remain UNMEASURED; novel scripts and genuine urgent KYC alerts are
  documented failure modes.
* Ported, not imported — `eigenshield-v2/` stays untouched; this tree evolves
  independently. `spine/` docstrings were rebranded; logic carried over as-is.
* Executor is DRY-RUN: every tool returns `{"status": "DRY_RUN_*", ...}`.
  Real organ behavior lands with the M2 Sentinel shields.
* Campaign correlator v0 = union-find over shared entity tokens in the sliding
  window. Temporal kernels / weighted fingerprints are Phase 2.
* Env-var compatibility: `EIGENSHIELD_*` names retained (BUS_KEY, SALT,
  CANARY_KEY, MODEL). Renaming to `RAKSHA_*` is scheduled for the v0.2 branding
  pass; do it in one sweep, not piecemeal.
* `spine/config/manifest.json` pins the config set with package-relative
  paths; re-pin with `--pin` after ANY legitimate config change (audited).
