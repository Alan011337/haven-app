#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

echo "[dev-doctor] start"

echo "[dev-doctor] materialization check"
python3 scripts/check-worktree-materialization.py --root "${ROOT_DIR}" \
  --summary-path /tmp/haven-worktree-materialization-summary.json

echo "[dev-doctor] backend env check"
PYTHONUTF8=1 PYTHONPATH="${ROOT_DIR}/backend" \
  "${ROOT_DIR}/backend/.venv-gate/bin/python" "${ROOT_DIR}/backend/scripts/check_env.py"

if command -v npm >/dev/null 2>&1; then
  echo "[dev-doctor] frontend env check"
  (cd "${ROOT_DIR}/frontend" && npm run -s check:env)
else
  echo "[dev-doctor] skip frontend env check (npm not installed)"
fi

echo "[dev-doctor] done"

