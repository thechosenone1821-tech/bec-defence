> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../docs/STATUS.md); see the [retired code note](../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# RAKSHA — Phase 2 Code Layout: Separate but Integrated

> **Status:** Phase 2 code scaffold implemented; Phase 3 contracts and Phase 4 Citizen consolidation later implemented · **Date:** 2026-11-26 · **Branch:** `arena/3b136fd9-bec-defence`
>
> **Phase 3/4 note:** the verification numbers below are the Phase 2 snapshot.
> Shared contracts, compatibility delegation and Citizen consolidation now live
> in `packages/` and `apps/citizen/`; see
> [`PHASE3_CONTRACT_SPINE.md`](PHASE3_CONTRACT_SPINE.md),
> [`PHASE4_CITIZEN_CONSOLIDATION.md`](PHASE4_CITIZEN_CONSOLIDATION.md), and
> `../BUILD_STATE.md` for current counts. Phase 5+ is not authorized.
>
> **User requirement:** the repo must not become one blended app. Citizen and
> Infra/Sentinel must remain separately editable, integrate through shared
> packages, and leave VoiceGuard / MAYA alone.
>
> **Scope:** code layout and boundary enforcement. This is not a big-bang merge
> or a full deletion of historical trees. It creates the visible `apps/` and
> `packages/` roots, moves the editable Citizen Python modules, adds app
> facades, compatibility aliases and boundary tests, and pins the frozen
> VoiceGuard/MAYA assets by hash.
>
> **Companion:** [`COMBINED_SYSTEM_ROADMAP.md`](COMBINED_SYSTEM_ROADMAP.md),
> [`PHASE1_ARCHITECTURE_FREEZE.md`](PHASE1_ARCHITECTURE_FREEZE.md),
> [`adr/ADR-010-separation-boundaries.md`](adr/ADR-010-separation-boundaries.md).

---

## 1. What changed

```text
bec-defence/
├── apps/                         # NEW: two independent app roots
│   ├── README.md                 # separation rules
│   ├── citizen/                  # APP 1 — editable Citizen surface
│   │   ├── api.py                # moved from raksha-code/citizen/api.py
│   │   ├── __main__.py           # python -m apps.citizen
│   │   ├── messageguard/         # moved from raksha-code/citizen/messageguard
│   │   ├── risk/                 # moved from raksha-code/citizen/risk
│   │   ├── legacy_voiceguard.py  # ONE adapter to the frozen seam
│   │   ├── app -> ../../raksha-code/citizen/app          # symlink, untouched
│   │   └── fixtures -> ../../raksha-code/citizen/fixtures # symlink, untouched
│   └── infra/                    # APP 2 — editable Infra surface
│       ├── backend/              # FastAPI facade over packages.spine
│       ├── detectors/            # 8-organ registry facade
│       └── console/              # read-only placeholder
├── packages/                     # NEW: shared integration layer only
│   ├── contracts/                # machine-readable separation contract
│   ├── spine/                    # bus + telemetry compatibility facades
│   ├── governance/               # Governor compatibility facade
│   └── ledger/                   # ledger compatibility facade
├── tools/                        # NEW: frozen-asset hash checker
├── tests/                        # NEW: root layout tests
├── pytest.ini                    # NEW: root + raksha-code pythonpath
└── raksha-code/                  # compatibility layer / provenance
    ├── apps -> ../apps           # keeps legacy cwd imports working
    ├── packages -> ../packages   # keeps legacy cwd imports working
    ├── citizen/                  # compatibility alias + frozen tree
    │   ├── __init__.py           # aliases citizen.* -> apps.citizen.*
    │   ├── api.py -> ../../apps/citizen/api.py
    │   ├── messageguard -> ../../apps/citizen/messageguard
    │   ├── risk -> ../../apps/citizen/risk
    │   ├── voiceguard/           # FROZEN — untouched, hash-pinned
    │   ├── app/                  # FROZEN PWA/Maya assets — untouched
    │   └── fixtures/             # unchanged measurement corpus
    ├── spine/, sentinel/, raavan/, corpora/, evals/  # legacy runtime still importable
```

## 2. Separation rule

| Layer | May import | Must not import |
| --- | --- | --- |
| `apps/citizen/` | `apps.citizen.*`, `packages.*`, one frozen `citizen.voiceguard` seam | `apps.infra.*`, `sentinel.*`, `raavan.*`, `spine.*` directly |
| `apps/infra/` | `apps.infra.*`, `packages.*`, legacy `spine/sentinel` compatibility seams | `apps.citizen.*`, `citizen.*` |
| `packages/` | `packages.*`, legacy shared runtime compatibility seams | either app |

The single frozen-seam exception is `apps/citizen/legacy_voiceguard.py`. It reads
the untouched VoiceGuard/MAYA modules through the `citizen` compatibility alias;
no other new app file imports VoiceGuard directly.

## 3. Why compatibility seams exist

The user asked to leave VoiceGuard/MAYA alone. Moving `raksha-code/citizen/` as
one directory would have moved those files, so Phase 2 instead:

- moved only editable Citizen Python modules;
- kept the frozen voice tree, PWA/Maya assets and fixtures in place;
- added symlinks so the new app still serves the same PWA and corpus;
- added `raksha-code/citizen/__init__.py` as a package alias so existing
  `citizen.api`, `citizen.messageguard`, `citizen.risk`, and
  `citizen.voiceguard` imports keep working;
- added `raksha-code/apps` and `raksha-code/packages` symlinks so commands run
  from `raksha-code/` resolve the new layout.

This is deliberate: editing `apps/citizen` does not require editing
`apps/infra`, and neither app reaches into the other app's code.

## 4. Boundary enforcement

- `packages/contracts/separation.py` declares allowed import roots.
- `raksha-code/tests/test_phase2_separation.py` scans `apps/**/*.py` and
  `packages/**/*.py` with `ast`, rejects direct cross-app imports, checks
  independent importability in subprocesses, and runs the frozen-asset checker.
- `tools/check_frozen_assets.py` compares 28 VoiceGuard/MAYA assets against
  `tools/frozen_assets.sha256`; it ignores Python bytecode caches.
- `tests/test_phase2_root_layout.py` checks the new roots and compatibility
  symlinks from the repo root.

## 5. Run commands

From repo root:

```bash
python -m apps.citizen --port 8095
python -m apps.infra.backend --port 8090
python tools/check_frozen_assets.py
pytest -q
```

Legacy commands from `raksha-code/` still work:

```bash
python -m citizen.api --port 8095
python -m spine.bus --port 8090
python evals/messageguard/run_evals.py --check
```

## 6. Phase 2 exit-gate honesty

| Roadmap exit gate | Phase 2 result |
| --- | --- |
| One `README.md` explains the whole repo in under one screen | **Deferred to Phase 10**; root README is still historical EIGENSHIELD reference |
| `raksha/` and `raksha-code/` no longer competing roots | **Partially**; `raksha-code/` is now explicitly a compatibility/provenance layer, not a second app |
| No runtime import points at a staging directory | **Yes** for the new app surface; no new app imports staging project trees |
| Two apps are separately editable | **Yes**; enforced by layout, ADR-010 and boundary tests |
| VoiceGuard/MAYA untouched | **Yes**; 28 assets hash-pinned |

This is a **separation-preserving scaffold**, not the final Phase 3–10 migration.
Legacy shared runtime remains importable behind `packages/` facades until the
bus, ledger, Governor, organs, planner and eval runner are consolidated in their
respective phases.

## 7. Safety

- No Governor, ledger, signature, canary or dry-run rail was relaxed.
- No VoiceGuard/MAYA source, model, capture, reason, i18n, PWA or doc content was
  edited by this phase.
- No real-world action or network target was introduced.


## 8. Verification

- Full pytest from repo root: **1259 passed**, 1 skipped, 1 xfailed, 4 warnings.
- Full pytest from `raksha-code/`: **1257 passed**, 1 skipped, 1 xfailed, 4 warnings.
- Node browser tests: **90 passed**, 0 fail.
- `evals/messageguard/run_evals.py --check`: **OK** — results.json matches current scorer and fixtures.
- `python tools/check_frozen_assets.py`: **OK** — 28 VoiceGuard/MAYA assets unchanged.
- `compileall`, `git diff --check`: clean.
