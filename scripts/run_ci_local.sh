#!/usr/bin/env bash
set -euo pipefail

# Local CI runner for the Ubisys integration
# - Creates/uses .venv
# - Installs dev/test deps
# - Runs black/isort/flake8/mypy and pytest with coverage

VENV_DIR=".venv"

usage() {
  cat <<EOF
Usage: bash scripts/run_ci_local.sh [--fix] [--quiet]

Options:
  --fix   Run black/isort in fix mode (not --check)
  --quiet Reduce installer output (no progress bars)

Steps executed:
  1) Create/activate .venv
  2) Install dev/test dependencies
  3) Lint/Type: black, isort, flake8, mypy
  4) Tests: pytest (with pinned Home Assistant) + coverage

Tip: To reuse the environment, re-run without deleting .venv.
EOF
}

FIX_MODE=false
QUIET=false
for arg in "$@"; do
  case "$arg" in
    --fix) FIX_MODE=true ;;
    --quiet) QUIET=true ;;
    -h|--help) usage; exit 0 ;;
  esac
done

# Prefer uv for speed; fall back to stdlib venv + pip
has_uv() { command -v uv >/dev/null 2>&1; }

# Pick a Python interpreter and ensure venv exists with a supported version
pick_python() {
  local candidates=(python3.11 python3.12 python3)
  for cmd in "${candidates[@]}"; do
    if command -v "$cmd" >/dev/null 2>&1; then
      "$cmd" - <<'PY' >/dev/null 2>&1 || continue
import sys
maj, minor = sys.version_info[:2]
print(f"{maj}.{minor}")
PY
      echo "$cmd"
      return 0
    fi
  done
  return 1
}

ensure_venv() {
  local desired_py
  desired_py=$(pick_python) || { echo "[ci] No suitable python found (need python3.11+ recommended, or python3)"; exit 1; }
  if [[ -d "${VENV_DIR}" ]]; then
    local vpy
    vpy="${VENV_DIR}/bin/python"
    if [[ ! -x "$vpy" ]]; then
      echo "[ci] Existing venv missing python, recreating"
      rm -rf "${VENV_DIR}"
    else
      local ver
      ver=$("$vpy" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)
      case "$ver" in
        3.11*|3.12*|3.13*|3.10*) : ;; # ok
        *) echo "[ci] Existing venv uses unsupported Python ${ver}, recreating"; rm -rf "${VENV_DIR}";;
      esac
    fi
  fi
  if [[ ! -d "${VENV_DIR}" ]]; then
    if has_uv; then
      echo "[ci] Creating virtualenv in ${VENV_DIR} with uv (python=${desired_py})"
      uv venv "${VENV_DIR}" -p "${desired_py}"
    else
      echo "[ci] Creating virtualenv in ${VENV_DIR} using ${desired_py}"
      "$desired_py" -m venv "${VENV_DIR}"
    fi
  fi
  # shellcheck disable=SC1090
  source "${VENV_DIR}/bin/activate"
}

ensure_venv

# Select installer within the venv
if has_uv; then
  INSTALLER=(uv pip)
  echo "[ci] Using uv for installs"
else
  INSTALLER=(pip)
  echo "[ci] Using pip for installs"
  echo "[ci] Upgrading pip"
  python -m pip install --upgrade pip
fi

PYVER=$("${VENV_DIR}/bin/python" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)

# Choose an HA version compatible with the Python in .venv
case "$PYVER" in
  3.11*|3.12*|3.13*)
    HA_VERSION="2024.1.6"
    ;;
  3.10*)
    HA_VERSION="2023.6.4"
    ;;
  *)
    echo "[ci] Python ${PYVER} is not supported for running tests."
    echo "[ci] Please create a venv with Python 3.11 (recommended) or 3.10, then rerun:"
    echo "[ci]   python3.11 -m venv .venv && source .venv/bin/activate && make ci"
    echo "[ci] Proceeding with lint/type only (no test deps)."
    HA_VERSION=""
    ;;
esac

# Install all development dependencies (lint, type, test) from pyproject.toml
if [[ -n "${HA_VERSION}" ]]; then
  echo "[ci] Installing dev dependencies (Python=${PYVER}, HA=${HA_VERSION})"
  echo "[ci] Using pyproject.toml [dependency-groups] (PEP 735)"
  if $QUIET; then
    "${INSTALLER[@]}" install -q --group dev
  else
    PIP_PROGRESS_BAR=on "${INSTALLER[@]}" install --group dev
  fi
else
  # Install only lint and typecheck (skip test group which needs compatible Python)
  echo "[ci] Installing lint/typecheck only (test skipped for Python ${PYVER})"
  if $QUIET; then
    "${INSTALLER[@]}" install -q --group lint --group typecheck
  else
    PIP_PROGRESS_BAR=on "${INSTALLER[@]}" install --group lint --group typecheck
  fi
fi

echo "[ci] Running linters and type checks"
if ${FIX_MODE}; then
  black .
  isort .
else
  black --check .
  isort --check-only .
fi
flake8 .
mypy

if [[ -n "${HA_VERSION}" ]]; then
  echo "[ci] Running tests with coverage"
  # pytest.ini handles PYTHONPATH and test discovery
  pytest --cov=custom_components/ubisys --cov-report=term-missing
else
  echo "[ci] Tests skipped (unsupported Python ${PYVER})"
fi

echo "[ci] Done ✅"
