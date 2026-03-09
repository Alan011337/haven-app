#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}/backend"

if [[ -x "venv/bin/python" ]]; then
  PYTHON_BIN="venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  PYTHON_BIN="python"
fi

# Default to local sqlite for deterministic offline runs.
# Caller can override by exporting DATABASE_URL explicitly.
export DATABASE_URL="${DATABASE_URL:-sqlite:///./billing-reconciliation-local.db}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-test-key}"
export SECRET_KEY="${SECRET_KEY:-01234567890123456789012345678901}"
export ABUSE_GUARD_STORE_BACKEND="${ABUSE_GUARD_STORE_BACKEND:-memory}"

"${PYTHON_BIN}" scripts/run_billing_reconciliation_audit.py
"${PYTHON_BIN}" scripts/validate_security_evidence.py --kind billing-reconciliation --contract-mode strict
