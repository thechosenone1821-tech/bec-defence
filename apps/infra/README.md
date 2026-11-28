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
- `demo/`: two synthetic attack surfaces. `hospital.py` runs a functional
  multi-stage exercise for one fake organisation in an isolated runtime the UI can
  start, step, play and reset. `scenarios.py` is the read-only script library the
  Infrastructure console's **Attack Lab** triggers from: one scenario per requested
  attack (suspicious logins, a ransomware sweep, a coordinated AI-agent flood, a
  hostile document, an infrastructure/monitoring anomaly, a kernel tamper, a staged
  exfiltration, plus a benign control), each step one enterprise-I1 event built
  from `detectors/registry.py`'s own fixtures with the outcome that step is
  expected to produce.
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

## Attack Lab — simulated attack demonstrations

`GET /api/infra/scenarios` serves the script library: every scenario, every step,
the exact event object the console posts, and what that step is expected to do.
The route is read-only (a `POST` there is a 405) and its path, contract and
capability card come from `features.py`, like every other Infra surface.

The demo works by *not* faking an outcome. The browser posts each scripted event
through the same-origin gateway ingest path a real organ uses — signed events get
their HMAC from the gateway, unsigned and forged ones are sent as built so the
runtime has to refuse them — and then reads detection, quarantine, fusion,
Governor decision, dry-run execution and ledger numbers back out of the runtime's
state view. The console therefore moves as a real incident would move it, and the
page can only ever show what the pipeline accepted.

Honesty rules the module and the page both follow:

- every event carries the label `SIMULATED` in its own summary, campaign id and
  case id (`SIMULATED-<scenario>-<tag>`), not just in a page banner;
- ids keep a per-run `{tag}` token so a repeat never reuses an `event_id` the
  runtime would refuse, and `{ts}` is filled with a live wall clock at trigger
  time, so timestamps on screen are the timestamps of this run;
- the quiet steps are as scripted as the loud ones: a benign control must produce
  zero findings, and that is shown as a result rather than hidden;
- reset clears the console's view and starts a new tag; it does not and cannot
  erase the append-only ledger, and the page says so;
- no host, network, account or file is touched, no exploit or traffic generator
  exists here, the executor stays dry-run, organ control and admin override stay
  refused, and efficacy against real attack traffic is UNMEASURED.

`tools/check_frontend_integration.py` re-derives every step against `detect(event)`
at check time, so a scenario that starts claiming something the detector would
skip fails CI before it can fail a presentation.

Start with `python -m apps.infra --port 8090`, or set `RAKSHA_INFRA_PORT` to
use a fresh preview port without editing the boot manifest. The shared launcher
also reads `RAKSHA_INFRA_PORT` and `RAKSHA_CITIZEN_PORT`.

The integrated [Phosphor frontend](../../frontend/README.md) is the default UI. Legacy frontend compatibility routes are retained as recoverable fallbacks; backend APIs are unchanged.
