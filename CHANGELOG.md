# Changelog

## Current

## Attack Lab: simulated attack demonstrations in the Infrastructure console

The Infrastructure console gained a triggered demo surface for live presentations.
`apps/infra/demo/scenarios.py` scripts one scenario per requested attack —
suspicious repeated login activity, a ransomware encryption sweep, a coordinated
AI-agent flood, a hostile document, a suspicious infrastructure and monitoring
anomaly, a kernel tamper with self-healing, a staged exfiltration, plus a benign
control — where each step is one enterprise-I1 event assembled from the detector
registry's own fixtures, with the outcome that step is expected to produce. The new
`/console/attack-lab` view gives every scenario its own trigger button and a reset,
shows a per-step timeline with timestamps, severity, description and detection
status, and moves the dashboard tiles because the counters are polled from the same
gateway state view the other console surfaces read.

The events travel the real path: signed steps are posted through the gateway signer,
and unsigned and forged ones are sent untouched so the runtime's refusal is what the
screen reports. Detection, quarantine, cross-leg fusion, Governor decisions, dry-run
containment and ledger sequence numbers are therefore the runtime's own answers, not
a storyboard. Every event carries the `SIMULATED` label in its summary, campaign id
and case id; a per-run tag keeps repeated runs valid against the runtime's
duplicate-id refusal, and each step's stamp is the live clock at trigger time.
Nothing here touches a host, network, account or file, no exploit or traffic
generator exists, the executor stays dry-run, organ control and admin override stay
refused, and efficacy against real attack traffic remains UNMEASURED.

`GET /api/infra/scenarios` serves the script (read-only, its path and contract from
`apps/infra/features.py`, recorded in the Infra boot manifest), and
`frontend/src/lib/scenarios.ts` classifies each reply against the step's declared
expectation so drift appears on screen. `tools/check_frontend_integration.py` now
re-derives every scripted step through `detect(event)` — labels, per-run id tokens,
payload keys, organ coverage and declared versus actual outcome — and
`tools/run_frontend_smoke.py` drives the whole library over HTTP through both apps,
asserting the benign control stays quiet and no live action path appears.
`tests/test_phase12_attack_lab.py` pins the same contract in-process, including that
a replayed run tag is refused rather than counted as a second detection. The legacy
`/demo/hospital` exercise and its isolated resettable runtime are unchanged.


## One-action launcher for the whole application

`start.sh`, `stop.sh`, `start.bat` and `stop.bat` now start and stop the entire
workspace in one action. Each start preflights the interpreter, the packages the
two apps import, the credential variables (reported by name only) and the ports
claimed by the boot manifests; starts exactly the Infra and Citizen processes;
waits for both console origins to answer; prints one URL per interface plus the
health, status, VIGIL, legacy-PWA, fake-hospital and Attack Lab entry points; and records the
pids, ports and log paths in the git-ignored `.raksha/` run directory. Re-running
a start against a live stack reports it and starts nothing, so a double-click
cannot bind a duplicate app; a port held by a process these scripts did not
record is a hard preflight failure with the variable to move it. Stop signals
only the recorded pids, re-checking each command line first and refusing a
recycled pid that now belongs to another program, and a second stop is a no-op.
Startup failures surface the app's own log tail instead of a bare timeout. The
start path opens no database and no broker (the audit ledger is in-process and
the console gateway is a module inside each app), needs no Node process at serve
time, and executes no model run, eval pass or Commander call — Infra's optional
model stays `EIGENSHIELD_MODEL=disabled` unless the operator sets it. All four
scripts delegate to `tools/launch_apps.py`, which gained `--check`, `--detach`,
`--status`, `--stop`, `--restart`, `--timeout`, `--state-dir` and an optional
`.raksha/env` config file, so POSIX and Windows share one implementation;
`make start`, `make stop`, `make status` and `make restart` wrap it, CI runs the
preflight plus the shell-script syntax check, and `tests/test_phase11_launcher_scripts.py`
keeps the scripts honest about the flags, targets and processes they name.

## Unified Phosphor frontend integration

The uploaded Next.js frontend was extracted, pruned to a reproducible npm dependency set, rebuilt as a static export and served by the two active Python apps. A shared same-origin gateway now connects Consumer and Organization routes to actual Citizen and Infrastructure endpoints, injects scoped tokens, signs sandbox telemetry and returns structured errors. Both Citizen and Infrastructure interfaces are preserved; legacy UI files remain recoverable under `archive/frontend-backup`.

The console is now the default interface on both app origins: `/` redirects to the app's console route, the built bundle is served from `packages/frontend/static`, and an unknown `api/*` path answers with JSON not-found instead of the client shell. Gateway compatibility views are labelled read-only projections and add no claims the backends do not make — no organ health nobody measured, no canary that did not run, no synthesized autonomy tier, and organ halt/resume answers `DRY_RUN_ONLY` with zero real actions. The transcript screen returns the real MessageGuard verdict, score, legacy band, engine, reasons and rule families instead of an invented confidence label, and its earlier fake "ledger verify" field was removed. Two bugs found while wiring this surface are fixed: the Citizen report forward now signs and validates with the shared ingest key from `packages/contracts` (the bus previously rejected its own reports as `tampered`), and trailing-slash deep links now serve their own prerendered document rather than the root shell.

Two gates cover the integration. `tools/check_frontend_integration.py` proves statically that every path the console calls resolves to a real Citizen or Infra route, that no credential, absolute backend URL, WebSocket or browser media API reaches the served bundle, that the exported build matches the committed one, that the shared module set contains no retired prototype module, and that the Red Team replay still uses the detector registry's own firing fixtures. `tools/run_frontend_smoke.py` boots both apps on free ports and exercises the console, gateway proxy, transcript screen, three-act replay, fleet/containment views, ledger and auth boundaries over real HTTP, with non-default tokens so an embedded default would fail. The vendored component kit was pruned to the modules the console actually imports, and the frontend toolchain is the repository's Node/npm setup rather than Bun; the untouched original bundle remains `ark-omnitek-frontend.zip`. VIGIL active, status, capability and detector cards, the functional fake-hospital attack exercise, dry-run-only execution and UNMEASURED real-world claims are unchanged.

VIGIL active: the Citizen app now mounts the TorchScript PrivacyNet image-privacy runtime. The Citizen backend also exposes a same-origin VIGIL status endpoint and app-state model flags. The boot manifest, requirements, continuous integration workflow, evaluation runner, claims ledger, runtime tests, HTTP smoke, weight gate and purge gate were aligned with the active model-backed build. Infra stays deterministic and dry-run, and now exposes owned status, capability and detector cards, a navigation-ready read-only console, read-token fallbacks for preview proxies, and an HTTP smoke gate. A functional fake-hospital attack exercise now drives a series of synthetic attacks through the Infra UI and the deterministic detector/Governor/ledger/dry-run path, with a dedicated smoke gate. No real patient data or live containment is used. The retired voice-scorer code, capture assets, synthetic corpora, model-dependent tests and frozen hash pins were removed from executable paths. Real-world accuracy, recall, false-positive rate and privacy efficacy remain UNMEASURED.

See the [generated evaluation report](EVALS.md), [status](docs/STATUS.md), [release summary](summary.md) and [retired code note](archive/provenance/RETIRED.md).
