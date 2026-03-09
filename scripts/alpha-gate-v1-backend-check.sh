#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"

cd "${BACKEND_DIR}"

PYTHON_BIN="${BACKEND_PYTHON_BIN:-.venv-gate/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

echo "[alpha-gate-backend] python=${PYTHON_BIN}"
PYTHONUTF8=1 PYTHONPATH=. "${PYTHON_BIN}" -m pytest -q -p no:cacheprovider \
  tests/test_alpha_allowlist_auth.py \
  tests/test_posthog_events.py \
  tests/test_cors_preflight_alpha_gate.py \
  tests/test_feature_flags.py \
  tests/test_notification_api.py \
  tests/test_notification_service.py \
  tests/test_notification_multichannel_runtime.py \
  tests/test_push_subscription_api.py \
  tests/test_push_sli_runtime.py \
  tests/test_health_endpoint.py \
  tests/test_auth_token_endpoint_security.py \
  tests/security/test_bola_matrix.py \
  tests/test_endpoint_authorization_matrix_policy.py \
  tests/test_api_inventory_contract.py

cd "${ROOT_DIR}"
API_INVENTORY_AUTO_WRITE=1 SECURITY_GATE_PROFILE=fast bash backend/scripts/security-gate.sh

echo "[alpha-gate-backend] pass"
