# Active build summary

This workspace is model-backed. Citizen is the single user-facing service and mounts VIGIL in-process. Infra remains deterministic, read-only and dry-run. Shared contracts, governance, MessageGuard and the append-only ledger stay in one package layer.

## Runtime

The Citizen app serves the offline-first PWA, MessageGuard screening, risk fusion, report routing and the VIGIL dashboard. VIGIL loads the committed TorchScript PrivacyNet checkpoint lazily, produces semantic masks, applies seeded Gaussian noise, structured-frequency perturbation or composite redaction, sanitises exported PNG metadata and purges session buffers. The boot manifest names the active model and weights manifest. The Citizen backend also owns a VIGIL status endpoint and app-state model flags. The weights gate verifies the committed hashes and sizes.

Infra keeps the single detector registry, quarantine-before-detection semantics, Governor, dry-run executor, signed telemetry, append-only ledger and read-only console. Its boot manifest declares deterministic operation and a dry-run executor. The completed Infra surface adds owned status, capability and detector cards, a navigation-ready read-only console, read-token fallbacks for preview proxies, and an HTTP smoke gate. A functional fake-hospital attack exercise exposes start/step/play/reset controls for an isolated synthetic attack series shown in the UI; all events still traverse detector, Governor, ledger and dry-run executor, with zero real actions. The Commander card stays disabled. No live executor or Commander/SLM client is imported.

## Honesty

Real-world accuracy, recall, false-positive rate and privacy efficacy remain UNMEASURED. The generated evaluation report labels hand-authored MessageGuard fixtures, synthetic organ fixtures, sandbox replay and local VIGIL training metrics separately. Local model metrics are not field efficacy. Pixel modification coverage is not anonymity. The active UI and API state the claims not made.

## Purge

The retired voice-scorer implementation, its capture assets, synthetic corpora, model-dependent tests, frozen hash pins and placeholder re-entry gates were removed from executable and generated data paths. Historical prose may remain under provenance solely to explain removed material; see the [retired code note](archive/provenance/RETIRED.md). The active [purge checker](tools/check_code_purge.py) fails on retired identifiers in source-controlled text files.

## Proof

The active command surface is [Makefile](Makefile). The continuous integration workflow runs Python tests, browser tests, VIGIL runtime tests, VIGIL HTTP smoke, weight verification, retired-code purge, eval drift, ledger verification, boot manifests, secrets, import policy, claims and local links. The generated [evaluation report](EVALS.md) and [status](docs/STATUS.md) are the outward measurement surfaces. Dedicated [VIGIL documentation](packages/vigil/README.md) explains routes, retention and local metrics.

All changes described here remain local to this working branch. No commit, push, pull request update or live preview is implied by this summary.
