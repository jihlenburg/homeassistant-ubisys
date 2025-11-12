#!/usr/bin/env bash
set -euo pipefail

# Local CI runner for the Ubisys integration
# - Creates/uses .venv
# - Installs dev/test deps
# - Runs black/isort/flake8/mypy and pytest with coverage

PYTHON_BIN="python3"
VENV_DIR=".venv"

usage() {
  cat <<EOF
Usage: bash scripts/run_ci_local.sh [--fix]

Options:
  --fix   Run black/isort in fix mode (not --check)

Steps executed:
  1) Create/activate .venv
  2) Install dev/test dependencies
  3) Lint/Type: black, isort, flake8, mypy
  4) Tests: pytest (with HA ${HA_VERSION}) + coverage

Tip: To reuse the environment, re-run without deleting .venv.
EOF
}

FIX_MODE=false
if [[ "${1:-}" == "--fix" ]]; then
  FIX_MODE=true
elif [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

echo "[ci] Using Python: ${PYTHON_BIN}"
command -v "${PYTHON_BIN}" >/dev/null 2>&1 || { echo "[ci] python3 not found" >&2; exit 1; }

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "[ci] Creating virtualenv in ${VENV_DIR}"
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip >/dev/null

echo "[ci] Installing lint/type tooling"
pip install -q black isort flake8 mypy

PYVER=$(. ${VENV_DIR}/bin/python - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)

# Choose an HA version compatible with the Python in .venv
if [[ "$PYVER" == 3.11* || "$PYVER" == 3.12* || "$PYVER" == 3.13* ]]; then
  HA_VERSION="2024.1.6"
else
  # Fallback for Python 3.10 environments
  HA_VERSION="2023.6.4"
fi

echo "[ci] Installing test deps (Python=${PYVER}, HA=${HA_VERSION})"
pip install -q \
  homeassistant==${HA_VERSION} \
  pytest pytest-asyncio pytest-cov \
  pytest-homeassistant-custom-component

echo "[ci] Running linters and type checks"
if ${FIX_MODE}; then
  black custom_components/ubisys custom_zha_quirks
  isort .
else
  black --check custom_components/ubisys custom_zha_quirks
  isort --check-only .
fi
flake8 custom_components/ubisys
mypy

echo "[ci] Running tests"
pytest -q --cov=custom_components/ubisys --cov-report=term-missing

echo "[ci] Done ✅"
