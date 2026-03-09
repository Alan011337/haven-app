#!/usr/bin/env bash
# Install backend deps with visible progress. Run from repo root or backend.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_DIR}"

PYTHON="${BACKEND_PYTHON_BIN:-}"
if [[ -z "${PYTHON}" ]]; then
  if [[ -x "${BACKEND_DIR}/venv/bin/python" ]]; then
    PYTHON="${BACKEND_DIR}/venv/bin/python"
  elif [[ -x "${BACKEND_DIR}/.venv-gate/bin/python" ]]; then
    PYTHON="${BACKEND_DIR}/.venv-gate/bin/python"
  else
    echo "No venv found. Create one first: python3 -m venv venv" >&2
    exit 1
  fi
fi

echo "[install-deps] Using: ${PYTHON}"
echo "[install-deps] Running pip install (-v for visible progress)..."
PYTHONUNBUFFERED=1 "${PYTHON}" -m pip install --no-cache-dir -v -r requirements.txt
echo "[install-deps] Done."
