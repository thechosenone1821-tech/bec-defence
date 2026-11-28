# Shared Phosphor frontend package

`gateway.py` is the one frontend gateway registered on **both** active RAKSHA
apps by `apps/citizen/api.py` and `apps/infra/backend/app.py`. It is a module
inside those two processes — it is not a third app, and it owns no database,
model or network listener of its own.

`static/` is the build produced by `cd frontend && npm run build`
(`next build && node scripts/sync-static.mjs`). It is committed so a checkout
serves the console without a Node toolchain, and it is regenerated — never
hand-edited.

## What it serves

| Path | Behaviour |
| --- | --- |
| `GET /` | `307` to the app's console default (`/console/call-screen` for Citizen, `/console/rings` for Infra) |
| `GET /api/frontend/health` | frontend contract, static-build presence, gateway and root redirect |
| `GET /api/gateway/*` | same-origin backend-for-frontend gateway (below) |
| `GET /{asset}` | static file, directory → `index.html`, unknown client route → the shell; unknown `api/*` → JSON `404`; missing bundle → `503` |

## What the gateway does for the browser

- **Credentials stay server-side.** Reads use the scoped Infra token, ingest
  uses the sensor token, and the sandbox signing key is resolved through
  `packages.contracts.envelope.ingest_key()` so it always matches what the
  runtime verifies. Nothing here is ever sent to the client.
- **Request handling.** JSON bodies are forwarded verbatim; every proxied
  request carries `Accept`, `Content-Type` and a bounded timeout. Batched
  ingest posts one envelope per backend call because `POST /api/ingest` accepts
  a single event.
- **Error handling.** A malformed body is `400`; a missing bundle is `503`; an
  unreachable backend is `502` with `{"ok": false, "error", "detail"}`, which is
  the shape `frontend/src/lib/gateway.ts` renders. Responses carry
  `Cache-Control: no-store` and an `X-Gateway-Target` header.
- **Compatibility views, labelled as views.** `api/health`, `api/state`,
  `api/orchestrate`, `api/containment` and `api/fleet` are read-only
  projections over the active endpoints (`/v1/state`, `/v1/decisions`,
  `/v1/metrics`, `/v1/quarantine`, `/api/infra/detectors`). Each response names
  its sources. They add no claims the backends do not make: no organ "health"
  that nobody measured, no canary that did not run, no Commander, no live
  containment — and organ control answers `DRY_RUN_ONLY` with zero real actions.

## Configuration

| Environment variable | Default |
| --- | --- |
| `RAKSHA_CITIZEN_INTERNAL_URL` | `http://127.0.0.1:8095` |
| `RAKSHA_INFRA_INTERNAL_URL` | `http://127.0.0.1:8090` |
| `RAKSHA_FRONTEND_READ_TOKEN` | `RAKSHA_OBSERVER_TOKEN` or the demo observer token |
| `RAKSHA_FRONTEND_SENSOR_TOKEN` | `RAKSHA_SENSOR_TOKEN` or the demo sensor token |
| `RAKSHA_SENSOR_KEY` | the shared ingest key the runtime verifies with |

`tools/launch_apps.py` sets all of these for the two-process run. A single-app
run needs none of them: each app points its own gateway at the port it binds
(`--port` moves `RAKSHA_*_INTERNAL_URL` with it) and the read/ingest tokens fall
back to the app's own `RAKSHA_OBSERVER_TOKEN` / `RAKSHA_SENSOR_TOKEN` records.
The static bundle is env-free by design — no variable reaches the browser.

Gates: `tools/check_frontend_integration.py` (static integration contract) and
`tools/run_frontend_smoke.py` (boots both apps and exercises every path above).
