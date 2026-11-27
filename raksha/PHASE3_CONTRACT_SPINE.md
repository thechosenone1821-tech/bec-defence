# RAKSHA — Phase 3: Unified Shared Contracts and Spine

> **Status:** Phase 3 code scaffold implemented; Phase 4 Citizen consolidation later implemented · **Date:** 2026-11-26 · **Branch:** `arena/3b136fd9-bec-defence`
>
> **User constraint preserved:** the repo is still **two separate apps**, not one
> blended app. VoiceGuard / MAYA remain untouched. At Phase 3 close, Phase 4+
> work was not started; see `PHASE4_CITIZEN_CONSOLIDATION.md` for the later
> Phase 4 implementation.
>
> **Phase 4 note:** counts below are the Phase 3 snapshot; current deterministic
> counts are in [`../BUILD_STATE.md`](../docs/STATUS.md) and
> [`EVALS.md`](../EVALS.md). See
> [`PHASE4_CITIZEN_CONSOLIDATION.md`](PHASE4_CITIZEN_CONSOLIDATION.md).
>
> **Companion:** [`COMBINED_SYSTEM_ROADMAP.md`](COMBINED_SYSTEM_ROADMAP.md),
> [`PHASE2_CODE_LAYOUT.md`](PHASE2_CODE_LAYOUT.md),
> [`adr/ADR-010-separation-boundaries.md`](adr/ADR-010-separation-boundaries.md),
> [`adr/ADR-011-unified-contracts.md`](adr/ADR-011-unified-contracts.md).

---

## 1. Scope delivered

Phase 3 makes the two apps speak one language **through `packages/` only**:

- one canonical JSON rule in `packages/contracts/canonical.py`;
- one signed-event validation contract in `packages/contracts/envelope.py`;
- one verdict-band table in `packages/contracts/bands.py`;
- one `MSG-*` / reason-code catalogue in `packages/contracts/reasons.py`;
- one sanitizer/entity-token rule set in `packages/contracts/entities.py`;
- one config-pin set and auth-scope list in `packages/contracts/config.py`;
- one backend-route contract in `packages/contracts/backend.py`;
- one append / verify ledger interface and CLI in `packages/ledger/`;
- one signature + Governor action gate in `packages/contracts/guard.py`;
- one reserved VoiceGuard contract slot in `packages/contracts/voiceguard.py`.

The shipped wire formats were **not** rewritten. Compatibility modules delegate
to the shared contracts, so Citizen, Infra, RAAVAN, eval harnesses, enterprise
I1 envelopes, and governance ledger code can be reconciled without breaking
legacy imports or tests.

## 2. Separate-but-integrated boundary

| Root | Phase 3 role |
| --- | --- |
| `apps/citizen/` | Signs reports through `packages.contracts.envelope`; exposes the event contract in health; still owns Citizen UI/API, MessageGuard and risk. |
| `apps/infra/` | Exposes `/app/contract` and `/app/health`; reaches the legacy bus through `packages.spine.bus`; still owns backend, detectors and console. |
| `packages/` | ONLY integration layer. Owns contracts, canonical rule, config pins, backend contract, ledger adapter and action gate. |
| `raksha-code/` | Compatibility/provenance layer for frozen VoiceGuard/MAYA assets, fixtures, legacy tests and shipped runtime behind facades. |

`packages/contracts/separation.py` now also declares
`FORBIDDEN_APP_BYPASS_ROOTS`. `tools/check_phase3_contracts.py` scans `apps/**/*.py`
with `ast` and rejects direct imports of `spine.bus`, `spine.governor`,
`spine.ledger`, `spine.containment`, `spine.sanitizer`, `spine.entity_graph`,
`spine.orchestrator`, or private organ RPC handlers.

## 3. One signed-event envelope

`packages/contracts/envelope.py` normalises three shipped profiles without
changing their wire shape:

| Profile | Signature field | Used by |
| --- | --- | --- |
| `organ-telemetry-v1` | `mac` | Citizen reports, Infra bus, RAAVAN, eval harness |
| `organ-sealed-v1` | `mac` + `signature` | legacy BaseOrgan events |
| `enterprise-i1-v1` | `sig` + `sig_alg` | enterprise I1 dataclass envelopes |

`validate_envelope()` returns one `CanonicalEnvelope` with `contract`,
`profile`, normalised severity, payload/entities/metrics, signature state,
`verified`, `actionable`, `governor_required`, and `signature_required`.
An unsigned or tampered event is never actionable.

`SharedActionGate` is the only new action path: it requires a valid signature
AND a Governor `APPROVED` decision before invoking an optional dry-run
executor. No app code imports a private executor or Governor bypass.

