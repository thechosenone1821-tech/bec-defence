# Active build summary

This workspace is model-backed and uses one unified Phosphor frontend served by exactly two active Python apps. Citizen hosts the VIGIL image-privacy runtime and MessageGuard; Infra remains deterministic, read-only and dry-run. Shared contracts, governance, MessageGuard, the append-only ledger and the frontend gateway stay in one package layer.

## Runtime

The [Phosphor frontend](frontend/README.md) is built from the uploaded Next.js ZIP as a static export. `packages/frontend/gateway.py` serves that export from both app origins and provides `/api/gateway/*`. The gateway injects scoped Infra tokens, maps compatibility routes to active endpoints, signs sandbox telemetry with the active sensor key, and never exposes credentials to the browser. Consumer routes exercise Citizen; Organization routes exercise Infrastructure. Both Citizen and Infrastructure interfaces are preserved.

Citizen also serves the offline-first PWA as a compatibility surface, MessageGuard screening, risk fusion, report routing and the mounted VIGIL dashboard. VIGIL loads the committed TorchScript PrivacyNet checkpoint lazily, produces semantic masks, applies seeded transforms, sanitises exported PNGs and purges session buffers. Its efficacy remains UNMEASURED.

Infra keeps the single detector registry, quarantine-before-detection semantics, Governor, dry-run executor, signed telemetry, append-only ledger, read-only console and a functional fake-hospital attack exercise. The console also carries an Attack Lab: scripted simulated attack scenarios — suspicious logins, a ransomware sweep, a coordinated agent flood, a hostile document, an infrastructure anomaly, a kernel tamper, a staged exfiltration and a benign control — each triggered from the page, each step one synthetic event sent through the real signed ingest path, and every detection, quarantine, fusion, decision and ledger figure on screen read back from the runtime. The scenario script is served read-only from `GET /api/infra/scenarios` so no payload number is duplicated in the frontend. The Commander card stays disabled and no live executor or Commander/SLM client is imported; no real host, network or account is touched, and efficacy against real attack traffic remains UNMEASURED.

## Startup

`start.sh` and `start.bat` preflight the interpreter, the imported packages, the
credential variables (by name only) and the ports the two boot manifests claim;
then they start exactly the Infra and Citizen processes, wait until both console
origins answer, and print one URL per interface. Re-running either script against
a live stack reports it rather than binding a duplicate. `stop.sh` and `stop.bat`
signal only the recorded pids, and refuse a pid whose command line no longer
matches the app it is supposed to own. The run directory `.raksha/` holds the
state file and the per-app logs and is git-ignored. Nothing in the start path
opens a database or a broker — the audit ledger is in-process — and nothing
executes a model, an eval pass or a Commander call.

## Honesty

Real-world accuracy, recall, false-positive rate and privacy efficacy remain UNMEASURED. The generated evaluation report labels hand-authored MessageGuard fixtures, synthetic organ fixtures, sandbox replay and local VIGIL training metrics separately. Local model metrics are not field efficacy. Pixel modification coverage is not anonymity. The active UI and API state the claims not made.

## Recovery

The pre-replacement UI is preserved in [archive/frontend-backup](archive/frontend-backup) with a checksum manifest. Legacy compatibility routes remain available until they are confirmed unnecessary. The original uploaded ZIP also remains in the repository.

## Proof

The active command surface is [Makefile](Makefile). CI verifies the launcher preflight, installs frontend dependencies, verifies the static build, runs the frontend integration gate and HTTP smoke, then runs Python tests, browser tests, VIGIL tests, smokes, weight verification, retired-code purge, eval drift, ledger verification, boot manifests, secrets, import policy, claims and local links. The generated [evaluation report](EVALS.md) and [status](docs/STATUS.md) are the outward measurement surfaces.
