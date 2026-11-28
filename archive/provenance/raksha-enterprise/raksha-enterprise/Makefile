PYTHON ?= python3
DATA   ?= ./data

.PHONY: help seed api raavan evals test ledger-verify clean

help:
	@echo "make seed          - create data dir, sensor key, API tokens, topology"
	@echo "make api           - run the FastAPI bus (uvicorn, port from .env)"
	@echo "make raavan        - run the RAAVAN red-team replay against the local bus"
	@echo "make evals         - regenerate data/evals/{EVALS.md,summary.json}"
	@echo "make test          - run the pytest suite"
	@echo "make ledger-verify - verify the ledger hash chain"
	@echo "make clean         - remove caches and generated state"

seed:
	$(PYTHON) -m raksha.bootstrap

api:
	$(PYTHON) -m uvicorn raksha.bus.app:create_app --factory --host $${RAKSHA_HOST:-127.0.0.1} --port $${RAKSHA_PORT:-8000}

raavan:
	$(PYTHON) -m raksha.raavan.player --bus-url http://$${RAKSHA_HOST:-127.0.0.1}:$${RAKSHA_PORT:-8000}

evals:
	$(PYTHON) tools/run_evals.py --out $(DATA)/evals

test:
	$(PYTHON) -m pytest

ledger-verify:
	$(PYTHON) -m raksha.ledger.cli verify --db $(DATA)/ledger.db

clean:
	rm -rf .pytest_cache raksha_enterprise.egg-info tests/__pycache__ raksha/**/__pycache__
