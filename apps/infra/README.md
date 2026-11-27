# RAKSHA Infra / Sentinel app boundary

This is the editable Infra app root. It owns:

- `backend/`: the FastAPI/WS facade over the deterministic Phase 6–8 runtime.
  It publishes `/app/health`, `/app/contract`, `/app/console`, the canonical
  `/v1` API/WS surface, and the Infra-owned `/api/infra/status`,
  `/api/infra/capabilities` and `/api/infra/detectors` cards. It no longer
  imports the legacy `spine.bus`.
- `detectors/`: one eight-organ detection registry and the
  `detect(event) -> finding` contract. Quarantine happens before detection for
  unsigned, forged, tampered and unknown-organ events.
- `console/`: an operable read-only SOC console with tab navigation, filters,
  snapshot download, API explorer, and WebSocket status. It has no Governor
  override or mutation control. It links to the separate fake-hospital demo.
- `demo/`: a functional synthetic-organisation attack exercise. Scripted
  events use the active detector/Governor/ledger/dry-run path in an isolated
  runtime; the UI can start, step, play and reset the series.
- `features.py`: the one source for Infra status paths, app-state flags,
  boot-manifest keys, honesty claims and the per-organ detector card.

The console uses a read-scoped token. The backend injects that token into
`console.js`, sets a same-origin read cookie, and accepts a read-only query
token on GET routes so preview proxies that strip `Authorization` headers do
not leave the UI dead. Write and admin paths still require a scoped header or
cookie; query tokens cannot be used for `telemetry:write` or `admin` scopes.

Infra must not import `apps.citizen` or `citizen.*`. It also must not import
VIGIL. Shared capabilities are imported through `packages/`, especially
`packages.spine` and `packages.contracts`. The active eval runner, Infra
HTTP smoke and fake-hospital demo smoke exercise the deterministic replay, the
read surfaces, refusal of append-only override, WebSocket history and the
isolated attack series. Commander remains disabled and the executor is dry-run
only. Demo controls require the read-scoped console token via header or cookie;
query tokens remain GET-only. No real patient data, network traffic or live
containment action is used.

Start with `python -m apps.infra --port 8090`, or set `RAKSHA_INFRA_PORT` to
use a fresh preview port without editing the boot manifest. The shared launcher
also reads `RAKSHA_INFRA_PORT` and `RAKSHA_CITIZEN_PORT`.
