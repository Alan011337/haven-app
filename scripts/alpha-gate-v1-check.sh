#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash "${ROOT_DIR}/scripts/alpha-gate-v1-backend-check.sh"
bash "${ROOT_DIR}/scripts/alpha-gate-v1-frontend-check.sh"
if [[ "${ALPHA_GATE_SKIP_CURL:-0}" == "1" ]]; then
  echo "[alpha-gate-v1] skip curl checks (ALPHA_GATE_SKIP_CURL=1)"
else
  bash "${ROOT_DIR}/scripts/alpha-gate-v1-curl-check.sh"
fi

echo "[alpha-gate-v1] all checks passed"
