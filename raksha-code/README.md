# raksha-code — RAKSHA application monorepo

> **Status: M1–M5 shipped.** spine + Sentinel shields + Citizen PWA + RAAVAN
> kill chain + containment planner are all real and tested (67/67). Six-day
> hackathon plan lives in `../raksha/ROADMAP.md`. **Nothing here performs
> real-world actions** — the organ-backed executor is dry-run by construction
> (no host ever touched).

## Layout

```text
spine/          shared kernel — ported from eigenshield-v2, then hardened for RAKSHA
spine/containment.py  M5: exhaustive min-disruption cut planner (J = C+λD+μR+νA)
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
tests/          pytest — 67 tests incl. M1 end-to-end campaign flow
requirements.txt
```

citizen/          RAKSHA Citizen (M3) — offline PWA + same-origin FastAPI
  messageguard/     deterministic scam-script scorer (en/hi/te signal families)
  voiceguard/       interface + spectral fallback (NEVER claims clones; labelled)
  fixtures/         20-item synthetic labeled corpus (hand-authored)
  api.py            GET /api/citizen/health · POST screen_message / screen_voice / report
  app/              PWA: home · check message · check voice · report · 1930 panic button

## Quickstart

```bash
cd raksha-code
python -m venv ../.venv && source ../.venv/bin/activate   # or reuse repo venv
pip install -r requirements.txt
pytest -q                                        # 67 passed expected
python -m spine.boot_manifest --check spine/config/manifest.json
python -m spine.ledger_cli verify                # (after any run wrote a ledger)
python -m spine.bus --policy spine/config/policy.yaml \
    --topology spine/config/company_topology.json --port 8090
python -m citizen.api --port 8095                 # Citizen app + PWA
curl -s localhost:8090/api/health
```

Verify a campaign flows: `pytest tests/test_m1_campaign_flow.py -q`.

## Porting notes (honesty log)

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
