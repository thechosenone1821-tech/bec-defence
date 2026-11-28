# ARK OMNITEK — RAKSHA Phosphor frontend

This is the frontend from the uploaded bundle, integrated with the existing
RAKSHA backend. It builds to a static export and is served by **both** active
Python apps (Citizen and Infra/Sentinel), so there is no third app to run and
no browser-side `localhost` call. The original bundle stays in the repository
as [`../ark-omnitek-frontend.zip`](../ark-omnitek-frontend.zip) for
provenance, and the UI it replaced is preserved under
[`../archive/frontend-backup`](../archive/frontend-backup).

## Architecture

- Next.js App Router, React 19, TypeScript, Tailwind CSS 4 — the toolchain the
  bundle shipped, with its unused packages pruned (no Prisma, no Bun lockfile,
  no NextAuth, no editor/markdown kit).
- `next.config.ts` sets `output: "export"` with `trailingSlash: true`; the
  bundle's Next.js route handlers were removed, so the browser talks only to
  the Python gateway.
- `npm run build` writes `out/` and copies it into
  [../packages/frontend/static](../packages/frontend/static), which is what the
  apps serve. `out/`, `node_modules/` and `.next/` are git-ignored; the synced
  bundle is committed so a checkout serves without a Node toolchain.
- [../packages/frontend/gateway.py](../packages/frontend/gateway.py) serves the
  static files, adds `/api/gateway/*` and `/api/frontend/health`, injects the
  scoped backend tokens, and signs sandbox telemetry with the ingest key. The
  browser never holds a credential.
- Both modes are preserved: consumer surfaces call the Citizen API,
  organization surfaces call the deterministic Infra runtime.
- The vendored component kit is pruned to the modules this console imports
  (`ui/liquid-glass-toggle`, `ui/toast`, `ui/toaster`) and the packages only the
  rest of that kit needed were dropped from `package.json`. Nothing was lost:
  the complete original kit is inside the retained ZIP.
- Live data comes from polling the gateway, never from a browser WebSocket, and
  the browser holds no token — the gateway adds the scoped backend header.

## Routes

| Surface | Path | Reads / writes |
| --- | --- | --- |
| Landing + mode dock | `/` | none |
| Call Screen | `/console/call-screen` | `POST /api/citizen/screen_transcript` |
| Message Guard | `/console/message-guard` | `POST /api/citizen/screen_message` |
| Citizen Spine | `/console/citizen-spine` | `/api/citizen/report`, Infra health + state |
| VIGIL | `/console/vigil` | `/api/citizen/assess`, `/api/citizen/vigil/status` |
| Rings | `/console/rings` | Infra fleet/state views, signed replay ingest |
| Governance | `/console/governance` | Infra state, orchestration, containment |
| Red Team | `/console/red-team` | three-act replay against the detector registry |
| Attack Lab | `/console/attack-lab` | `GET /api/infra/scenarios`, signed + untrusted replay ingest |

## Attack Lab — simulated attack scenarios

The Attack Lab is the presentation surface for the Infrastructure console: one
trigger button per scripted scenario, a reset, a live per-step timeline and
dashboard tiles that move when a scenario runs. It is deliberately thin:

- `src/lib/scenarios.ts` loads the script from `GET /api/infra/scenarios`, mints a
  per-run tag, posts each step, and classifies the runtime's own answer against the
  step's declared expectation. It holds no payload numbers of its own —
  `apps/infra/demo/scenarios.py` does, copied from the detector registry's fixtures.
- Signed steps go to `POST /api/gateway/spine-signed`, so the gateway mints the HMAC
  and the browser never holds a sensor key. Unsigned and forged steps go to
  `POST /api/gateway/spine/api/ingest` exactly as built: the refusal is the point.
- Every dashboard number is polled from the gateway state view
  (`GET /api/gateway/spine/api/state`), the same surface Rings and Governance read.
  Nothing is seeded, cached or animated in from a fixture, and the clock shown for a
  row is the event stamp the runtime echoed, or the poll time — never a synthetic
  "live" timestamp.
- Each row is labelled `SIMULATED`, and the page states what the run does not prove:
  dry-run containment only, no Commander inference, real-world efficacy UNMEASURED.

## Commands

```bash
npm ci --no-audit --no-fund
npm run build        # next build (typechecks) + sync into packages/frontend/static
npm run typecheck    # tsc --noEmit
npm run lint         # eslint, app code held to the strict react-hooks rules
npm run start        # optional standalone static preview on PORT 3000
```

