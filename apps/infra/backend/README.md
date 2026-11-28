# Infra backend facade

This package builds the one Infra FastAPI app from `packages.spine.runtime`
and injects the `apps.infra.detectors.registry.detect` contract. It adds the
Infra-owned status, capability and detector endpoints, the read-only
console assets, and the isolated fake-hospital demo UI/control API.

Open `/demo/hospital` for the functional fake-hospital attack series. Run
from repo root: `python -m apps.infra.backend --port 8090`, or set
`RAKSHA_INFRA_PORT` and run without `--port`. The runtime stays deterministic,
dry-run and Commander-disabled. It never imports Citizen, VIGIL, a live
executor or the legacy `spine.bus`.
