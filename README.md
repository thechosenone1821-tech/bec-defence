# RAKSHA

RAKSHA is an active two-app defence workspace. Citizen hosts MessageGuard and the model-backed VIGIL TorchScript image-privacy runtime. Infra provides deterministic signed telemetry, governance, dry-run containment and a read-only console. The Citizen backend exposes a same-origin VIGIL status endpoint and app-state model flags. The Infra backend exposes owned status, capability and detector cards, a navigation-ready read-only console, read-token fallbacks for preview proxies, and a functional fake-hospital attack exercise at `/demo/hospital` that drives scripted synthetic events through the deterministic detector/Governor/ledger/dry-run path. Real-world accuracy, recall, false-positive rate and privacy efficacy remain UNMEASURED.

## Active surfaces

- [Status](docs/STATUS.md) describes the active runtime and its honesty limits.
- [Evaluations](EVALS.md) are generated from the one active results file.
- [Release summary](summary.md) records the current architecture and command surface.
- [VIGIL runtime](packages/vigil/README.md) documents the Citizen-mounted privacy engine.
- [Retired code note](archive/provenance/RETIRED.md) explains the purge boundary.
- [Tools](tools/README.md) lists the active gates and runners.

## Commands

Run `make ci` for the full local gate suite, `make hospital-smoke` for the fake-hospital exercise proof, and `make eval-generate` after changing measurement inputs. Run `make vigil-tests` and `make vigil-smoke` for the dedicated VIGIL proof paths. Run `make run` to launch exactly the Citizen and Infra processes.

No live containment action, Commander inference, network capture or real-world efficacy claim is part of this workspace. VIGIL modifies pixels and reports local artifact metrics; it does not claim deepfake prevention, modern face-recognition defeat or an anonymity guarantee.
