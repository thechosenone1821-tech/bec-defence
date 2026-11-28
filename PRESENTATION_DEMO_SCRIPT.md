# Presentation demo script

Verified against a live stack on this branch. Everything on the Attack Lab screen is
**simulated telemetry** — synthetic events, labelled `SIMULATED` in every row, every
campaign id and every case id. No real host, network, account or file is touched, the
executor is dry-run only, organ control and admin override are refused by design, and
efficacy against real attack traffic is UNMEASURED. No AI model is executed by any step
below.

## Startup

```bash
./start.sh
```

Windows: run `start.bat`. Preflight only (starts nothing): `./start.sh --check`.
It starts both apps, waits for both origins, and prints one URL per interface. Re-running
it against a live stack prints `OK: the stack is already running — no duplicate processes
started` and changes nothing.

## URLs

| Interface | URL |
| --- | --- |
| Citizen interface | `http://127.0.0.1:8095/console/call-screen` |
| Infrastructure interface | `http://127.0.0.1:8090/console/rings` |
| Attack Lab (simulated scenarios) | `http://127.0.0.1:8090/console/attack-lab` |
| Governance (decisions, ledger) | `http://127.0.0.1:8090/console/governance` |
| Infra status card | `http://127.0.0.1:8090/api/infra/status` |
| Scenario catalogue (read-only) | `http://127.0.0.1:8090/api/infra/scenarios` |

Both origins serve the same built console, so either host works for any view; use `8090`
for the Infrastructure views and `8095` for the Citizen views.

## Suggested sequence

1. **Citizen — Call Screen** (`:8095/console/call-screen`). Paste a UPI/OTP demand into the
   transcript box. Expect: verdict `CRITICAL`, the rule-engine name, and the disclaimer that
   nothing is recorded. Then a normal message: expect a low verdict. This sets up "the same
   platform protects people and infrastructure".
2. **Infrastructure — Rings** (`:8090/console/rings`). Point at the eight detection organs
   and the fleet column before anything is triggered.
3. **Attack Lab** (`:8090/console/attack-lab`). Walk the five scenarios below, one click each.
4. **Governance** (`:8090/console/governance`). After the runs, show the sealed decisions, the
   ledger height and that `live_action_paths` is zero: the platform decided, and stopped at
   dry-run on purpose.

## How to trigger each simulation

On each scenario card press **Trigger**. The page posts that scenario's scripted events through
the same signed ingest path a real organ uses, then reads every number back from the runtime.
Press **Reset** to clear the page's view and arm a fresh run tag; **Run all** walks the whole
library, scenario by scenario. Cards are marked `LAST TRIGGERED` after their run.

The library holds eight scenarios. These five make the shortest complete story:

| Order | Scenario | Button | What you should see |
| --- | --- | --- | --- |
| 1 | Suspicious login activity | Trigger on `suspicious-login` | 2 detected (`COOKIE-TURBULENT-REPLAY`), 2 held unverified (the unsigned retry and the forged signature), 1 correctly quiet baseline. Alert line appears; campaign `SIMULATED-suspicious-login-<tag>` fuses across both legs. |
| 2 | Suspicious infrastructure activity | Trigger on `infra-anomaly` | 2 detected on two different organs (`LANDAUER-POWER-RESIDUAL`, `HESSIAN-LYAPUNOV-CLIFF`), 1 held, 1 quiet rack. The point: an anomaly is a finding, not a verdict. |
| 3 | Coordinated AI-agent flood | Trigger on `ai-agent-flood` | 5 detected across three organs (`BEC-RANK1-CONDENSATION` ×3, `HASHIMOTO-CASCADE-RISK`, plus the consumer-leg report), 1 quiet human-traffic step. Many small events becoming one campaign. |
| 4 | Ransomware encryption sweep | Trigger on `ransomware-sweep` | 3 detected (`PAGECURVE-PARITY-BREAK` ×2 on the encrypt burst and the shadow-delete, plus the victim's consumer-leg report), 2 verified no-finding steps — the nightly `backup-job` (busy, invariant intact) and an `endpoint-note` with no readable page-curve features. |
| 5 | Benign load spike (control) | Trigger on `benign-baseline` | 6 events accepted and verified, 0 findings, 0 quarantines, 0 decisions. Loudly quiet is the correct answer, and it proves the demos above are not rigged. |

Other scenarios in the same list, if asked: `hostile-document`, `kernel-tamper`, `staged-exfil`
(the last one is the full chain: detection → cross-leg fusion → Governor decision → dry-run
containment → ledger entries).

## Expected results, on the page and in the data

- Per step, a row with its timestamp, organ, ring, leg, severity, the rule that fired, and its
  detection status: `DETECTED`, `HELD UNVERIFIED`, `NO FINDING`, `REFUSED` (a replayed id), plus
  `ARMED` before a step runs and `BACKEND ERROR` if a call fails. A row whose answer differs from
  the script's expectation is flagged `≠ EXPECTED`, so drift is visible on stage instead of hidden.
- A SIMULATED alert strip, one line per organ the runtime flagged, with the rule ids and the
  entities involved.
- Dashboard tiles that move because the runtime changed: sealed detections, held-unverified
  count, no-finding count, organs lit, Governor decisions, and the ledger height. On a fresh
  stack these five triggers moved it from 3 to 15 sealed detections, from 3 to 6 held events,
  from 3 to 7 organs reporting, and from 49 to 193 ledger entries; `drift` (steps that answered
  differently than their script) stayed at zero.
- Response, not just detection: fused campaigns produce Governor decisions whose executions read
  `SIMULATED` (allowed) or `SKIPPED_REFUSAL` (refused), with
  `containment.executor_result.real_action_count = 0`.
- Repetition is safe: two runs with different tags produced byte-identical outcome sequences in
  verification, and re-sending an old tag is refused as `duplicate event_id` and shown as
  `REFUSED` rather than counted twice.
- The ledger is append-only. **Reset** clears this page's view and starts a new run tag; it does
  not erase sealed evidence, and the page says so. If you want an empty dashboard on stage rather
  than an accumulating one, restart the stack (`./stop.sh && ./start.sh`) — a fresh process starts
  with the seeded sandbox campaign and nothing else.
- The legacy fake-hospital page offers a real server-side reset too: its Reset button calls
  `POST /api/infra/demo/hospital/reset`, which rebuilds that exercise's isolated runtime (steps
  back to zero, its own ledger height back to zero). It never touches the shared runtime the
  console reads.

