# Apps

Exactly two apps are active:

- [Citizen](citizen/README.md) hosts the PWA, MessageGuard, risk fusion, report routing and the mounted VIGIL image-privacy runtime. It is model-backed and process-local.
- [Infra](infra/README.md) hosts deterministic signed telemetry, detection, governance, dry-run containment and the read-only console. It does not import VIGIL.

Both apps bind all interfaces for preview and share the `packages/` contract layer. Neither app starts a live executor or Commander/SLM client. Real-world privacy efficacy remains UNMEASURED.
