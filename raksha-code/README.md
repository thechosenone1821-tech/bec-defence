# raksha-code — RAKSHA application monorepo

> **Status: M1–M6 + Citizen phases shipped. Verified 2026-11-26:** 1252 Python
> tests passed (1 skipped, 1 documented xfail) and 90 browser tests passed.
> MessageGuard v1 is integrated: 492 hand-authored en/hi/te fixtures, a
> reproducible eval harness, and a generated report at
> [`../raksha/MESSAGEGUARD_EVALS.md`](../raksha/MESSAGEGUARD_EVALS.md). Six-day
> hackathon plan lives in `../raksha/ROADMAP.md`. **Nothing here performs
> real-world actions** — the organ-backed executor is dry-run by construction
> (no host ever touched).

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
tests/          pytest — 1252 passed incl. M1 end-to-end and MessageGuard v1
requirements.txt
```

```text
citizen/          RAKSHA Citizen (M3) — offline PWA + same-origin FastAPI
  messageguard/     v1 deterministic scorer · reason catalogue · normalize · bandmap
                    en/hi/te regex token sets · negation guards · API adapter
  voiceguard/       Maya synthetic-speech screening (NEVER claims clone detection)
  risk/             bounded noisy-OR fusion; no SAFE verdict exists
  fixtures/
    messageguard/   492 hand-authored labelled JSONL fixtures (372 scam / 120 genuine)
    message_fixtures.json   legacy 20-item M3 smoke corpus; NOT a measurement
  api.py            GET /api/citizen/health · POST screen_message / screen_voice / report
  app/              PWA: home · check message · check voice · report · 1930 panic button
```

## Quickstart

```bash
cd raksha-code
python -m venv ../.venv && source ../.venv/bin/activate   # or reuse repo venv
pip install -r requirements.txt
pytest -q                                        # 1252 passed expected
node --test tests/*.test.js                      # 90 passed expected
python evals/messageguard/run_evals.py --check # published MessageGuard numbers reproducible
python evals/messageguard/gen_evals_md.py      # regenerate ../raksha/MESSAGEGUARD_EVALS.md
python -m spine.boot_manifest --check spine/config/manifest.json
python -m spine.ledger_cli verify                # (after any run wrote a ledger)
python -m spine.bus --policy spine/config/policy.yaml \
    --topology spine/config/company_topology.json --port 8090
python -m citizen.api --port 8095                 # Citizen app + PWA
curl -s localhost:8090/api/health
```

Verify a campaign flows: `pytest tests/test_m1_campaign_flow.py -q`.
Verify the integrated detector: `pytest tests/test_messageguard*.py -q`.

## Integration and porting notes (honesty log)

* The standalone Part 3 tree at
  `../random project that ew need to integrate/raksha/` has been folded into
  `citizen/messageguard/` and `evals/messageguard/`. The API's `score_message`
  contract is preserved; `analyze()` is the measured engine. The original
  staging tree is retained only for provenance and is no longer the runtime
  source of truth.
* MessageGuard v1 is rules-based, stdlib-only and offline. Its published
  99.2% detection, 11.7% false-positive rate and 96.5% accuracy are
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
