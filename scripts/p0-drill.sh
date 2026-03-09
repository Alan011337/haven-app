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

"${PYTHON_BIN}" scripts/run_p0_drills.py
"${PYTHON_BIN}" scripts/validate_security_evidence.py --kind p0-drill --contract-mode strict
"${PYTHON_BIN}" scripts/validate_security_evidence.py --kind data-rights-fire-drill --contract-mode strict
"${PYTHON_BIN}" scripts/validate_security_evidence.py --kind billing-fire-drill --contract-mode strict
