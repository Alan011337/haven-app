#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"

cd "${FRONTEND_DIR}"

echo "[alpha-gate-frontend] typecheck"
npm run typecheck

echo "[alpha-gate-frontend] lint:console-error"
npm run lint:console-error

echo "[alpha-gate-frontend] lint:route-collision"
npm run lint:route-collision

if [[ "${ALPHA_GATE_RUN_FULL_ESLINT:-0}" == "1" ]]; then
  echo "[alpha-gate-frontend] full eslint (can be slow)"
  LINT_TIMEOUT_MS="${LINT_TIMEOUT_MS:-420000}" npm run lint
else
  echo "[alpha-gate-frontend] full eslint skipped (set ALPHA_GATE_RUN_FULL_ESLINT=1 to enable)"
fi

echo "[alpha-gate-frontend] pass"
