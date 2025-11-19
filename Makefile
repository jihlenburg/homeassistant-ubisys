.PHONY: ci fmt lint type typecheck test

ci:
	bash scripts/run_ci_local.sh

fmt:
	bash scripts/run_ci_local.sh --fix

# The following targets assume .venv and tooling are already installed.
# Run `make ci` once to bootstrap.

lint:
	. .venv/bin/activate && \
	black --check . && \
	isort --check-only . && \
	flake8 .

typecheck:
	. .venv/bin/activate && mypy

# Alias for convenience
type: typecheck

test:
	. .venv/bin/activate && pytest -q --cov=custom_components/ubisys --cov-report=term-missing