Useful read-only checks while presenting:

```bash
curl -s http://127.0.0.1:8090/api/infra/scenarios | head -c 400
curl -s http://127.0.0.1:8090/api/gateway/spine/api/state | head -c 400
curl -s http://127.0.0.1:8090/api/gateway/status
curl -s http://127.0.0.1:8090/api/frontend/health
```

## Shutdown

```bash
./stop.sh
```

Windows: `stop.bat`. It signals only the pids recorded in `.raksha/launcher.json`, and refuses a
pid whose command line no longer matches the app it is supposed to own. `./start.sh --status`
shows what is running and where the logs are.

## If a service fails

1. **Find out what is alive:** `./start.sh --status`. `FAIL: infra is not running` (or citizen)
   names the missing half; logs are at `.raksha/logs/infra.log` and `.raksha/logs/citizen.log`.
2. **Restart the whole stack:** `./stop.sh && ./start.sh`. The stop is safe even if nothing is
   running, and the start re-runs the preflight (interpreter, imports, credentials by name,
   ports, static bundle).
3. **Port already taken:** the preflight reports the port as a PROBLEM. Either free it
   (`./stop.sh`) or move to fresh ports and let the gateway follow them:
   `RAKSHA_INFRA_PORT=8123 RAKSHA_CITIZEN_PORT=8124 ./start.sh`, then open
   `http://127.0.0.1:8123/console/attack-lab`.
4. **A console view shows "Service offline":** the page never fakes data while a backend is away.
   Press Retry (or reload) after step 2. The Attack Lab keeps the last catalogue it loaded and
   says so on the page.
5. **Static bundle missing or stale:** `make frontend-build` (then `make frontend-check` and
   `make frontend-smoke`). The bundle is served from `packages/frontend/static` by both apps.
6. **One origin is down:** both apps serve the same built console, so if a page will not load on
   one port, open the same route on the other. `GET /api/gateway/status` on either origin names
   which backend is unreachable. The Organization views (Attack Lab, Rings, Governance, Red Team)
   read the Infra process through that gateway, and the Citizen views read the Citizen process:
   with the backend they need down, the page renders its honest offline notice instead of
   inventing anything — the Attack Lab's catalogue call answers
   `502 spine service unreachable` and the screen shows "Service offline" with a Retry button.
   Start only the missing app (next step), then press Retry.
7. **Frontend unusable at the podium:** the legacy Infrastructure console at
   `http://127.0.0.1:8090/app/console` (state, ledger, organs, API explorer, and a
   `GET /api/infra/scenarios` button) and the standalone fake-hospital exercise at
   `http://127.0.0.1:8090/demo/hospital` are hand-written pages served by the same process, with
   their own start/step/play/reset controls.
8. **Start one app by hand** (bypassing the launcher):
   `.venv/bin/python -m apps.infra --port 8090` and
   `.venv/bin/python -m apps.citizen --port 8095`.
9. **Prove the stack before you walk on stage:** `make ci` runs every gate; the fast targeted
   proofs are `make frontend-smoke` (boots both apps on free ports, drives the console and every
   simulated scenario over real HTTP), `make infra-smoke` (Infra surface plus the catalogue) and
   `make hospital-smoke` (the legacy exercise).

Nothing in the failure path needs a model, a database, a broker or a network capture.
