# RAKSHA apps — separate but integrated

This directory is the Phase 2 answer to "show me the separation", extended by
Phase 3 shared contracts and Phase 4 Citizen consolidation: **two app roots**,
each independently editable, with integration only through
[`../packages/`](../packages/).

| App | Root | Owns | Must not import |
| --- | --- | --- | --- |
| Citizen | `apps/citizen/` | PWA/API boundary, MessageGuard, risk, report rail, app-owned copy, disabled VoiceGuard seam | `apps.infra.*`, `sentinel.*`, `raavan.*`, `spine.*` directly |
| Infra / Sentinel | `apps/infra/` | backend, detectors, console, RAAVAN integration | `apps.citizen.*`, `citizen.*` |

Phase 4 keeps exactly one Citizen service and one physical PWA shell. The active
Citizen path uses `packages/contracts/i18n.py` for rendering logic and
`apps/citizen/copy.py` for citizen-facing sentences; VoiceGuard/MAYA is frozen
behind a hard-disabled feature flag and no AI model is invoked. See
[`../raksha/PHASE4_CITIZEN_CONSOLIDATION.md`](../raksha/PHASE4_CITIZEN_CONSOLIDATION.md)
and [`../tools/check_phase4_citizen.py`](../tools/check_phase4_citizen.py).
Reproduce the deterministic no-AI checks with
`python tools/run_phase4_pytest.py` and
`python tools/run_phase4_node_tests.py`.
