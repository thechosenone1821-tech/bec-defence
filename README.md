# RAKSHA

RAKSHA is an active two-app defence workspace. Citizen hosts MessageGuard and the model-backed VIGIL TorchScript image-privacy runtime. Infra provides deterministic signed telemetry, governance, dry-run containment, a read-only console and an Attack Lab of clearly labelled simulated attack scenarios that the console can trigger and re-run. Both apps now serve the integrated [Phosphor frontend](frontend/README.md) as their default UI, while their Citizen and Infrastructure backend interfaces remain available. The shared Python gateway injects scoped tokens and maps the frontend API to active endpoints. Real-world accuracy, recall, false-positive rate and privacy efficacy remain UNMEASURED.

## Start and stop

One action starts the whole application — preflight, both app processes, both
console origins, and a readiness wait before the prompt returns:

```bash
./start.sh              # start; re-running it reports the live stack instead of doubling it
./start.sh --check      # preflight only: interpreter, imports, credentials by name, free ports
./start.sh --status     # what is running, on which port, and where the logs are
./start.sh --restart    # stop, then start again
./stop.sh               # stop only the processes start.sh recorded
```

On Windows use `start.bat` and `stop.bat`. They call the same engine
([tools/launch_apps.py](tools/launch_apps.py)) as the shell scripts, so the two
platforms cannot drift; `make start`, `make stop`, `make status` and
`make restart` wrap the same flags, while `make run` keeps the pair in the
foreground of your terminal.

The start needs no database, no broker and no Node process: the audit ledger is
in-process and each app serves the built console from the committed static
export. It starts no model run, no eval pass and no Commander call — the
deterministic runtime stays deterministic and VIGIL stays idle until an image is
submitted to the Citizen app. Startup state (pids, ports, log paths) is scratch
under `.raksha/`, which is git-ignored; `stop` re-checks that each recorded pid
still runs the expected app on the expected port before signalling it, and
refuses anything it did not start.

## Active surfaces

- [Presentation demo script](PRESENTATION_DEMO_SCRIPT.md) is the one-page runbook: start, what to click, what to expect, stop, and the fallbacks.
- [Presentation talking points](PRESENTATION_TALKING_POINTS.md) splits that runbook across five speakers, with handoffs, per-scenario lines to say and a Q&A map.
- [Project concepts guide](PROJECT_CONCEPTS_GUIDE.md) is the learning document: the contract, the pipeline, each organ's actual rule, governance, the ledger, both demos, and five hands-on exercises.
- [Status](docs/STATUS.md) describes the active runtime and its honesty limits.
- [Frontend integration](frontend/README.md) documents the new static build, routing and gateway.
- [Gateway package](packages/frontend/README.md) documents the shared serving layer.
- [Evaluations](EVALS.md) are generated from the one active results file.
- [Release summary](summary.md) records the current architecture and command surface.
- [VIGIL runtime](packages/vigil/README.md) documents the Citizen-mounted privacy engine.
- [Retired code note](archive/provenance/RETIRED.md) explains the purge boundary.
- [Tools](tools/README.md) lists the active gates and runners.

## Commands

Run `make ci` for the full local gate suite, `make frontend-build` after changing frontend source, `make frontend-check` and `make frontend-smoke` for the integration gates (which re-derive the Attack Lab's simulated scenarios against the detector registry), `make hospital-smoke` for the fake-hospital exercise proof, and `make eval-generate` after changing measurement inputs. Run `make vigil-tests`, `make vigil-smoke` and `make run` for the dedicated VIGIL proof paths and the two-app launcher.

No live containment action, Commander inference, network capture or real-world efficacy claim is part of this workspace. VIGIL modifies pixels and reports local artifact metrics; it does not claim deepfake prevention, modern face-recognition defeat or an anonymity guarantee.
