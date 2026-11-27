# Tools

Active gates and runners:

- [launch_apps.py](launch_apps.py) starts exactly the Citizen and Infra processes.
- [run_phase4_pytest.py](run_phase4_pytest.py) and [run_phase4_node_tests.py](run_phase4_node_tests.py) run the active Python and browser suites with the runtime import policy.
- [run_vigil_tests.py](run_vigil_tests.py) and [run_vigil_smoke.py](run_vigil_smoke.py) prove the VIGIL runtime and Citizen-mounted HTTP workflow.
- [run_infra_smoke.py](run_infra_smoke.py) proves the deterministic Infra HTTP surface; [run_hospital_demo_smoke.py](run_hospital_demo_smoke.py) proves the functional fake-hospital attack series stays isolated, ledger-verified and dry-run.
- [check_vigil_assets.py](check_vigil_assets.py) verifies committed weight hashes, sizes and active candidate order.
- [check_code_purge.py](check_code_purge.py) rejects retired identifiers in source-controlled text files.
- [check_boot_manifest.py](check_boot_manifest.py) proves the two boot manifests and active VIGIL route.
- [check_no_live_executor.py](check_no_live_executor.py) isolates model imports and rejects live-action/Commander clients.
- [check_eval_drift.py](check_eval_drift.py), [check_claims_ledger.py](check_claims_ledger.py) and [check_local_links.py](check_local_links.py) prove generated docs, claims and links.
- `check_phase*.py` modules are active acceptance gates for contracts, Citizen, MessageGuard, Infra and the unified release.

The [Makefile](../Makefile) is the canonical command surface. Real-world privacy efficacy remains UNMEASURED.
