# Citizen

Citizen is the single user-facing service. It serves the offline-first PWA, MessageGuard screening, risk fusion, report routing and the VIGIL dashboard under `/vigil/`. VIGIL is a shared package mounted into this FastAPI app; it is not a third service.

- `api.py` owns health, features, reports, risk and message endpoints, then mounts VIGIL.
- `features.py` declares the active model and honest VIGIL card.
- `GET /api/citizen/vigil/status` reports the mounted VIGIL model status and honesty card.\n- `app.state` carries the model-backed, VIGIL-integrated and status-path flags.
- `copy.py` owns citizen-facing sentences and the shared renderer.
- `retention.py` documents process-memory-only VIGIL sessions and purge triggers.
- `risk/` fuses bounded, low-confidence advisory signals.
- `BOOT_MANIFEST.json` declares the active model and weights manifest.

The active TorchScript weights are verified by `tools/check_vigil_assets.py`. VIGIL local metrics are not real-world privacy efficacy, which remains UNMEASURED. See the [VIGIL runtime notes](../../packages/vigil/README.md), [status](../../docs/STATUS.md) and [generated evaluation report](../../EVALS.md).

The integrated [Phosphor frontend](../../frontend/README.md) is the default UI. Legacy frontend compatibility routes are retained as recoverable fallbacks; backend APIs are unchanged.
