PYTHON ?= python3

.PHONY: lint typecheck unit smoke-test

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy agent_runner sim_eval controller eval --ignore-missing-imports

unit:
	$(PYTHON) -m pytest tests/ -v

smoke-test:
	$(PYTHON) -m sim_eval.smoke_test
