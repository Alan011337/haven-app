#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${BACKEND_DIR}"

if [[ -n "${BACKEND_PYTHON_BIN:-}" ]] && [[ -x "${BACKEND_PYTHON_BIN}" ]]; then
  PYTHON="${BACKEND_PYTHON_BIN}"
elif [[ -x "${BACKEND_DIR}/.venv-gate/bin/python" ]]; then
  PYTHON="${BACKEND_DIR}/.venv-gate/bin/python"
elif [[ -x "${BACKEND_DIR}/venv/bin/python" ]]; then
  PYTHON="${BACKEND_DIR}/venv/bin/python"
else
  PYTHON="python3"
fi

"${PYTHON}" scripts/check_env.py
exec "${PYTHON}" -m uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
