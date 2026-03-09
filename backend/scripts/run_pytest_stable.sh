#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -n "${BACKEND_PYTHON_BIN:-}" ]]; then
  BACKEND_PYTHON="${BACKEND_PYTHON_BIN}"
elif [[ -x "${BACKEND_DIR}/.venv-gate/bin/python" ]]; then
  BACKEND_PYTHON="${BACKEND_DIR}/.venv-gate/bin/python"
elif [[ -x "${BACKEND_DIR}/venv/bin/python" ]]; then
  BACKEND_PYTHON="${BACKEND_DIR}/venv/bin/python"
else
  BACKEND_PYTHON="python3"
fi

if ! command -v "${BACKEND_PYTHON}" >/dev/null 2>&1 && [[ "${BACKEND_PYTHON}" != */* ]]; then
  echo "[run_pytest_stable] fail: python not found: ${BACKEND_PYTHON}"
  exit 1
fi

export PYTHONUTF8="${PYTHONUTF8:-1}"
export PYTHONPATH="${BACKEND_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

RUN_TIMEOUT_SECONDS="${RUN_TIMEOUT_SECONDS:-1800}"
RUN_HEARTBEAT_SECONDS="${RUN_HEARTBEAT_SECONDS:-45}"
PYTEST_ARGS_DEFAULT="${PYTEST_ARGS_DEFAULT:--q -p no:cacheprovider}"

run_step() {
  local step_name="$1"
  shift
  "${BACKEND_PYTHON}" "${BACKEND_DIR}/scripts/run_with_timeout.py" \
    --timeout-seconds "${RUN_TIMEOUT_SECONDS}" \
    --heartbeat-seconds "${RUN_HEARTBEAT_SECONDS}" \
    --step-name "${step_name}" \
    -- "${BACKEND_PYTHON}" -m pytest "$@"
}

cd "${BACKEND_DIR}"

echo "[run_pytest_stable] python=${BACKEND_PYTHON}"
echo "[run_pytest_stable] timeout=${RUN_TIMEOUT_SECONDS}s heartbeat=${RUN_HEARTBEAT_SECONDS}s"
echo "[run_pytest_stable] phase 1: unit+contract (excluding slow)"
run_step "pytest_unit_contract" ${PYTEST_ARGS_DEFAULT} -m "unit or contract" --maxfail=2

echo "[run_pytest_stable] phase 2: integration (excluding slow)"
run_step "pytest_integration" ${PYTEST_ARGS_DEFAULT} -m "integration and not slow" --maxfail=2

if [[ "${RUN_SLOW_TESTS:-0}" == "1" ]]; then
  echo "[run_pytest_stable] phase 3: slow"
  run_step "pytest_slow" ${PYTEST_ARGS_DEFAULT} -m "slow" --maxfail=1
else
  echo "[run_pytest_stable] phase 3: slow skipped (set RUN_SLOW_TESTS=1 to enable)"
fi
