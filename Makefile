PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)

.PHONY: install test eval eval-generate run ci-checks ci links

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) tools/run_phase4_pytest.py
	$(PYTHON) tools/run_phase4_node_tests.py
	$(PYTHON) tools/check_phase3_contracts.py
	$(PYTHON) tools/check_phase4_citizen.py
	$(PYTHON) tools/check_phase5_messageguard.py
	$(PYTHON) tools/check_phase678_integration.py
	$(PYTHON) tools/check_phase910_integration.py
	$(PYTHON) tools/check_frozen_assets.py
	$(PYTHON) -m packages.contracts
	$(PYTHON) tools/check_local_links.py
	$(PYTHON) -m compileall -q apps packages evals tools tests

eval:
	$(PYTHON) tools/check_eval_drift.py

eval-generate:
	$(PYTHON) -m evals.run_evals
	$(PYTHON) tools/check_eval_drift.py

run:
	$(PYTHON) tools/launch_apps.py

ci-checks:
	$(PYTHON) tools/check_eval_drift.py
	$(PYTHON) tools/verify_runtime_ledger.py
	$(PYTHON) tools/check_boot_manifest.py
	$(PYTHON) tools/check_no_secrets.py
	$(PYTHON) tools/check_no_live_executor.py
	$(PYTHON) tools/check_claims_ledger.py
	$(PYTHON) tools/check_phase910_integration.py

links:
	$(PYTHON) tools/check_local_links.py

ci: install test eval ci-checks
