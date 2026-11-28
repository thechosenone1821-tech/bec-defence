# Status

VIGIL active: Citizen hosts the committed TorchScript PrivacyNet checkpoint under the same-origin VIGIL route. The runtime loads weights lazily, reports neural-active status, supports protected-region transforms, exports sanitised PNGs and purges in-memory sessions. The Citizen backend exposes a same-origin VIGIL status endpoint that reports the mounted model and keeps efficacy UNMEASURED. Infra remains deterministic, read-only and dry-run with a disabled Commander card. It exposes owned status, capability and detector cards, an operable read-only console, read-token fallbacks for preview proxies, and a functional fake-hospital attack exercise. The exercise uses a synthetic organisation; each scripted attack becomes a signed or invalid event and traverses the real detector, quarantine, campaign-fusion, Governor, ledger and dry-run executor path. Start, step, play and reset controls mutate only an isolated scenario, never real telemetry or hosts. The console's Attack Lab adds a triggered form of the same demonstration: one scripted scenario per requested attack, each step posted through the gateway ingest path a real organ uses, every event labelled SIMULATED, and every counter read back from the runtime rather than written by the page.

The unified Phosphor frontend is now the default interface on both app origins. Its static build is served by the two active Python apps; a shared same-origin gateway injects scoped tokens, maps compatibility API calls to active Citizen and Infra endpoints, and returns structured errors. Both Citizen and Infrastructure interfaces are preserved. Legacy UI files remain available as recoverable compatibility surfaces until they are confirmed unnecessary.

Both app origins are started, inspected and stopped by one launcher: `start.sh`
and `start.bat` (with `stop.sh` / `stop.bat`) run the same
`tools/launch_apps.py` engine, which preflight-checks the interpreter, imports,
credential variables and manifest ports, waits for both console origins to
answer, records the pids under the git-ignored `.raksha/` directory, and refuses
to signal a pid it cannot match to the app it started. A start-up against a live
stack changes nothing, so duplicates are never created. The path starts no
database or broker and executes no model, eval or Commander run.

Real-world accuracy, recall, false-positive rate and privacy efficacy remain UNMEASURED. Local VIGIL metrics describe committed model artifacts only. MessageGuard figures describe hand-authored fixtures only. Replay figures describe sandbox telemetry only. No field FPR, production SLA or guaranteed uptime is claimed.

See the [generated evaluation report](../EVALS.md), the [frontend integration notes](../frontend/README.md), the [release summary](../summary.md), the [VIGIL runtime notes](../packages/vigil/README.md) and the [retired code note](../archive/provenance/RETIRED.md). The active [tools list](../tools/README.md) documents the gates that prove this status.
