# Apps

Exactly two apps are active:

- [Citizen](citizen/README.md) hosts the PWA, MessageGuard, risk fusion, report routing and the mounted VIGIL image-privacy runtime. It is model-backed and process-local.
- [Infra](infra/README.md) hosts deterministic signed telemetry, detection, governance, dry-run containment and the read-only console. It does not import VIGIL.

Both apps bind all interfaces for preview and share the `packages/` contract layer. Neither app starts a live executor or Commander/SLM client. Real-world privacy efficacy remains UNMEASURED.

The integrated [Phosphor frontend](../frontend/README.md) is the default UI. Legacy frontend compatibility routes are retained as recoverable fallbacks; backend APIs are unchanged.

Start both apps — and the console they serve — with `./start.sh` (or `start.bat`), inspect them with `--status` and stop them with `./stop.sh` (or `stop.bat`); `make start`, `make stop`, `make status` and `make restart` wrap the same launcher. The start waits for both origins to answer, opens no database or broker, and executes no model run.
