#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}/backend"
if [[ -x "venv/bin/python" ]]; then
  PYTHON_BIN="venv/bin/python"
else
  PYTHON_BIN="python3"
fi

"${PYTHON_BIN}" scripts/check_env.py
./scripts/security-gate.sh
"${PYTHON_BIN}" scripts/check_slo_burn_rate_gate.py --allow-missing-url

"${PYTHON_BIN}" -m pytest -q -p no:cacheprovider

cd "${ROOT_DIR}/frontend"
npm run check:env
TYPECHECK_TIMEOUT_MS="${TYPECHECK_TIMEOUT_MS:-180000}" npm run typecheck
