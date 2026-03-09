#!/usr/bin/env bash
# Create venv with Python 3.12 (via uv) and run backend. Use when Python 3.13
# hangs on FastAPI/pip import. Requires: uv (curl -LsSf https://astral.sh/uv/install.sh | sh)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_DIR}"

PYTHON_BIN_OVERRIDE="${BACKEND_PYTHON_BIN:-}"
if [[ -n "${PYTHON_BIN_OVERRIDE}" ]]; then
  if [[ ! -x "${PYTHON_BIN_OVERRIDE}" ]]; then
    echo "[run-dev-python312] BACKEND_PYTHON_BIN is not executable: ${PYTHON_BIN_OVERRIDE}" >&2
    exit 1
  fi
  PYTHON_BIN="${PYTHON_BIN_OVERRIDE}"
else
  if [[ -x "${HOME}/.local/bin/uv" ]]; then
    export PATH="${HOME}/.local/bin:${PATH}"
  fi
  if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
  fi

  VENV312="${BACKEND_DIR}/venv312"
  if [[ ! -d "${VENV312}" ]]; then
    echo "[run-dev-python312] Creating venv with Python 3.12..."
    uv venv "${VENV312}" --python 3.12
    echo "[run-dev-python312] Installing dependencies..."
    uv pip install -r requirements.txt --python "${VENV312}/bin/python"
    echo "[run-dev-python312] Done. venv at ${VENV312}"
  fi
  PYTHON_BIN="${VENV312}/bin/python"
fi

export BACKEND_PYTHON_BIN="${PYTHON_BIN}"
# Safer dev defaults on iCloud-synced workspace: memory store; RELOAD=0; worker mode with load-time timeout.
export ABUSE_GUARD_STORE_BACKEND="${ABUSE_GUARD_STORE_BACKEND:-memory}"
export RELOAD="${RELOAD:-0}"
export RUN_APP_IN_MAIN_PROCESS="${RUN_APP_IN_MAIN_PROCESS:-0}"
exec "${SCRIPT_DIR}/run-dev.sh"
