.PHONY: ci fmt lint typecheck test

ci:
	bash scripts/run_ci_local.sh

fmt:
	bash scripts/run_ci_local.sh --fix

# The following targets assume .venv and tooling are already installed.
# Run `make ci` once to bootstrap.

lint:
	. .venv/bin/activate && black --check custom_components/ubisys custom_zha_quirks && isort --check-only . && flake8 custom_components/ubisys

typecheck:
	. .venv/bin/activate && mypy

test:
	. .venv/bin/activate && pytest -q --cov=custom_components/ubisys --cov-report=term-missing

