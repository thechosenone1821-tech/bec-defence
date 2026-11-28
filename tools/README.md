# Tools

Active gates and runners:

- [launch_apps.py](launch_apps.py) starts exactly the Citizen and Infra processes.
  Plain run is attached (Ctrl+C stops both); `--check` runs the startup preflight
  (interpreter, imports, credentials by name, free ports, static bundle),
  `--detach` starts both apps in the background, waits for readiness, prints the
  URLs and records the pids in `.raksha/launcher.json`; `--status` reports that
  stack and `--stop` signals only those recorded pids after re-checking that each
  one still runs the expected module on the expected port. `--restart` does both.
  It starts no database (the audit ledger is in-process) and executes no model run,
  eval or Commander call. `../start.sh`, `../stop.sh`, `../start.bat` and
  `../stop.bat` are thin wrappers around these flags for one-action use.
- [run_phase4_pytest.py](run_phase4_pytest.py) and [run_phase4_node_tests.py](run_phase4_node_tests.py) run the active Python and browser suites with the runtime import policy.
- [run_vigil_tests.py](run_vigil_tests.py) and [run_vigil_smoke.py](run_vigil_smoke.py) prove the VIGIL runtime and Citizen-mounted HTTP workflow.
- [run_infra_smoke.py](run_infra_smoke.py) proves the deterministic Infra HTTP surface and the read-only simulated-scenario catalogue at `/api/infra/scenarios`; [run_hospital_demo_smoke.py](run_hospital_demo_smoke.py) proves the functional fake-hospital attack series stays isolated, ledger-verified and dry-run.
- [check_frontend_integration.py](check_frontend_integration.py) proves the served Phosphor bundle statically: routes, gateway paths, auth boundaries, the committed build digest, and that both the Red Team replay and the Attack Lab script still match the detector registry step by step (labels, per-run id tokens, payload keys, declared versus actual `detect(event)` outcome, organ coverage). [run_frontend_smoke.py](run_frontend_smoke.py) boots both apps on free ports and repeats that over real HTTP, including every simulated scenario through the gateway ingest paths and the state view afterwards.
- [check_vigil_assets.py](check_vigil_assets.py) verifies committed weight hashes, sizes and active candidate order.
- [check_code_purge.py](check_code_purge.py) rejects retired identifiers in source-controlled text files.
- [check_boot_manifest.py](check_boot_manifest.py) proves the two boot manifests and active VIGIL route.
- [check_no_live_executor.py](check_no_live_executor.py) isolates model imports and rejects live-action/Commander clients.
- [check_eval_drift.py](check_eval_drift.py), [check_claims_ledger.py](check_claims_ledger.py) and [check_local_links.py](check_local_links.py) prove generated docs, claims and links.
- `check_phase*.py` modules are active acceptance gates for contracts, Citizen, MessageGuard, Infra and the unified release.

The [Makefile](../Makefile) is the canonical command surface. Real-world privacy efficacy remains UNMEASURED.

The integrated [Phosphor frontend](../frontend/README.md) is the default UI. Legacy frontend compatibility routes are retained as recoverable fallbacks; backend APIs are unchanged.
