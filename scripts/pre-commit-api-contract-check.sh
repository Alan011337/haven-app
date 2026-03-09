#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"

cd "${BACKEND_DIR}"
export PYTHONUTF8=1
export PYTHONPATH="${BACKEND_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

PYTHON_BIN="${PYTHON_BIN:-.venv-gate/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

echo "[pre-commit-api-contract] check backend contract snapshot"
"${PYTHON_BIN}" scripts/check_api_contract_snapshot.py

echo "[pre-commit-api-contract] check backend contract source-of-truth"
"${PYTHON_BIN}" scripts/check_api_contract_sot.py \
  --inventory "${ROOT_DIR}/docs/security/api-inventory.json" \
  --require-api-prefix

echo "[pre-commit-api-contract] check write-idempotency coverage"
"${PYTHON_BIN}" scripts/check_write_idempotency_coverage.py

echo "[pre-commit-api-contract] check idempotency normalization contract"
"${PYTHON_BIN}" scripts/check_idempotency_normalization_contract.py

echo "[pre-commit-api-contract] check frontend generated contract types"
cd "${FRONTEND_DIR}"
node scripts/generate-api-contract-types.mjs --check

echo "[pre-commit-api-contract] pass"
