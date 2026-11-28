PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)

.PHONY: install start stop status restart test eval eval-generate run frontend-install frontend-build frontend-check frontend-smoke infra-smoke hospital-smoke vigil-tests vigil-smoke ci-checks ci links

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) tools/run_phase4_pytest.py
	$(PYTHON) tools/run_phase4_node_tests.py
	$(PYTHON) tools/check_phase3_contracts.py
	$(PYTHON) tools/check_phase4_citizen.py
	$(PYTHON) tools/check_phase5_messageguard.py
	$(PYTHON) tools/check_phase678_integration.py
	$(PYTHON) tools/check_code_purge.py
	$(PYTHON) tools/check_vigil_assets.py
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

start:
	./start.sh

stop:
	./stop.sh

status:
	./start.sh --status

restart:
	./start.sh --restart

frontend-install:
	cd frontend && npm ci --no-audit --no-fund

frontend-build:
	cd frontend && npm run build

frontend-check:
	$(PYTHON) tools/check_frontend_integration.py

frontend-smoke:
	$(PYTHON) tools/run_frontend_smoke.py

infra-smoke:
	$(PYTHON) tools/run_infra_smoke.py

hospital-smoke:
	$(PYTHON) tools/run_hospital_demo_smoke.py

vigil-tests:
	$(PYTHON) tools/run_vigil_tests.py

vigil-smoke:
	$(PYTHON) tools/run_vigil_smoke.py

ci-checks:
	$(PYTHON) tools/check_eval_drift.py
	$(PYTHON) tools/verify_runtime_ledger.py
	$(PYTHON) tools/check_boot_manifest.py
	$(PYTHON) tools/check_no_secrets.py
	$(PYTHON) tools/check_no_live_executor.py
	$(PYTHON) tools/check_vigil_assets.py
	$(PYTHON) tools/check_code_purge.py
	$(PYTHON) tools/check_claims_ledger.py
	$(PYTHON) tools/check_frontend_integration.py
	$(PYTHON) tools/run_frontend_smoke.py
	$(PYTHON) tools/check_phase910_integration.py
	$(PYTHON) tools/run_infra_smoke.py
	$(PYTHON) tools/run_hospital_demo_smoke.py
	$(PYTHON) tools/run_vigil_tests.py
	$(PYTHON) tools/run_vigil_smoke.py

links:
	$(PYTHON) tools/check_local_links.py

ci: install test eval ci-checks