## 4. Canonical JSON and ledger reconciliation

`spine/telemetry_mac.py`, `sentinel/shields/base_organ.py`, `spine/ledger.py`,
enterprise `raksha/events.py`, and governance `raksha/canonical.py` now delegate
to `packages.contracts.canonical`. The rule is:

```text
json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str)
```

`packages/ledger/interface.py` normalises the three shipped ledger shapes
behind one `append(record_type, payload)` / `verify()` adapter. The one CLI is:

```bash
python -m packages.ledger.cli verify --ledger PATH
python -m spine.ledger_cli verify --ledger PATH   # compatibility wrapper
```

`spine/ledger_cli.py` delegates to the shared CLI, so both commands verify the
same chain and produce the same JSON report.

## 5. Config pinning, auth scopes, sanitizer and entity graph

- `packages/contracts/config_pins.json` pins `policy.yaml`,
  `company_topology.json`, `tool_schemas.json`, `system_prompt.txt`, and
  `manifest.json` by SHA-256.
- `spine/boot_manifest.py` uses the shared `BOOT_MANIFEST_PATHS` list.
- enterprise `ALL_SCOPES` re-exports the shared `AUTH_SCOPES`
  (`telemetry:write`, `read`, `admin`).
- `spine/sanitizer.py` and `spine/entity_graph.py` import regexes, entity
  prefixes and `ENTITY_PATH` from `packages/contracts/entities.py`.

Run the full checker:

```bash
python tools/check_phase3_contracts.py
python tools/check_phase3_contracts.py --write-pins   # audited config re-baseline
```

## 6. Backend contract

`packages/contracts/backend.py` maps canonical route names to the legacy
spine-v2 and enterprise-i1 surfaces:

| Canonical | Spine v2 | Enterprise I1 |
| --- | --- | --- |
| health | `/api/health` | `/healthz` |
| ingest | `/api/ingest` | `/v1/telemetry` |
| state | `/api/state` | `/v1/state` |
| orchestrate | `/api/orchestrate` | `/v1/campaigns` |
| ledger_verify | one shared CLI | `/v1/ledger/verify` |
| websocket | `/ws/telemetry` | `/v1/telemetry/stream` |
| decisions | shared Governor reports | `/v1/decisions` |

`apps/infra/backend/app.py` exposes `/app/contract`; route validation is checked
against the real FastAPI app.

## 7. VoiceGuard / MAYA

- No VoiceGuard/MAYA source, PWA/Maya JS, model, capture, i18n, reason, corpus,
  eval, model card, or historical spec content was edited or moved by Phase 3.
- `packages/contracts/voiceguard.py` reserves a contract slot with **no**
  VoiceGuard imports. It records the future requirements only.
- `tools/check_frozen_assets.py` still verifies 28 untouched assets.
- The frozen i18n reason family map is checked against the shared `MSG-*`
  catalogue without editing the frozen module.

## 8. Verification

Final Phase 3 run, 2026-11-26:

| Check | Result |
| --- | --- |
| `pytest -q` from repo root | **1271 passed**, 1 skipped, 1 xfailed, 4 warnings |
| `pytest -q` from `raksha-code/` | **1263 passed**, 1 skipped, 1 xfailed, 4 warnings |
| `pytest --collect-only -q` | **1273 collected** root / **1265 collected** legacy cwd |
| `node --test tests/*.test.js` | **90 passed**, 0 fail |
| `python tools/check_phase3_contracts.py` | **OK — shared contracts pinned and consistent** |
| `python -m packages.contracts` | **OK — 5 shared config pins unchanged** |
| `evals/messageguard/run_evals.py --check` | **OK — results.json matches scorer and fixtures** |
| `python tools/check_frozen_assets.py` | **OK — 28 VoiceGuard/MAYA assets unchanged** |
| `compileall` / `git diff --check` / local links | **clean** |
| import smoke / app and ledger CLI `--help` | **clean** |
| **Total passing checks** | **1361** (1271 Python root + 90 Node) |

Warnings are the pre-existing FastAPI/Starlette/NumPy warnings; no detector
threshold, fixture score, safety rail or frozen asset changed. See
[`../BUILD_STATE.md`](../docs/STATUS.md), [`EVALS.md`](../EVALS.md), and
[`CHANGELOG.md`](CHANGELOG.md) for the same current numbers.

## 9. Scope honesty

This phase unifies **contracts and compatibility seams**, not all runtime
implementation. `packages/spine`, `packages/governance`, and `packages/ledger`
still facade shipped `raksha-code/` runtime where needed. Full implementation
moves for governance, organs, RAAVAN/corpora/evals, docs/archive and packaging
remain Phases 6–10. No commit or push was requested.
