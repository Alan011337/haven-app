#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${BACKEND_DIR}"

# So Python loads backend/annotated_doc.py first (avoids FastAPI import hang in some envs)
export PYTHONPATH="${BACKEND_DIR}:${PYTHONPATH:-}"

# UTF-8 mode: 避免載入 site-packages 時因路徑/編碼造成卡住（macOS 上常見）
export PYTHONUTF8=1

# Prefer venv so uvicorn and deps are available (avoid "uvicorn: command not found")
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
if [[ "${SKIP_WORKTREE_MATERIALIZATION_CHECK:-0}" != "1" ]]; then
  MATERIALIZATION_PATHS=(
    "backend/app/main.py"
    "backend/app/services/ai_router.py"
    "backend/app/services/notification.py"
    "backend/scripts/run_uvicorn.py"
    "backend/scripts/run_uvicorn_worker.py"
  )
  if [[ "${ALLOW_DATALESS_WORKTREE:-1}" == "1" ]]; then
    "${PYTHON}" ../scripts/check-worktree-materialization.py \
      --root "${BACKEND_DIR}/.." \
      --summary-path /tmp/haven-worktree-materialization-dev-summary.json \
      --allow-dataless \
      "${MATERIALIZATION_PATHS[@]}"
  else
    "${PYTHON}" ../scripts/check-worktree-materialization.py \
      --root "${BACKEND_DIR}/.." \
      --summary-path /tmp/haven-worktree-materialization-dev-summary.json \
      "${MATERIALIZATION_PATHS[@]}"
  fi
fi
export PYTHONUNBUFFERED=1
# Default RELOAD=0: StatReload's child can hang on FastAPI import on some macOS envs;
# worker subprocess (run_uvicorn_worker.py) loads app once and serves without reload.
# Set RELOAD=1 for auto-reload (edit code then manually restart if worker hangs).
export RELOAD="${RELOAD:-0}"
exec "${PYTHON}" scripts/run_uvicorn.py
