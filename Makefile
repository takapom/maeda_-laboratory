.PHONY: lint typecheck unit smoke-test

lint:
	python -m ruff check .

typecheck:
	python -m mypy agent_runner sim_eval controller eval --ignore-missing-imports

unit:
	python -m pytest tests/ -v

smoke-test:
	python -m sim_eval.smoke_test
