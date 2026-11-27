# RAKSHA Infra / Sentinel app boundary

This is the editable Infra app root. It owns:

- `backend/`: one FastAPI/WS service facade over the deterministic Phase 6–8
  runtime. It publishes `/app/health`, `/app/contract`, `/app/console` and the
  canonical `/v1` API/WS surface; it no longer imports the legacy `spine.bus`.
- `detectors/`: one 8-organ detection registry and `detect(event) -> finding` contract.
- `console/`: operable read-only SOC console; no Governor override or mutation route.
- RAAVAN replay remains a legacy `../../raksha-code/raavan/` compatibility seam
  until the Phase 9 runner unification. Phase 6–8 details are in
  [`../../raksha/PHASE678_UNIFIED_INTEGRATION.md`](../../raksha/PHASE678_UNIFIED_INTEGRATION.md).

Infra must not import `apps.citizen` or `citizen.*`. Shared capabilities are
imported through [`../../packages/`](../../packages/), especially
`packages.spine` and `packages.contracts`. Legacy `spine`, `sentinel`, `raavan`,
`corpora` and `evals` imports are allowed only as compatibility seams until
their Phase 5–9 migrations land; app-level bypass roots are rejected by
[`../../tools/check_phase3_contracts.py`](../../tools/check_phase3_contracts.py).

See [`../../raksha/PHASE3_CONTRACT_SPINE.md`](../../raksha/PHASE3_CONTRACT_SPINE.md)
and [`../../raksha/PHASE4_CITIZEN_CONSOLIDATION.md`](../../raksha/PHASE4_CITIZEN_CONSOLIDATION.md).