From the repository root — one action starts everything the console needs:

```bash
./start.sh            # preflight + both apps + both console origins, waits until ready
./start.sh --status   # what is running, where, and which logs to read
./stop.sh             # stop only the pids start.sh recorded
make frontend-install
make frontend-build
make frontend-check   # tools/check_frontend_integration.py
make frontend-smoke   # tools/run_frontend_smoke.py — boots both apps over HTTP
make run              # the same two apps in the foreground instead of detached
```

Nothing runs Node at serve time: the apps serve the committed static export, and
`start.sh` (mirrored by `start.bat`) only checks that the bundle is present and
tells you to run `make frontend-build` when it is not.

## Backend mapping

| Browser path | Active backend target |
| --- | --- |
| `/api/gateway/status` | Citizen `/api/citizen/health` + Infra `/api/health`, concurrently |
| `/api/gateway/citizen/<route>` | proxied to the matching Citizen FastAPI route |
| `/api/gateway/citizen/api/citizen/screen_transcript` | alias of `POST /api/citizen/screen_message` |
| `/api/gateway/spine/api/health` | Infra `/api/health`, projected without added claims |
| `/api/gateway/spine/api/state` | `/v1/state` + `/v1/decisions` + `/v1/metrics` |
| `/api/gateway/spine/api/orchestrate` | same sealed state, plus why nothing was executed |
| `/api/gateway/spine/api/containment` | last sealed proposal/decision, dry-run only |
| `/api/gateway/spine/api/fleet` | `/api/infra/detectors` + `/v1/state` + `/v1/quarantine` |
| `/api/gateway/spine/api/fleet/canary` | registry/rule inventory; states that no canary ran |
| `/api/gateway/spine/api/fleet/<organ>/<halt\|resume>` | refused with `DRY_RUN_ONLY` — no live control exists |
| `/api/gateway/spine/api/ingest` | Infra `/api/ingest`, one event per request |
| `/api/gateway/spine-signed` | gateway signs each event, then ingests it |
| `/api/gateway/spine/v1/*` | proxied to the matching Infra runtime route |
| `/api/frontend/health` | frontend contract, static-build and gateway probe |

## What this console deliberately does not do

- **No invented backend state.** The fleet view reports per-organ rules, sealed
  detections and held events — not process health, call counts or error rates,
  because the active build has no organ supervisor to measure. The canary view
  says `ran: false`. The Red Team panel prints the statuses the runtime
  actually returned.
- **No model claims.** Verdicts come from the deterministic MessageGuard
  transcript screen and the deterministic detector/Governor path. Real-world
  efficacy is UNMEASURED, and the pages say so.
- **No live action.** Halt/resume answer `DRY_RUN_ONLY` with zero real actions;
  the ledger refuses overrides with `403`.
- **No microphone, recording or signing in the browser.** The uploaded bundle's
  audio-capture prototype and its Next.js signing routes were archived under
  `../archive/frontend-backup/next-api-prototypes/`; Call Screen pastes a
  transcript instead, and signing lives in the gateway.

## Data flow and error handling

- [src/lib/gateway.ts](src/lib/gateway.ts) is the only network layer: same-origin
  `fetch`, JSON headers, a per-request `AbortController` timeout, `no-store`,
  and one error shape (`detail` → `reason` → `error`) that every panel renders
  through `BackendNotice` with a retry.
- [src/hooks/use-poll.ts](src/hooks/use-poll.ts) is the single polling
  implementation: one pass on mount, then an interval, cancellation-safe, with a
  derived `pending` so a spinner never needs a pre-await `setState`.
- [src/hooks/use-spine-feed.ts](src/hooks/use-spine-feed.ts) polls the state
  view rather than opening a WebSocket; the gateway is the only client of the
  bus.
- `tools/check_frontend_integration.py` asserts every path above exists, that
  no credential or absolute backend URL reaches the bundle, and that the Red
  Team replay still uses the detector registry's own firing fixtures.

Environment defaults for the Python gateway are documented in
[.env.example](.env.example); the static bundle needs no env file. Export the
variables before `./start.sh`, or put them in `.raksha/env` as `KEY=value` lines —
the git-ignored run directory, because the repository's secrets gate rejects any
file named `.env`. Real environment variables always win over the file, and the
launcher prints these names with `set` / `demo default`, never their values.
