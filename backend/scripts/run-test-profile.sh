#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_DIR}"

PROFILE="${1:-${TEST_PROFILE:-fast}}"
PY_BIN="${BACKEND_PYTHON_BIN:-.venv-gate/bin/python}"
PYTEST_TIMEOUT_SECONDS="${PYTEST_TIMEOUT_SECONDS:-1200}"
if [[ "${PY_BIN}" != */* ]]; then
  PY_BIN="$(command -v "${PY_BIN}")"
fi
if [[ ! -x "${PY_BIN}" ]]; then
  echo "[run-test-profile] fail: python not executable: ${PY_BIN}" >&2
  exit 1
fi

export PYTHONUTF8=1
export PYTHONPATH="${BACKEND_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

echo "[run-test-profile] profile=${PROFILE}"
echo "[run-test-profile] python=${PY_BIN}"
echo "[run-test-profile] pytest_timeout_seconds=${PYTEST_TIMEOUT_SECONDS}"

if [[ -z "${TEST_PROFILE_SLA_ENFORCED+x}" ]]; then
  if [[ "${CI:-}" == "true" || "${CI:-}" == "1" ]]; then
    TEST_PROFILE_SLA_ENFORCED="1"
  else
    TEST_PROFILE_SLA_ENFORCED="0"
  fi
fi

resolve_profile_sla_seconds() {
  case "${PROFILE}" in
    smoke) echo "${TEST_PROFILE_SLA_SMOKE_SECONDS:-240}" ;;
    fast) echo "${TEST_PROFILE_SLA_FAST_SECONDS:-480}" ;;
    runtime) echo "${TEST_PROFILE_SLA_RUNTIME_SECONDS:-600}" ;;
    safety) echo "${TEST_PROFILE_SLA_SAFETY_SECONDS:-720}" ;;
    contract) echo "${TEST_PROFILE_SLA_CONTRACT_SECONDS:-720}" ;;
    unit) echo "${TEST_PROFILE_SLA_UNIT_SECONDS:-1200}" ;;
    full) echo "${TEST_PROFILE_SLA_FULL_SECONDS:-3600}" ;;
    *) echo "${TEST_PROFILE_SLA_DEFAULT_SECONDS:-1200}" ;;
  esac
}

PROFILE_SLA_SECONDS="$(resolve_profile_sla_seconds)"
echo "[run-test-profile] profile_sla_seconds=${PROFILE_SLA_SECONDS}"
echo "[run-test-profile] test_profile_sla_enforced=${TEST_PROFILE_SLA_ENFORCED}"
PROFILE_STARTED_AT="$(date +%s)"

run_pytest_guarded() {
  "${PY_BIN}" scripts/pytest_guard.py --timeout-seconds "${PYTEST_TIMEOUT_SECONDS}" -- "$@"
}

case "${PROFILE}" in
  smoke)
    ruff check . --select F821,F841,E9
    run_pytest_guarded -q -p no:cacheprovider \
      tests/test_health_endpoint.py \
      tests/test_ai_router_runtime.py \
      tests/test_notification_outbox.py \
      tests/test_security_gate_contract.py
    ;;
  fast)
    ruff check .
    run_pytest_guarded -q -p no:cacheprovider \
      tests/test_health_endpoint.py \
      tests/test_notification_outbox.py \
      tests/test_billing_edge_policy_contract.py \
      tests/test_store_enforcement_hooks_contract.py \
      tests/test_event_tracking_privacy_contract.py \
      tests/test_feature_flag_governance_contract.py \
      tests/test_frontend_idempotency_helper_contract.py \
      tests/test_frontend_timeline_loadmore_guard_contract.py \
      tests/test_pytest_guard_script.py \
      tests/test_socket_manager_backpressure.py
    ;;
  runtime)
    ruff check .
    run_pytest_guarded -q -p no:cacheprovider \
      tests/test_health_endpoint.py \
      tests/test_structured_logging_contract.py \
      tests/test_ai_router_metrics.py \
      tests/test_timeline_runtime_metrics.py \
      tests/test_timeline_runtime_alert_gate_script.py \
      tests/test_notification_outbox_health_snapshot_script.py \
      tests/test_router_registration_contract.py \
      tests/test_oncall_runtime_snapshot_script.py
    ;;
  unit)
    ruff check . --select F821,F841,E9
    run_pytest_guarded -q -p no:cacheprovider -m "unit and not slow"
    ;;
  contract)
    ruff check .
    run_pytest_guarded -q -p no:cacheprovider -m "contract and not slow"
    ;;
  safety)
    ruff check .
    run_pytest_guarded -q -p no:cacheprovider \
      tests/security/test_bola_matrix.py \
      tests/security/test_bola_subject_matrix.py \
      tests/test_notification_authorization_matrix.py \
      tests/test_billing_authorization_matrix.py \
      tests/test_billing_webhook_security.py \
      tests/test_endpoint_authorization_matrix_policy.py \
      tests/test_api_inventory_contract.py
    ;;
  full)
    ruff check .
    run_pytest_guarded -q -p no:cacheprovider
    ;;
  *)
    echo "[run-test-profile] fail: unsupported profile '${PROFILE}'" >&2
    echo "[run-test-profile] supported: smoke | fast | runtime | unit | contract | safety | full" >&2
    exit 1
    ;;
esac

echo "[run-test-profile] result=pass profile=${PROFILE}"
PROFILE_ENDED_AT="$(date +%s)"
PROFILE_DURATION_SECONDS="$(( PROFILE_ENDED_AT - PROFILE_STARTED_AT ))"
echo "[run-test-profile] duration_seconds=${PROFILE_DURATION_SECONDS}"
if [[ "${TEST_PROFILE_SLA_ENFORCED}" == "1" && "${PROFILE_DURATION_SECONDS}" -gt "${PROFILE_SLA_SECONDS}" ]]; then
  echo "[run-test-profile] fail: profile duration exceeded SLA (${PROFILE_DURATION_SECONDS}s > ${PROFILE_SLA_SECONDS}s)" >&2
  exit 1
fi
