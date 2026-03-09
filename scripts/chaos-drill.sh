#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"

cd "${BACKEND_DIR}"

if [[ -x ".venv-gate/bin/python" ]]; then
  PYTHON_BIN=".venv-gate/bin/python"
elif [[ -x "venv/bin/python" ]]; then
  PYTHON_BIN="venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  PYTHON_BIN="python"
fi

export PYTHONUTF8=1
export PYTHONPATH="${BACKEND_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
export CHAOS_DRILL_ENV="${CHAOS_DRILL_ENV:-local}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///./chaos-drill.db}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-test-key}"
export SECRET_KEY="${SECRET_KEY:-01234567890123456789012345678901}"
export ABUSE_GUARD_STORE_BACKEND="${ABUSE_GUARD_STORE_BACKEND:-memory}"

"${PYTHON_BIN}" scripts/run_chaos_drill_audit.py
"${PYTHON_BIN}" scripts/validate_security_evidence.py --kind chaos-drill --contract-mode strict
