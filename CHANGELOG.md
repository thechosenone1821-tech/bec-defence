# Changelog

## Current

VIGIL active: the Citizen app now mounts the TorchScript PrivacyNet image-privacy runtime. The Citizen backend also exposes a same-origin VIGIL status endpoint and app-state model flags. The boot manifest, requirements, continuous integration workflow, evaluation runner, claims ledger, runtime tests, HTTP smoke, weight gate and purge gate were aligned with the active model-backed build. Infra stays deterministic and dry-run, and now exposes owned status, capability and detector cards, a navigation-ready read-only console, read-token fallbacks for preview proxies, and an HTTP smoke gate. A functional fake-hospital attack exercise now drives a series of synthetic attacks through the Infra UI and the deterministic detector/Governor/ledger/dry-run path, with a dedicated smoke gate. No real patient data or live containment is used. The retired voice-scorer code, capture assets, synthetic corpora, model-dependent tests and frozen hash pins were removed from executable paths. Real-world accuracy, recall, false-positive rate and privacy efficacy remain UNMEASURED.

See the [generated evaluation report](EVALS.md), [status](docs/STATUS.md), [release summary](summary.md) and [retired code note](archive/provenance/RETIRED.md).
