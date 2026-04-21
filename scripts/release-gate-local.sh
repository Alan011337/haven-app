#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
BACKEND_PYTHONPATH="${BACKEND_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
source "${SCRIPT_DIR}/gate-common.sh"
source "${SCRIPT_DIR}/release-gate-env.sh"

can_bootstrap_python() {
  local candidate="$1"
  gate_python_can_bootstrap \
    "${candidate}" \
    "${BACKEND_PYTHONPATH}" \
    "import signal; signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError())); signal.alarm(8); import fastapi; import pydantic_settings; import sqlmodel.orm.session; import openai; signal.alarm(0)"
}

if [[ -n "${BACKEND_PYTHON_BIN:-}" ]]; then
  if [[ "${BACKEND_PYTHON_BIN}" == */* ]]; then
    if [[ ! -x "${BACKEND_PYTHON_BIN}" ]]; then
      echo "[release-gate-local] fail: BACKEND_PYTHON_BIN is not executable: ${BACKEND_PYTHON_BIN}"
      exit 1
    fi
  elif ! command -v "${BACKEND_PYTHON_BIN}" >/dev/null 2>&1; then
    echo "[release-gate-local] fail: BACKEND_PYTHON_BIN command not found: ${BACKEND_PYTHON_BIN}"
    exit 1
  fi
  if [[ "${RELEASE_GATE_SKIP_BACKEND_BOOTSTRAP_PREFLIGHT:-0}" != "1" ]]; then
    if ! can_bootstrap_python "${BACKEND_PYTHON_BIN}"; then
      echo "[release-gate-local] fail: BACKEND_PYTHON_BIN failed bootstrap preflight."
      echo "[release-gate-local] hint: PYTHONUTF8=1 PYTHONPATH=. ${BACKEND_PYTHON_BIN} -c \"import fastapi; import pydantic_settings; import sqlmodel.orm.session; import openai\""
      exit 1
    fi
  fi
  BACKEND_PYTHON="${BACKEND_PYTHON_BIN}"
else
  for candidate in "${BACKEND_DIR}/.venv-gate/bin/python" "${BACKEND_DIR}/venv/bin/python" "python3"; do
    if [[ "${candidate}" == */* ]] && [[ ! -x "${candidate}" ]]; then
      continue
    fi
    if [[ "${candidate}" != */* ]] && ! command -v "${candidate}" >/dev/null 2>&1; then
      continue
    fi
    if [[ "${RELEASE_GATE_SKIP_BACKEND_BOOTSTRAP_PREFLIGHT:-0}" == "1" ]]; then
      BACKEND_PYTHON="${candidate}"
      break
    fi
    if can_bootstrap_python "${candidate}"; then
      BACKEND_PYTHON="${candidate}"
      break
    fi
    echo "[release-gate-local] skip python candidate (preflight failed): ${candidate}"
  done
fi

if [[ -z "${BACKEND_PYTHON:-}" ]]; then
  echo "[release-gate-local] fail: no usable backend python interpreter found."
  exit 1
fi

echo "[release-gate-local] backend python: ${BACKEND_PYTHON}"
echo "[release-gate-local] backend bootstrap: PYTHONUTF8=1, PYTHONPATH includes ${BACKEND_DIR}"
CURRENT_BRANCH="$(gate_detect_current_branch "${ROOT_DIR}")"
if gate_is_protected_release_branch "${CURRENT_BRANCH}"; then
  RELEASE_GATE_PROTECTED_BRANCH="1"
else
  RELEASE_GATE_PROTECTED_BRANCH="0"
fi
echo "[release-gate-local] git branch: ${CURRENT_BRANCH}"
echo "[release-gate-local] protected branch mode: ${RELEASE_GATE_PROTECTED_BRANCH}"
if [[ -z "${RELEASE_GATE_STRICT_MODE+x}" ]]; then
  RELEASE_GATE_STRICT_MODE="$(release_gate_resolve_strict_mode "${CI:-}" "${RELEASE_GATE_PROTECTED_BRANCH}")"
fi
echo "[release-gate-local] strict mode: ${RELEASE_GATE_STRICT_MODE}"

if [[ -z "${RELEASE_GATE_ENV:-}" ]]; then
  RELEASE_GATE_ENV="${ENV:-local}"
fi
RELEASE_GATE_ENV="$(release_gate_normalize_env_mode "${RELEASE_GATE_ENV}")"
echo "[release-gate-local] env mode: ${RELEASE_GATE_ENV}"

release_gate_component_kind() {
  local default_kind="$1"
  if [[ "${RELEASE_GATE_ENV}" == "alpha" || "${RELEASE_GATE_ENV}" == "prod" ]]; then
    echo "required"
    return
  fi
  echo "${default_kind}"
}
RELEASE_GATE_STEP_TIMEOUT_SECONDS="${RELEASE_GATE_STEP_TIMEOUT_SECONDS:-900}"
RELEASE_GATE_HEARTBEAT_SECONDS="${RELEASE_GATE_HEARTBEAT_SECONDS:-45}"

run_python_gate_step() {
  local step_name="$1"
  shift
  "${BACKEND_PYTHON}" "${BACKEND_DIR}/scripts/run_with_timeout.py" \
    --timeout-seconds "${RELEASE_GATE_STEP_TIMEOUT_SECONDS}" \
    --heartbeat-seconds "${RELEASE_GATE_HEARTBEAT_SECONDS}" \
    --step-name "${step_name}" \
    -- "${BACKEND_PYTHON}" "$@"
}

run_shell_gate_step() {
  local step_name="$1"
  shift
  "${BACKEND_PYTHON}" "${BACKEND_DIR}/scripts/run_with_timeout.py" \
    --timeout-seconds "${RELEASE_GATE_STEP_TIMEOUT_SECONDS}" \
    --heartbeat-seconds "${RELEASE_GATE_HEARTBEAT_SECONDS}" \
    --step-name "${step_name}" \
    -- "$@"
}

release_gate_default_by_strict_mode() {
  local strict_default="$1"
  local relaxed_default="$2"
  gate_default_by_strict_mode "${RELEASE_GATE_STRICT_MODE}" "${strict_default}" "${relaxed_default}"
}

run_local_backend_contract_preflight_steps() {
  run_python_gate_step "check_release_gate_override_contract_local" scripts/check_release_gate_override_contract.py \
    --summary-path /tmp/release-gate-override-summary-local.json
  run_python_gate_step "check_gate_consistency_contract_local" scripts/check_gate_consistency_contract.py
  run_python_gate_step "check_deploy_source_of_truth_local" scripts/check_deploy_source_of_truth.py
  run_python_gate_step "check_file_hygiene_contract_local" scripts/check_file_hygiene_contract.py
  run_python_gate_step "check_frontend_security_headers_contract_local" scripts/check_frontend_security_headers_contract.py
  run_python_gate_step "check_event_registry_contract_local" scripts/check_event_registry_contract.py
  run_python_gate_step "check_env_secret_manifest_contract_local" scripts/check_env_secret_manifest_contract.py
  if [[ "${RELEASE_GATE_ENV}" == "alpha" || "${RELEASE_GATE_ENV}" == "prod" ]]; then
    run_python_gate_step "check_settings_contract_local" scripts/check_settings_contract.py
    return
  fi

  set +e
  run_python_gate_step "check_settings_contract_local_warn" scripts/check_settings_contract.py
  SETTINGS_CONTRACT_EXIT_CODE=$?
  set -e
  if [[ "${SETTINGS_CONTRACT_EXIT_CODE}" -ne 0 ]]; then
    echo "[release-gate-local] warn: settings contract check failed in dev mode (non-blocking)"
  fi
}

run_local_api_contract_alignment_steps() {
  set +e
  "${BACKEND_PYTHON}" scripts/run_openapi_inventory_snapshot.py --output "${OPENAPI_SNAPSHOT_PATH}"
  OPENAPI_SNAPSHOT_EXIT_CODE=$?
  set -e
  if [[ "${OPENAPI_SNAPSHOT_EXIT_CODE}" -ne 0 ]]; then
    if [[ "${RELEASE_GATE_REQUIRE_OPENAPI_SNAPSHOT:-0}" == "1" ]]; then
      echo "[release-gate-local] fail: openapi snapshot export failed and strict mode enabled"
      exit "${OPENAPI_SNAPSHOT_EXIT_CODE}"
    fi
    echo "[release-gate-local] openapi snapshot export degraded (non-blocking)"
  fi

  "${BACKEND_PYTHON}" scripts/check_api_contract_sot.py \
    --inventory "${ROOT_DIR}/docs/security/api-inventory.json" \
    --require-api-prefix \
    --summary-path "${API_CONTRACT_SOT_SUMMARY_PATH}"

  "${BACKEND_PYTHON}" scripts/check_write_idempotency_coverage.py \
    --inventory "${ROOT_DIR}/docs/security/api-inventory.json" \
    --summary-path "${IDEMPOTENCY_COVERAGE_SUMMARY_PATH}"

  "${BACKEND_PYTHON}" scripts/check_idempotency_contract_convergence.py \
    --summary-path "${IDEMPOTENCY_CONVERGENCE_SUMMARY_PATH}"
}

WORKTREE_MATERIALIZATION_SUMMARY_PATH="/tmp/worktree-materialization-summary-local.json"
rm -f "${WORKTREE_MATERIALIZATION_SUMMARY_PATH}"
if [[ -z "${RELEASE_GATE_ALLOW_DATALESS_WORKTREE+x}" ]]; then
  if [[ "${CI:-}" == "true" || "${CI:-}" == "1" || "${RELEASE_GATE_PROTECTED_BRANCH}" == "1" ]]; then
    RELEASE_GATE_ALLOW_DATALESS_WORKTREE="0"
  else
    RELEASE_GATE_ALLOW_DATALESS_WORKTREE="1"
  fi
fi
if [[ "${RELEASE_GATE_ALLOW_DATALESS_WORKTREE}" == "1" ]]; then
  echo "[release-gate-local] worktree materialization gate: allow dataless (local override)"
  run_python_gate_step "check_worktree_materialization_allow_dataless" "${ROOT_DIR}/scripts/check-worktree-materialization.py" \
    --root "${ROOT_DIR}" \
    --allow-dataless \
    --summary-path "${WORKTREE_MATERIALIZATION_SUMMARY_PATH}"
else
  echo "[release-gate-local] worktree materialization gate: fail-closed"
  run_python_gate_step "check_worktree_materialization_fail_closed" "${ROOT_DIR}/scripts/check-worktree-materialization.py" \
    --root "${ROOT_DIR}" \
    --summary-path "${WORKTREE_MATERIALIZATION_SUMMARY_PATH}"
fi

if [[ -z "${RELEASE_GATE_AUTO_REFRESH_EVIDENCE+x}" ]]; then
  RELEASE_GATE_AUTO_REFRESH_EVIDENCE="0"
fi

if [[ "${RELEASE_GATE_AUTO_REFRESH_EVIDENCE}" == "1" ]]; then
  echo "[release-gate-local] auto refresh security evidence: enabled"
  if [[ -x "${ROOT_DIR}/scripts/refresh-security-evidence-local.sh" ]]; then
    run_shell_gate_step "refresh_security_evidence_local" bash "${ROOT_DIR}/scripts/refresh-security-evidence-local.sh"
  else
    echo "[release-gate-local] fail: missing executable scripts/refresh-security-evidence-local.sh"
    exit 1
  fi
else
  echo "[release-gate-local] auto refresh security evidence: disabled"
fi

cd "${BACKEND_DIR}"
export PYTHONUTF8=1
export PYTHONPATH="${BACKEND_PYTHONPATH}"

if [[ "${RELEASE_GATE_SKIP_COMPILEALL:-0}" == "1" ]]; then
  echo "[release-gate-local] skip compileall (RELEASE_GATE_SKIP_COMPILEALL=1)"
else
  "${BACKEND_PYTHON}" -m compileall -q app
fi
run_local_backend_contract_preflight_steps
if [[ -n "${RELEASE_GATE_BACKEND_TEST_PROFILE:-}" ]]; then
  echo "[release-gate-local] backend preflight profile: ${RELEASE_GATE_BACKEND_TEST_PROFILE}"
  BACKEND_PYTHON_BIN="${BACKEND_PYTHON}" TEST_PROFILE="${RELEASE_GATE_BACKEND_TEST_PROFILE}" ./scripts/run-test-profile.sh
fi
if [[ -z "${RELEASE_GATE_SECURITY_PROFILE+x}" ]]; then
  if [[ "${CI:-}" == "true" || "${CI:-}" == "1" || "${RELEASE_GATE_PROTECTED_BRANCH}" == "1" ]]; then
    RELEASE_GATE_SECURITY_PROFILE="full"
  else
    RELEASE_GATE_SECURITY_PROFILE="fast"
  fi
fi
API_INVENTORY_AUTO_WRITE="${API_INVENTORY_AUTO_WRITE:-1}"
echo "[release-gate-local] backend security profile: ${RELEASE_GATE_SECURITY_PROFILE}"
echo "[release-gate-local] api inventory auto-write: ${API_INVENTORY_AUTO_WRITE}"
if [[ "${RELEASE_GATE_SKIP_SECURITY_GATE:-0}" == "1" ]]; then
  echo "[release-gate-local] skip backend security gate (RELEASE_GATE_SKIP_SECURITY_GATE=1)"
else
  run_shell_gate_step "security_gate_local" env \
    PYTHON_BIN="${BACKEND_PYTHON}" \
    SECURITY_GATE_PROFILE="${RELEASE_GATE_SECURITY_PROFILE}" \
    API_INVENTORY_AUTO_WRITE="${API_INVENTORY_AUTO_WRITE}" \
    ./scripts/security-gate.sh
fi

API_CONTRACT_SOT_SUMMARY_PATH="/tmp/api-contract-sot-summary-local.json"
IDEMPOTENCY_COVERAGE_SUMMARY_PATH="/tmp/idempotency-coverage-summary-local.json"
IDEMPOTENCY_CONVERGENCE_SUMMARY_PATH="/tmp/idempotency-contract-convergence-summary-local.json"
BOLA_COVERAGE_SUMMARY_PATH="/tmp/bola-coverage-summary-local.json"
RATE_LIMIT_POLICY_SUMMARY_PATH="/tmp/rate-limit-policy-summary-local.json"
OPENAPI_SNAPSHOT_PATH="/tmp/openapi-contract-snapshot-local.json"
rm -f \
  "${OPENAPI_SNAPSHOT_PATH}" \
  "${API_CONTRACT_SOT_SUMMARY_PATH}" \
  "${IDEMPOTENCY_COVERAGE_SUMMARY_PATH}" \
  "${IDEMPOTENCY_CONVERGENCE_SUMMARY_PATH}" \
  "${BOLA_COVERAGE_SUMMARY_PATH}" \
  "${RATE_LIMIT_POLICY_SUMMARY_PATH}"
run_local_api_contract_alignment_steps

API_CONTRACT_SNAPSHOT_SUMMARY_PATH="/tmp/api-contract-snapshot-summary-local.json"
rm -f "${API_CONTRACT_SNAPSHOT_SUMMARY_PATH}"
if "${BACKEND_PYTHON}" scripts/check_api_contract_snapshot.py; then
  "${BACKEND_PYTHON}" - <<'PY'
import json
from pathlib import Path

summary = {
    "artifact_kind": "api-contract-snapshot-local",
    "schema_version": "v1",
    "result": "pass",
    "reasons": [],
}
Path("/tmp/api-contract-snapshot-summary-local.json").write_text(
    json.dumps(summary, ensure_ascii=True, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
else
  echo "[release-gate-local] fail: api contract snapshot drift detected"
  exit 1
fi

"${BACKEND_PYTHON}" scripts/check_bola_coverage_from_inventory.py \
  --inventory "${ROOT_DIR}/docs/security/api-inventory.json" \
  --summary-path "${BOLA_COVERAGE_SUMMARY_PATH}"

"${BACKEND_PYTHON}" scripts/check_rate_limit_policy_contract.py \
  --source "${BACKEND_DIR}/app/services/rate_limit_scope.py" \
  --summary-path "${RATE_LIMIT_POLICY_SUMMARY_PATH}"
if [[ -z "${RELEASE_GATE_ALLOW_MISSING_SLO_URL+x}" ]]; then
  RELEASE_GATE_ALLOW_MISSING_SLO_URL="0"
fi
if [[ "${RELEASE_GATE_ALLOW_MISSING_SLO_URL}" == "1" ]]; then
  echo "[release-gate-local] slo burn-rate gate: allow missing URL"
  SLO_BURN_RATE_SUMMARY_PATH="/tmp/slo-burn-rate-summary-local.json"
  rm -f "${SLO_BURN_RATE_SUMMARY_PATH}"
  "${BACKEND_PYTHON}" scripts/check_slo_burn_rate_gate.py \
    --allow-missing-url \
    --summary-path "${SLO_BURN_RATE_SUMMARY_PATH}"
else
  if [[ -z "${SLO_GATE_HEALTH_SLO_URL:-}" && -z "${SLO_GATE_HEALTH_SLO_FILE:-}" && "${RELEASE_GATE_PROTECTED_BRANCH}" != "1" && "${CI:-}" != "true" && "${CI:-}" != "1" ]]; then
    echo "[release-gate-local] slo burn-rate gate: no URL/file configured; generating local CUJ fixture"
    bash "${ROOT_DIR}/scripts/generate-cuj-synthetic-evidence-local.sh"
    export SLO_GATE_HEALTH_SLO_FILE="/tmp/cuj-slo-payload-local.json"
    echo "[release-gate-local] slo burn-rate gate: using payload file ${SLO_GATE_HEALTH_SLO_FILE}"
  fi
  if [[ -z "${RELEASE_GATE_REQUIRE_SLO_SUFFICIENT_DATA+x}" ]]; then
    if [[ "${RELEASE_GATE_PROTECTED_BRANCH}" == "1" ]]; then
      RELEASE_GATE_REQUIRE_SLO_SUFFICIENT_DATA="1"
    else
      RELEASE_GATE_REQUIRE_SLO_SUFFICIENT_DATA="0"
    fi
  fi
  echo "[release-gate-local] slo burn-rate gate: fail-closed (missing URL not allowed)"
  if [[ "${RELEASE_GATE_REQUIRE_SLO_SUFFICIENT_DATA}" == "1" ]]; then
    echo "[release-gate-local] slo burn-rate gate: require sufficient data"
    SLO_BURN_RATE_SUMMARY_PATH="/tmp/slo-burn-rate-summary-local.json"
    rm -f "${SLO_BURN_RATE_SUMMARY_PATH}"
    "${BACKEND_PYTHON}" scripts/check_slo_burn_rate_gate.py \
      --require-sufficient-data \
      --summary-path "${SLO_BURN_RATE_SUMMARY_PATH}"
  else
    SLO_BURN_RATE_SUMMARY_PATH="/tmp/slo-burn-rate-summary-local.json"
    rm -f "${SLO_BURN_RATE_SUMMARY_PATH}"
    "${BACKEND_PYTHON}" scripts/check_slo_burn_rate_gate.py \
      --summary-path "${SLO_BURN_RATE_SUMMARY_PATH}"
  fi
fi
if [[ -z "${RELEASE_GATE_ALLOW_MISSING_ERROR_BUDGET_STATUS+x}" ]]; then
  RELEASE_GATE_ALLOW_MISSING_ERROR_BUDGET_STATUS="$(
    release_gate_default_by_strict_mode "0" "1"
  )"
fi
if [[ "${RELEASE_GATE_ALLOW_MISSING_ERROR_BUDGET_STATUS}" == "1" ]]; then
  echo "[release-gate-local] error budget gate: allow missing status"
  "${BACKEND_PYTHON}" scripts/check_error_budget_freeze_gate.py --allow-missing-status
else
  echo "[release-gate-local] error budget gate: fail-closed"
  "${BACKEND_PYTHON}" scripts/check_error_budget_freeze_gate.py
fi
SERVICE_TIER_SUMMARY_PATH="/tmp/service-tier-gate-summary-local.json"
rm -f "${SERVICE_TIER_SUMMARY_PATH}"
if [[ -z "${RELEASE_GATE_ALLOW_MISSING_SERVICE_TIER_STATUS+x}" ]]; then
  RELEASE_GATE_ALLOW_MISSING_SERVICE_TIER_STATUS="$(
    release_gate_default_by_strict_mode "0" "1"
  )"
fi
if [[ "${RELEASE_GATE_ALLOW_MISSING_SERVICE_TIER_STATUS}" == "1" ]]; then
  echo "[release-gate-local] service tier gate: allow missing status"
  "${BACKEND_PYTHON}" scripts/check_service_tier_budget_gate.py \
    --allow-missing-status \
    --summary-path "${SERVICE_TIER_SUMMARY_PATH}"
else
  echo "[release-gate-local] service tier gate: fail-closed"
  "${BACKEND_PYTHON}" scripts/check_service_tier_budget_gate.py \
    --summary-path "${SERVICE_TIER_SUMMARY_PATH}"
fi
SERVICE_TIER_SUMMARY_PATH="${SERVICE_TIER_SUMMARY_PATH}" \
"${BACKEND_PYTHON}" - <<'PY'
import json
import os
from pathlib import Path

summary_file = Path(os.environ["SERVICE_TIER_SUMMARY_PATH"])
if not summary_file.exists():
    print("[release-gate-local] service tier summary")
    print("  result: unavailable")
    print("  reason: summary_file_missing")
    raise SystemExit(0)

try:
    payload = json.loads(summary_file.read_text(encoding="utf-8"))
except Exception:
    print("[release-gate-local] service tier summary")
    print("  result: unavailable")
    print("  reason: summary_parse_error")
    raise SystemExit(0)

meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
reasons = payload.get("reasons") or []
print("[release-gate-local] service tier summary")
print(f"  result: {payload.get('result', 'unknown')}")
print(f"  target_tier: {meta.get('target_tier', 'unknown')}")
print(f"  release_intent: {meta.get('release_intent', 'unknown')}")
print(
    "  release_freeze: "
    + ("yes" if meta.get("release_freeze") else "no")
)
print(
    "  tier_error_budget_freeze_enforced: "
    + ("yes" if meta.get("tier_error_budget_freeze_enforced") else "no")
)
print(f"  reasons: {', '.join(str(reason) for reason in reasons) if reasons else 'none'}")
PY
if [[ "${RELEASE_GATE_ALLOW_MISSING_LAUNCH_SIGNOFF:-0}" == "1" ]]; then
  echo "[release-gate-local] launch signoff gate: override enabled (allow missing artifact)"
  "${BACKEND_PYTHON}" scripts/check_launch_signoff_gate.py \
    --allow-missing-artifact \
    --require-ready \
    --max-age-days "${LAUNCH_SIGNOFF_MAX_AGE_DAYS:-14}"
else
  echo "[release-gate-local] launch signoff gate: fail-closed"
  "${BACKEND_PYTHON}" scripts/check_launch_signoff_gate.py \
    --require-ready \
    --max-age-days "${LAUNCH_SIGNOFF_MAX_AGE_DAYS:-14}"
fi

if [[ "${RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE:-0}" == "1" ]]; then
  echo "[release-gate-local] cuj synthetic evidence gate: override enabled (allow missing evidence)"
  "${BACKEND_PYTHON}" scripts/check_cuj_synthetic_evidence_gate.py \
    --allow-missing-evidence \
    --require-pass \
    --max-age-hours "${CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS:-36}"
else
  echo "[release-gate-local] cuj synthetic evidence gate: fail-closed"
  "${BACKEND_PYTHON}" scripts/check_cuj_synthetic_evidence_gate.py \
    --require-pass \
    --max-age-hours "${CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS:-36}"
fi

AI_QUALITY_EVIDENCE_PATH="/tmp/ai-quality-snapshot-latest.json"
AI_QUALITY_EVIDENCE_SOURCE="${RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE:-local_snapshot}"
AI_QUALITY_FETCH_SUMMARY_PATH="/tmp/ai-quality-snapshot-fetch-summary.json"
AI_QUALITY_GATE_SUMMARY_PATH="/tmp/ai-quality-snapshot-gate-summary-local.json"

rm -f "${AI_QUALITY_FETCH_SUMMARY_PATH}" "${AI_QUALITY_GATE_SUMMARY_PATH}"

if [[ "${AI_QUALITY_EVIDENCE_SOURCE}" == "daily_artifact" ]]; then
  echo "[release-gate-local] ai quality evidence source: daily_artifact"
  rm -f "${AI_QUALITY_EVIDENCE_PATH}"
  fetch_args=(
    "--output" "${AI_QUALITY_EVIDENCE_PATH}"
    "--workflow-file" "${RELEASE_GATE_AI_QUALITY_EVIDENCE_WORKFLOW_FILE:-.github/workflows/ai-quality-snapshot.yml}"
    "--branch" "${RELEASE_GATE_AI_QUALITY_EVIDENCE_BRANCH:-main}"
    "--artifact-name" "${RELEASE_GATE_AI_QUALITY_EVIDENCE_ARTIFACT_NAME:-ai-quality-snapshot}"
    "--artifact-file" "${RELEASE_GATE_AI_QUALITY_EVIDENCE_ARTIFACT_FILE:-docs/security/evidence/ai-quality-snapshot-latest.json}"
    "--summary-path" "${AI_QUALITY_FETCH_SUMMARY_PATH}"
  )
  if [[ -n "${RELEASE_GATE_AI_QUALITY_EVIDENCE_REPO:-}" ]]; then
    fetch_args+=("--repo" "${RELEASE_GATE_AI_QUALITY_EVIDENCE_REPO}")
  fi
  if [[ "${RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE:-0}" == "1" ]]; then
    fetch_args+=("--allow-missing-evidence")
  fi
  "${BACKEND_PYTHON}" scripts/fetch_latest_ai_quality_snapshot_evidence.py "${fetch_args[@]}"
elif [[ "${AI_QUALITY_EVIDENCE_SOURCE}" == "local_snapshot" ]]; then
  echo "[release-gate-local] ai quality evidence source: local_snapshot"
  "${BACKEND_PYTHON}" scripts/run_ai_quality_snapshot.py \
    --allow-missing-current \
    --output "${AI_QUALITY_EVIDENCE_PATH}"
  AI_QUALITY_FETCH_SUMMARY_PATH="${AI_QUALITY_FETCH_SUMMARY_PATH}" \
  AI_QUALITY_EVIDENCE_PATH="${AI_QUALITY_EVIDENCE_PATH}" \
  "${BACKEND_PYTHON}" - <<'PY'
import json
import os
from pathlib import Path

summary_path = Path(os.environ["AI_QUALITY_FETCH_SUMMARY_PATH"])
evidence_path = Path(os.environ["AI_QUALITY_EVIDENCE_PATH"])
payload = {
    "result": "pass",
    "reasons": [],
    "meta": {
        "source": "local_snapshot",
        "output": str(evidence_path),
    },
}
summary_path.write_text(
    json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
else
  echo "[release-gate-local] fail: invalid RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE: ${AI_QUALITY_EVIDENCE_SOURCE}"
  echo "[release-gate-local] hint: supported values are local_snapshot or daily_artifact"
  exit 1
fi

if [[ "${RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE:-0}" == "1" ]]; then
  "${BACKEND_PYTHON}" scripts/check_ai_quality_snapshot_freshness_gate.py \
    --evidence "${AI_QUALITY_EVIDENCE_PATH}" \
    --allow-missing-evidence \
    --max-age-hours "${AI_QUALITY_SNAPSHOT_MAX_AGE_HOURS:-36}" \
    --summary-path "${AI_QUALITY_GATE_SUMMARY_PATH}"
else
  "${BACKEND_PYTHON}" scripts/check_ai_quality_snapshot_freshness_gate.py \
    --evidence "${AI_QUALITY_EVIDENCE_PATH}" \
    --max-age-hours "${AI_QUALITY_SNAPSHOT_MAX_AGE_HOURS:-36}" \
    --summary-path "${AI_QUALITY_GATE_SUMMARY_PATH}"
fi

AI_QUALITY_FETCH_SUMMARY_PATH="${AI_QUALITY_FETCH_SUMMARY_PATH}" \
AI_QUALITY_GATE_SUMMARY_PATH="${AI_QUALITY_GATE_SUMMARY_PATH}" \
"${BACKEND_PYTHON}" - <<'PY'
import json
import os
from pathlib import Path

fetch_path = Path(os.environ["AI_QUALITY_FETCH_SUMMARY_PATH"])
gate_path = Path(os.environ["AI_QUALITY_GATE_SUMMARY_PATH"])

def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}

fetch_payload = _load(fetch_path)
gate_payload = _load(gate_path)
fetch_meta = fetch_payload.get("meta") if isinstance(fetch_payload.get("meta"), dict) else {}
gate_meta = gate_payload.get("meta") if isinstance(gate_payload.get("meta"), dict) else {}

print("[release-gate-local] ai quality summary")
print(f"  source_result: {fetch_payload.get('result', 'unknown')}")
print(f"  source_reason: {', '.join(fetch_payload.get('reasons') or ['none'])}")
print(f"  source_type: {fetch_meta.get('source', 'artifact_fetch')}")
print(f"  gate_result: {gate_payload.get('result', 'unknown')}")
print(f"  evaluation_result: {gate_meta.get('evaluation_result', 'unknown')}")
print(f"  evidence_age_hours: {gate_meta.get('age_hours', 'unknown')}")
PY

AI_RUNTIME_SUMMARY_PATH="/tmp/ai-runtime-gate-summary-local.json"
rm -f "${AI_RUNTIME_SUMMARY_PATH}"
if [[ -z "${RELEASE_GATE_ALLOW_DEGRADED_AI_RUNTIME+x}" ]]; then
  RELEASE_GATE_ALLOW_DEGRADED_AI_RUNTIME="$(
    release_gate_default_by_strict_mode "0" "1"
  )"
fi
if [[ "${RELEASE_GATE_ALLOW_DEGRADED_AI_RUNTIME}" == "1" ]]; then
  "${BACKEND_PYTHON}" scripts/check_ai_runtime_gate.py \
    --snapshot "${AI_QUALITY_EVIDENCE_PATH}" \
    --allow-degraded \
    --summary-path "${AI_RUNTIME_SUMMARY_PATH}"
else
  "${BACKEND_PYTHON}" scripts/check_ai_runtime_gate.py \
    --snapshot "${AI_QUALITY_EVIDENCE_PATH}" \
    --summary-path "${AI_RUNTIME_SUMMARY_PATH}"
fi

AI_ROUTER_RUNTIME_PERSIST_SUMMARY_PATH="/tmp/ai-router-runtime-persist-summary-local.json"
rm -f "${AI_ROUTER_RUNTIME_PERSIST_SUMMARY_PATH}"
AI_ROUTER_RUNTIME_PERSIST_ARGS=(
  "--output" "${AI_ROUTER_RUNTIME_PERSIST_SUMMARY_PATH}"
)
if [[ -n "${SLO_GATE_HEALTH_SLO_FILE:-}" ]]; then
  AI_ROUTER_RUNTIME_PERSIST_ARGS+=("--health-slo-file" "${SLO_GATE_HEALTH_SLO_FILE}")
else
  AI_ROUTER_RUNTIME_PERSIST_ARGS+=("--allow-missing-source")
fi
"${BACKEND_PYTHON}" scripts/run_ai_router_runtime_persist.py "${AI_ROUTER_RUNTIME_PERSIST_ARGS[@]}"

AI_ROUTER_MULTINODE_STRESS_SUMMARY_PATH="/tmp/ai-router-multinode-stress-summary-local.json"
rm -f "${AI_ROUTER_MULTINODE_STRESS_SUMMARY_PATH}"
if [[ "${RELEASE_GATE_RUN_AI_ROUTER_STRESS:-0}" == "1" ]]; then
  "${BACKEND_PYTHON}" scripts/run_ai_router_multinode_stress.py \
    --runs "${RELEASE_GATE_AI_ROUTER_STRESS_RUNS:-2}" \
    --timeout-seconds "${RELEASE_GATE_AI_ROUTER_STRESS_TIMEOUT_SECONDS:-180}" \
    --output "${AI_ROUTER_MULTINODE_STRESS_SUMMARY_PATH}" \
    --allow-failures
else
  "${BACKEND_PYTHON}" - <<'PY'
import json
from pathlib import Path

summary = {
    "artifact_kind": "ai-router-multinode-stress",
    "schema_version": "v1",
    "result": "skipped",
    "reasons": ["disabled_by_flag"],
}
Path("/tmp/ai-router-multinode-stress-summary-local.json").write_text(
    json.dumps(summary, ensure_ascii=True, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
fi

TIMELINE_PERF_SNAPSHOT_PATH="/tmp/timeline-perf-baseline-local.json"
TIMELINE_PERF_SUMMARY_PATH="/tmp/timeline-perf-gate-summary-local.json"
rm -f "${TIMELINE_PERF_SNAPSHOT_PATH}" "${TIMELINE_PERF_SUMMARY_PATH}"
if [[ -z "${RELEASE_GATE_RUN_TIMELINE_PERF+x}" ]]; then
  if [[ "${RELEASE_GATE_STRICT_MODE}" == "1" ]]; then
    RELEASE_GATE_RUN_TIMELINE_PERF="1"
  else
    RELEASE_GATE_RUN_TIMELINE_PERF="0"
  fi
fi
if [[ "${RELEASE_GATE_RUN_TIMELINE_PERF:-0}" == "1" ]]; then
  "${BACKEND_PYTHON}" scripts/run_perf_baseline.py \
    --iterations "${RELEASE_GATE_TIMELINE_PERF_ITERATIONS:-10}" \
    --output "${TIMELINE_PERF_SNAPSHOT_PATH}"
  TIMELINE_PERF_GATE_ARGS=(
    --snapshot "${TIMELINE_PERF_SNAPSHOT_PATH}"
    --timeline-p95-budget-ms "${RELEASE_GATE_TIMELINE_PERF_P95_BUDGET_MS:-300}"
    --summary-path "${TIMELINE_PERF_SUMMARY_PATH}"
  )
  if [[ "${RELEASE_GATE_STRICT_MODE}" == "1" || "${RELEASE_GATE_TIMELINE_FAIL_ON_DEGRADED:-0}" == "1" ]]; then
    TIMELINE_PERF_GATE_ARGS+=(--fail-on-degraded)
  fi
  "${BACKEND_PYTHON}" scripts/check_timeline_perf_baseline_gate.py \
    "${TIMELINE_PERF_GATE_ARGS[@]}"
else
  "${BACKEND_PYTHON}" scripts/check_timeline_perf_baseline_gate.py \
    --snapshot "${TIMELINE_PERF_SNAPSHOT_PATH}" \
    --allow-missing-snapshot \
    --summary-path "${TIMELINE_PERF_SUMMARY_PATH}"
fi

CORE_LOOP_SNAPSHOT_PATH="/tmp/core-loop-snapshot-release-gate-local.json"
CORE_LOOP_SNAPSHOT_SUMMARY_PATH="/tmp/core-loop-snapshot-release-gate-local-summary.json"
CORE_LOOP_SNAPSHOT_FIXTURE_DATABASE_URL="sqlite:////tmp/core-loop-snapshot-release-gate-local.db"
CORE_LOOP_SNAPSHOT_USING_LOCAL_FIXTURE="0"
if [[ -z "${CORE_LOOP_SNAPSHOT_DATABASE_URL+x}" ]]; then
  CORE_LOOP_SNAPSHOT_DATABASE_URL="${CORE_LOOP_SNAPSHOT_FIXTURE_DATABASE_URL}"
  CORE_LOOP_SNAPSHOT_USING_LOCAL_FIXTURE="1"
fi
rm -f "${CORE_LOOP_SNAPSHOT_PATH}" "${CORE_LOOP_SNAPSHOT_SUMMARY_PATH}"
if [[ "${CORE_LOOP_SNAPSHOT_USING_LOCAL_FIXTURE}" == "1" ]]; then
  echo "[release-gate-local] core loop snapshot: seeding local fixture db ${CORE_LOOP_SNAPSHOT_DATABASE_URL}"
  run_python_gate_step "seed_core_loop_fixture_local" scripts/seed_core_loop_fixture.py \
    --database-url "${CORE_LOOP_SNAPSHOT_DATABASE_URL}" \
    --reset
fi
set +e
DATABASE_URL="${CORE_LOOP_SNAPSHOT_DATABASE_URL}" "${BACKEND_PYTHON}" scripts/run_core_loop_snapshot.py \
  --window-days "${CORE_LOOP_SNAPSHOT_WINDOW_DAYS:-1}" \
  --output "${CORE_LOOP_SNAPSHOT_PATH}" \
  --latest-path "${CORE_LOOP_SNAPSHOT_PATH}"
CORE_LOOP_SNAPSHOT_EXIT_CODE=$?
set -e

CORE_LOOP_SNAPSHOT_PATH="${CORE_LOOP_SNAPSHOT_PATH}" \
CORE_LOOP_SNAPSHOT_SUMMARY_PATH="${CORE_LOOP_SNAPSHOT_SUMMARY_PATH}" \
CORE_LOOP_SNAPSHOT_EXIT_CODE="${CORE_LOOP_SNAPSHOT_EXIT_CODE}" \
"${BACKEND_PYTHON}" - <<'PY'
import json
import os
from pathlib import Path

snapshot_path = Path(os.environ["CORE_LOOP_SNAPSHOT_PATH"])
summary_path = Path(os.environ["CORE_LOOP_SNAPSHOT_SUMMARY_PATH"])
command_exit_code = int(os.environ.get("CORE_LOOP_SNAPSHOT_EXIT_CODE", "1"))
summary_payload = {
    "result": "unavailable",
    "reasons": ["summary_file_missing"] if command_exit_code == 0 else ["snapshot_command_failed"],
    "meta": {"command_exit_code": command_exit_code},
}

if command_exit_code == 0 and snapshot_path.exists():
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot = payload.get("snapshot") or {}
        evaluation = payload.get("evaluation") or {}
        metrics = snapshot.get("metrics") or {}
        counts = snapshot.get("counts") or {}
        evaluation_status = str(evaluation.get("status") or "unknown")
        reasons = evaluation.get("reasons") or []
        summary_payload = {
            "result": "pass" if evaluation_status in {"pass", "degraded", "insufficient_data"} else "fail",
            "reasons": list(reasons) if isinstance(reasons, list) else [],
            "meta": {
                "command_exit_code": command_exit_code,
                "evaluation_status": evaluation_status,
                "daily_loop_completion_rate": metrics.get("daily_loop_completion_rate"),
                "dual_reveal_pair_rate": metrics.get("dual_reveal_pair_rate"),
                "active_users_total": counts.get("active_users_total"),
            },
        }
    except Exception:
        summary_payload = {
            "result": "fail",
            "reasons": ["summary_parse_error"],
            "meta": {"command_exit_code": command_exit_code},
        }

summary_path.write_text(
    json.dumps(summary_payload, ensure_ascii=True, sort_keys=True) + "\n",
    encoding="utf-8",
)
print("[release-gate-local] core loop snapshot summary")
print(f"  result: {summary_payload.get('result', 'unknown')}")
meta = summary_payload.get("meta") if isinstance(summary_payload.get("meta"), dict) else {}
print(f"  command_exit_code: {meta.get('command_exit_code', 'unknown')}")
print(f"  evaluation_status: {meta.get('evaluation_status', 'unknown')}")
print(f"  daily_loop_completion_rate: {meta.get('daily_loop_completion_rate', 'unknown')}")
print(f"  dual_reveal_pair_rate: {meta.get('dual_reveal_pair_rate', 'unknown')}")
print(f"  active_users_total: {meta.get('active_users_total', 'unknown')}")
print(
    "  non_blocking_on_degraded: "
    + ("yes" if meta.get("evaluation_status") == "degraded" else "n/a")
)
print(
    "  reasons: "
    + (
        ", ".join(str(reason) for reason in summary_payload.get("reasons") or [])
        if summary_payload.get("reasons")
        else "none"
    )
)
PY

if [[ -z "${RELEASE_GATE_CORE_LOOP_FAIL_ON_DEGRADED+x}" ]]; then
  RELEASE_GATE_CORE_LOOP_FAIL_ON_DEGRADED="$(
    release_gate_default_by_strict_mode "1" "0"
  )"
fi
if [[ "${RELEASE_GATE_CORE_LOOP_FAIL_ON_DEGRADED}" == "1" ]]; then
  CORE_LOOP_SNAPSHOT_SUMMARY_PATH="${CORE_LOOP_SNAPSHOT_SUMMARY_PATH}" \
  "${BACKEND_PYTHON}" - <<'PY'
import json
import os
from pathlib import Path

summary_path = Path(os.environ["CORE_LOOP_SNAPSHOT_SUMMARY_PATH"])
if not summary_path.exists():
    raise SystemExit("[release-gate-local] fail: core loop summary missing in strict mode")
payload = json.loads(summary_path.read_text(encoding="utf-8"))
meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
status = str(meta.get("evaluation_status") or "unknown").strip().lower()
if status in {"degraded", "insufficient_data", "unknown"}:
    raise SystemExit(
        "[release-gate-local] fail: core loop snapshot degraded/insufficient in strict mode "
        f"(evaluation_status={status})"
    )
PY
fi

TIMELINE_RUNTIME_SUMMARY_PATH="/tmp/timeline-runtime-alert-summary-local.json"
rm -f "${TIMELINE_RUNTIME_SUMMARY_PATH}"
if [[ -z "${RELEASE_GATE_ALLOW_MISSING_TIMELINE_RUNTIME_SOURCE+x}" ]]; then
  if [[ "${RELEASE_GATE_ENV}" == "alpha" || "${RELEASE_GATE_ENV}" == "prod" ]]; then
    RELEASE_GATE_ALLOW_MISSING_TIMELINE_RUNTIME_SOURCE="0"
  else
    RELEASE_GATE_ALLOW_MISSING_TIMELINE_RUNTIME_SOURCE="$(
      release_gate_default_by_strict_mode "0" "1"
    )"
  fi
fi
if [[ -z "${RELEASE_GATE_TIMELINE_RUNTIME_FAIL_ON_ALERT+x}" ]]; then
  RELEASE_GATE_TIMELINE_RUNTIME_FAIL_ON_ALERT="$(
    release_gate_default_by_strict_mode "1" "0"
  )"
fi
TIMELINE_GATE_ARGS=(
  "--summary-path" "${TIMELINE_RUNTIME_SUMMARY_PATH}"
  "--min-query-total" "${TIMELINE_RUNTIME_MIN_QUERY_TOTAL:-20}"
  "--max-clamp-ratio-warn" "${TIMELINE_RUNTIME_CLAMP_WARN_RATIO:-0.15}"
  "--max-clamp-ratio-critical" "${TIMELINE_RUNTIME_CLAMP_CRITICAL_RATIO:-0.30}"
)
if [[ -n "${SLO_GATE_HEALTH_SLO_FILE:-}" ]]; then
  TIMELINE_GATE_ARGS+=("--health-slo-file" "${SLO_GATE_HEALTH_SLO_FILE}")
elif [[ -n "${SLO_GATE_HEALTH_SLO_URL:-}" ]]; then
  TIMELINE_GATE_ARGS+=("--health-slo-url" "${SLO_GATE_HEALTH_SLO_URL}")
elif [[ "${RELEASE_GATE_ALLOW_MISSING_TIMELINE_RUNTIME_SOURCE}" == "1" ]]; then
  TIMELINE_GATE_ARGS+=("--allow-missing-payload")
else
  echo "[release-gate-local] fail: timeline runtime gate requires SLO source (set SLO_GATE_HEALTH_SLO_FILE or SLO_GATE_HEALTH_SLO_URL)"
  exit 1
fi
if [[ "${RELEASE_GATE_TIMELINE_RUNTIME_FAIL_ON_ALERT}" == "1" ]]; then
  TIMELINE_GATE_ARGS+=("--fail-on-alert")
fi
"${BACKEND_PYTHON}" scripts/check_timeline_runtime_alert_gate.py "${TIMELINE_GATE_ARGS[@]}"

OUTBOX_HEALTH_SNAPSHOT_PATH="/tmp/notification-outbox-health-snapshot-local.json"
OUTBOX_HEALTH_SUMMARY_PATH="/tmp/notification-outbox-health-summary-local.json"
rm -f "${OUTBOX_HEALTH_SNAPSHOT_PATH}" "${OUTBOX_HEALTH_SUMMARY_PATH}"
if [[ -z "${RELEASE_GATE_ALLOW_MISSING_OUTBOX_HEALTH_SOURCE+x}" ]]; then
  if [[ "${RELEASE_GATE_ENV}" == "alpha" || "${RELEASE_GATE_ENV}" == "prod" ]]; then
    RELEASE_GATE_ALLOW_MISSING_OUTBOX_HEALTH_SOURCE="0"
  else
    RELEASE_GATE_ALLOW_MISSING_OUTBOX_HEALTH_SOURCE="$(
      release_gate_default_by_strict_mode "0" "1"
    )"
  fi
fi
if [[ -n "${RELEASE_GATE_OUTBOX_HEALTH_FILE:-}" ]]; then
  "${BACKEND_PYTHON}" scripts/run_notification_outbox_health_snapshot.py \
    --health-file "${RELEASE_GATE_OUTBOX_HEALTH_FILE}" \
    --output "${OUTBOX_HEALTH_SNAPSHOT_PATH}"
elif [[ -n "${RELEASE_GATE_OUTBOX_HEALTH_URL:-}" ]]; then
  "${BACKEND_PYTHON}" scripts/run_notification_outbox_health_snapshot.py \
    --health-url "${RELEASE_GATE_OUTBOX_HEALTH_URL}" \
    --timeout-seconds "${RELEASE_GATE_OUTBOX_HEALTH_TIMEOUT_SECONDS:-10}" \
    --output "${OUTBOX_HEALTH_SNAPSHOT_PATH}"
elif [[ -f "/tmp/cuj-health-payload-local.json" ]]; then
  "${BACKEND_PYTHON}" scripts/run_notification_outbox_health_snapshot.py \
    --health-file "/tmp/cuj-health-payload-local.json" \
    --output "${OUTBOX_HEALTH_SNAPSHOT_PATH}"
elif [[ "${RELEASE_GATE_ALLOW_MISSING_OUTBOX_HEALTH_SOURCE}" == "1" ]]; then
  "${BACKEND_PYTHON}" - <<'PY'
import json
from pathlib import Path

summary_path = Path("/tmp/notification-outbox-health-summary-local.json")
summary_path.write_text(
    json.dumps(
        {
            "result": "skipped",
            "reasons": ["missing_health_source"],
            "meta": {},
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
print("[release-gate-local] outbox health summary")
print("  result: skipped")
print("  reasons: missing_health_source")
PY
else
  echo "[release-gate-local] fail: outbox health snapshot requires source (set RELEASE_GATE_OUTBOX_HEALTH_FILE or RELEASE_GATE_OUTBOX_HEALTH_URL)"
  exit 1
fi

if [[ -f "${OUTBOX_HEALTH_SNAPSHOT_PATH}" ]]; then
  OUTBOX_HEALTH_SNAPSHOT_PATH="${OUTBOX_HEALTH_SNAPSHOT_PATH}" \
  OUTBOX_HEALTH_SUMMARY_PATH="${OUTBOX_HEALTH_SUMMARY_PATH}" \
  OUTBOX_DEPTH_WARN_THRESHOLD="${OUTBOX_DEPTH_WARN_THRESHOLD:-25}" \
  OUTBOX_DEAD_RATE_WARN_THRESHOLD="${OUTBOX_DEAD_RATE_WARN_THRESHOLD:-0.2}" \
  "${BACKEND_PYTHON}" - <<'PY'
import json
import os
from pathlib import Path

snapshot_path = Path(os.environ["OUTBOX_HEALTH_SNAPSHOT_PATH"])
summary_path = Path(os.environ["OUTBOX_HEALTH_SUMMARY_PATH"])
payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
outbox = payload.get("outbox") if isinstance(payload.get("outbox"), dict) else {}
depth = outbox.get("depth")
dead_rate = outbox.get("dead_letter_rate")

warn_depth = float(os.environ.get("OUTBOX_DEPTH_WARN_THRESHOLD", "25"))
warn_dead_rate = float(os.environ.get("OUTBOX_DEAD_RATE_WARN_THRESHOLD", "0.2"))
reasons: list[str] = []
result = "pass"

if isinstance(depth, (int, float)) and float(depth) > warn_depth:
    reasons.append("outbox_depth_above_warn_threshold")
if isinstance(dead_rate, (int, float)) and float(dead_rate) > warn_dead_rate:
    reasons.append("outbox_dead_letter_rate_above_warn_threshold")
if reasons:
    result = "degraded"

summary = {
    "result": result,
    "reasons": reasons,
    "meta": {
        "depth": depth,
        "dead_letter_rate": dead_rate,
        "warn_depth_threshold": warn_depth,
        "warn_dead_letter_rate_threshold": warn_dead_rate,
    },
}
summary_path.write_text(json.dumps(summary, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
print("[release-gate-local] outbox health summary")
print(f"  result: {result}")
print(f"  depth: {depth}")
print(f"  dead_letter_rate: {dead_rate}")
print(f"  reasons: {', '.join(reasons) if reasons else 'none'}")
PY
fi

OUTBOX_SLO_SUMMARY_PATH="/tmp/outbox-slo-summary-local.json"
rm -f "${OUTBOX_SLO_SUMMARY_PATH}"
if [[ -f "${OUTBOX_HEALTH_SNAPSHOT_PATH}" ]]; then
  OUTBOX_SLO_ARGS=(
    "--snapshot" "${OUTBOX_HEALTH_SNAPSHOT_PATH}"
    "--summary-path" "${OUTBOX_SLO_SUMMARY_PATH}"
    "--warn-depth" "${OUTBOX_DEPTH_WARN_THRESHOLD:-25}"
    "--warn-dead-rate" "${OUTBOX_DEAD_RATE_WARN_THRESHOLD:-0.2}"
  )
  if [[ -z "${RELEASE_GATE_OUTBOX_FAIL_ON_DEGRADED+x}" && "${RELEASE_GATE_STRICT_MODE}" == "1" ]]; then
    RELEASE_GATE_OUTBOX_FAIL_ON_DEGRADED="1"
  fi
  if [[ "${RELEASE_GATE_OUTBOX_FAIL_ON_DEGRADED:-0}" == "1" ]]; then
    OUTBOX_SLO_ARGS+=("--fail-on-degraded")
  fi
  "${BACKEND_PYTHON}" scripts/check_outbox_slo_gate.py "${OUTBOX_SLO_ARGS[@]}"
else
  "${BACKEND_PYTHON}" - <<'PY'
import json
from pathlib import Path

summary_path = Path("/tmp/outbox-slo-summary-local.json")
summary_path.write_text(
    json.dumps(
        {
            "result": "skipped",
            "reasons": ["missing_snapshot"],
            "meta": {},
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
print("[release-gate-local] outbox slo summary")
print("  result: skipped")
print("  reasons: missing_snapshot")
PY
fi

OUTBOX_SELF_HEAL_SUMMARY_PATH="/tmp/outbox-self-heal-summary-local.json"
rm -f "${OUTBOX_SELF_HEAL_SUMMARY_PATH}"
OUTBOX_SELF_HEAL_ARGS=(
  "--output" "${OUTBOX_SELF_HEAL_SUMMARY_PATH}"
)
if [[ -n "${OUTBOX_SELF_HEAL_POLICY_PATH:-}" ]]; then
  OUTBOX_SELF_HEAL_ARGS+=("--policy" "${OUTBOX_SELF_HEAL_POLICY_PATH}")
fi
if [[ -f "${OUTBOX_HEALTH_SNAPSHOT_PATH}" ]]; then
  OUTBOX_SELF_HEAL_ARGS+=("--snapshot" "${OUTBOX_HEALTH_SNAPSHOT_PATH}")
else
  OUTBOX_SELF_HEAL_ARGS+=("--allow-missing-snapshot")
fi
"${BACKEND_PYTHON}" scripts/run_notification_outbox_self_heal.py "${OUTBOX_SELF_HEAL_ARGS[@]}"

OBSERVABILITY_CONTRACT_SUMMARY_PATH="/tmp/observability-contract-summary-local.json"
rm -f "${OBSERVABILITY_CONTRACT_SUMMARY_PATH}"
if [[ -n "${SLO_GATE_HEALTH_SLO_FILE:-}" ]]; then
  OBSERVABILITY_GATE_ARGS=(
    "--payload-file" "${SLO_GATE_HEALTH_SLO_FILE}"
    "--summary-path" "${OBSERVABILITY_CONTRACT_SUMMARY_PATH}"
  )
  if [[ "${SLO_GATE_HEALTH_SLO_FILE}" == "/tmp/cuj-slo-payload-local.json" || "${RELEASE_GATE_OBSERVABILITY_ALLOW_MISSING_KEYS:-0}" == "1" ]]; then
    OBSERVABILITY_GATE_ARGS+=("--allow-missing-keys")
  fi
  "${BACKEND_PYTHON}" scripts/check_observability_payload_contract.py \
    "${OBSERVABILITY_GATE_ARGS[@]}"
elif [[ "${RELEASE_GATE_ALLOW_MISSING_TIMELINE_RUNTIME_SOURCE}" == "1" ]]; then
  "${BACKEND_PYTHON}" - <<'PY'
import json
from pathlib import Path

summary_path = Path("/tmp/observability-contract-summary-local.json")
summary_path.write_text(
    json.dumps(
        {
            "result": "skipped",
            "reasons": ["missing_payload"],
            "meta": {},
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
print("[release-gate-local] observability contract summary")
print("  result: skipped")
print("  reasons: missing_payload")
PY
else
  echo "[release-gate-local] fail: observability contract requires SLO_GATE_HEALTH_SLO_FILE when missing-source override is disabled"
  exit 1
fi

DATA_RIGHTS_FIRE_DRILL_OUTPUT="/tmp/data-rights-fire-drill-local.json"
DATA_RIGHTS_FIRE_DRILL_MD_OUTPUT="/tmp/data-rights-fire-drill-local.md"
rm -f "${DATA_RIGHTS_FIRE_DRILL_OUTPUT}" "${DATA_RIGHTS_FIRE_DRILL_MD_OUTPUT}"
"${BACKEND_PYTHON}" scripts/run_data_rights_fire_drill_snapshot.py \
  --output "${DATA_RIGHTS_FIRE_DRILL_OUTPUT}" \
  --md-output "${DATA_RIGHTS_FIRE_DRILL_MD_OUTPUT}" \
  --access-latency-seconds "${DATA_RIGHTS_ACCESS_LATENCY_SECONDS:-0.5}" \
  --export-latency-seconds "${DATA_RIGHTS_EXPORT_LATENCY_SECONDS:-1.2}" \
  --erase-latency-seconds "${DATA_RIGHTS_ERASE_LATENCY_SECONDS:-1.8}" \
  --result "${DATA_RIGHTS_FIRE_DRILL_RESULT:-pass}" \
  --notes "${DATA_RIGHTS_FIRE_DRILL_NOTES:-automated_local_snapshot}"

GROWTH_COST_SNAPSHOT_PATH="/tmp/growth-cost-snapshot-local.json"
rm -f "${GROWTH_COST_SNAPSHOT_PATH}"
"${BACKEND_PYTHON}" scripts/run_growth_cost_snapshot.py \
  --output "${GROWTH_COST_SNAPSHOT_PATH}" \
  --core-loop-summary "${CORE_LOOP_SNAPSHOT_SUMMARY_PATH}" \
  --outbox-summary "${OUTBOX_HEALTH_SUMMARY_PATH}" \
  --active-couples "${GROWTH_COST_ACTIVE_COUPLES:-0}" \
  --ai-cost-usd "${GROWTH_COST_AI_USD:-0}" \
  --push-cost-usd "${GROWTH_COST_PUSH_USD:-0}" \
  --db-cost-usd "${GROWTH_COST_DB_USD:-0}" \
  --ws-cost-usd "${GROWTH_COST_WS_USD:-0}"

DATA_RETENTION_BUNDLE_SUMMARY_PATH="/tmp/data-retention-bundle-summary-local.json"
rm -f "${DATA_RETENTION_BUNDLE_SUMMARY_PATH}"
if [[ -z "${RELEASE_GATE_DATA_RETENTION_DATABASE_URL:-}" ]]; then
  if [[ "${RELEASE_GATE_ENV}" == "alpha" || "${RELEASE_GATE_ENV}" == "prod" ]]; then
    RELEASE_GATE_DATA_RETENTION_DATABASE_URL="${DATABASE_URL:-}"
  else
    RELEASE_GATE_DATA_RETENTION_DATABASE_URL="sqlite:///./test.db"
  fi
fi
if [[ "${RELEASE_GATE_RUN_DATA_RETENTION_APPLY:-0}" == "1" ]]; then
  DATABASE_URL="${RELEASE_GATE_DATA_RETENTION_DATABASE_URL}" "${BACKEND_PYTHON}" scripts/run_data_retention_bundle.py \
    --apply \
    --allow-job-failures \
    --output "${DATA_RETENTION_BUNDLE_SUMMARY_PATH}"
else
  DATABASE_URL="${RELEASE_GATE_DATA_RETENTION_DATABASE_URL}" "${BACKEND_PYTHON}" scripts/run_data_retention_bundle.py \
    --allow-job-failures \
    --degrade-timeout-in-dry-run \
    --output "${DATA_RETENTION_BUNDLE_SUMMARY_PATH}"
fi

if [[ "${RUN_FULL_BACKEND_PYTEST:-0}" == "1" ]]; then
  echo "[release-gate-local] RUN_FULL_BACKEND_PYTEST=1, running full backend pytest"
  "${BACKEND_PYTHON}" -m pytest -q -p no:cacheprovider
else
  if [[ "${RUN_QUICK_BACKEND_CONTRACT_TESTS:-1}" == "1" ]]; then
    echo "[release-gate-local] running quick backend contract tests"
    QUICK_BACKEND_CONTRACT_LOG_PATH="${QUICK_BACKEND_CONTRACT_LOG_PATH:-/tmp/release-gate-local-quick-backend-tests.log}"
    QUICK_BACKEND_CONTRACT_SUMMARY_PATH="${QUICK_BACKEND_CONTRACT_SUMMARY_PATH:-/tmp/release-gate-local-quick-backend-tests-summary.json}"
    rm -f "${QUICK_BACKEND_CONTRACT_LOG_PATH}" "${QUICK_BACKEND_CONTRACT_SUMMARY_PATH}"
    QUICK_BACKEND_CONTRACT_START_TS="$(date +%s)"
    set +e
    "${BACKEND_PYTHON}" -m unittest \
      tests/test_release_gate_workflow_contract.py \
      tests/test_security_gate_contract.py \
      tests/test_optimization_scripts_contract.py \
      tests/test_frontend_e2e_summary_schema_gate_script.py \
      tests/test_frontend_e2e_summary_contract.py \
      tests/test_frontend_e2e_summary_script.py 2>&1 | tee "${QUICK_BACKEND_CONTRACT_LOG_PATH}"
    QUICK_BACKEND_CONTRACT_EXIT_CODE=${PIPESTATUS[0]}
    set -e
    QUICK_BACKEND_CONTRACT_END_TS="$(date +%s)"
    QUICK_BACKEND_CONTRACT_SUMMARY_PATH="${QUICK_BACKEND_CONTRACT_SUMMARY_PATH}" \
    QUICK_BACKEND_CONTRACT_LOG_PATH="${QUICK_BACKEND_CONTRACT_LOG_PATH}" \
    QUICK_BACKEND_CONTRACT_EXIT_CODE="${QUICK_BACKEND_CONTRACT_EXIT_CODE}" \
    QUICK_BACKEND_CONTRACT_START_TS="${QUICK_BACKEND_CONTRACT_START_TS}" \
    QUICK_BACKEND_CONTRACT_END_TS="${QUICK_BACKEND_CONTRACT_END_TS}" \
    "${BACKEND_PYTHON}" - <<'PY'
import json
import os
import re
from pathlib import Path

summary_path = Path(os.environ["QUICK_BACKEND_CONTRACT_SUMMARY_PATH"])
log_path = Path(os.environ["QUICK_BACKEND_CONTRACT_LOG_PATH"])
exit_code = int(os.environ["QUICK_BACKEND_CONTRACT_EXIT_CODE"])
start_ts = int(os.environ["QUICK_BACKEND_CONTRACT_START_TS"])
end_ts = int(os.environ["QUICK_BACKEND_CONTRACT_END_TS"])

test_count = None
if log_path.exists():
    text = log_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"Ran\s+(\d+)\s+tests?", text)
    if match:
        test_count = int(match.group(1))

payload = {
    "schema_version": "v1",
    "result": "pass" if exit_code == 0 else "fail",
    "exit_code": exit_code,
    "test_count": test_count,
    "duration_seconds": max(0, end_ts - start_ts),
    "log_path": str(log_path),
}
summary_path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")

print("[release-gate-local] quick backend contract summary")
print(f"  result: {payload['result']}")
print(f"  exit_code: {payload['exit_code']}")
print(f"  test_count: {payload['test_count'] if payload['test_count'] is not None else 'unknown'}")
print(f"  duration_seconds: {payload['duration_seconds']}")
print(f"  summary: {summary_path}")
print(f"  log: {log_path}")
PY
    "${BACKEND_PYTHON}" scripts/check_quick_backend_contract_summary.py \
      --summary-file "${QUICK_BACKEND_CONTRACT_SUMMARY_PATH}" \
      --required-schema-version v1
    if [[ "${QUICK_BACKEND_CONTRACT_EXIT_CODE}" -ne 0 ]]; then
      exit "${QUICK_BACKEND_CONTRACT_EXIT_CODE}"
    fi
  else
    echo "[release-gate-local] skip backend tests (set RUN_FULL_BACKEND_PYTEST=1 or RUN_QUICK_BACKEND_CONTRACT_TESTS=1 to enable)"
  fi
fi

FULL_PYTEST_STABILITY_SUMMARY_PATH="/tmp/full-pytest-stability-summary-local.json"
rm -f "${FULL_PYTEST_STABILITY_SUMMARY_PATH}"
if [[ "${RUN_FULL_BACKEND_PYTEST:-0}" == "1" ]]; then
  "${BACKEND_PYTHON}" scripts/run_full_pytest_stability_snapshot.py \
    --run \
    --timeout-seconds "${RELEASE_GATE_FULL_PYTEST_TIMEOUT_SECONDS:-3600}" \
    --pytest-args "-q -p no:cacheprovider" \
    --output "${FULL_PYTEST_STABILITY_SUMMARY_PATH}"
else
  "${BACKEND_PYTHON}" scripts/run_full_pytest_stability_snapshot.py \
    --timeout-seconds "${RELEASE_GATE_FULL_PYTEST_TIMEOUT_SECONDS:-3600}" \
    --pytest-args "-q -p no:cacheprovider" \
    --output "${FULL_PYTEST_STABILITY_SUMMARY_PATH}"
fi

cd "${FRONTEND_DIR}"
npm run check:env
npm run contract:types:check
npm run test:unit
if [[ "${SKIP_FRONTEND_TYPECHECK:-0}" == "1" ]]; then
  echo "[release-gate-local] skip frontend typecheck (SKIP_FRONTEND_TYPECHECK=1)"
else
  CI=1 NEXT_TELEMETRY_DISABLED=1 npm run typecheck
fi
CONTENT_REVIEW_MAX_COPILOT_WEAK="${CONTENT_REVIEW_MAX_COPILOT_WEAK:-180}" npm run seed:cards:review

MOBILE_DIR="${ROOT_DIR}/apps/haven-mobile"
if [[ -d "${MOBILE_DIR}" ]] && [[ -f "${MOBILE_DIR}/package.json" ]]; then
  if [[ "${SKIP_MOBILE_TYPECHECK:-0}" == "1" ]]; then
    echo "[release-gate-local] skip mobile typecheck (SKIP_MOBILE_TYPECHECK=1)"
  else
    echo "[release-gate-local] mobile (Expo) typecheck"
    (cd "${MOBILE_DIR}" && npm run typecheck)
  fi
else
  echo "[release-gate-local] skip mobile (apps/haven-mobile not found)"
fi

E2E_LOG_PATH="${E2E_LOG_PATH:-/tmp/frontend-e2e-local.log}"
E2E_SUMMARY_PATH="${E2E_SUMMARY_PATH:-/tmp/frontend-e2e-local-summary.json}"
STRICT_E2E_REQUIRED="0"
if [[ "${RELEASE_GATE_STRICT_MODE}" == "1" || "${RELEASE_GATE_ENV}" == "alpha" || "${RELEASE_GATE_ENV}" == "prod" ]]; then
  STRICT_E2E_REQUIRED="1"
fi
if [[ "${STRICT_E2E_REQUIRED}" == "1" && -z "${RUN_E2E+x}" ]]; then
  RUN_E2E="1"
  echo "[release-gate-local] strict mode: enabling frontend e2e by default"
fi
if [[ "${STRICT_E2E_REQUIRED}" == "1" && "${RUN_E2E:-0}" != "1" && "${RELEASE_GATE_ALLOW_SKIP_E2E_STRICT:-0}" != "1" ]]; then
  echo "[release-gate-local] fail: strict mode requires frontend e2e."
  echo "[release-gate-local] hint: set RUN_E2E=1"
  echo "[release-gate-local] hint: optionally set E2E_BASE_URL=http://localhost:3000 to target an existing app server"
  echo "[release-gate-local] hint: emergency override RELEASE_GATE_ALLOW_SKIP_E2E_STRICT=1"
  exit 1
fi
if [[ "${RUN_E2E:-0}" == "1" ]]; then
  E2E_NODE_BIN="${RELEASE_GATE_E2E_NODE_BIN:-node}"
  E2E_NODE_SOURCE="default_path"
  CURRENT_PATH_NODE_MAJOR="$(node -p "process.versions.node.split('.')[0]")"
  if [[ -z "${RELEASE_GATE_E2E_NODE_BIN:-}" && "${CURRENT_PATH_NODE_MAJOR}" -gt 22 && -x "/opt/homebrew/opt/node@22/bin/node" ]]; then
    E2E_NODE_BIN="/opt/homebrew/opt/node@22/bin/node"
    E2E_NODE_SOURCE="homebrew_node22_auto"
    echo "[release-gate-local] strict mode: reusing detected Homebrew Node 22 for frontend e2e"
  fi
  E2E_NODE_BIN_DIR="$(dirname "${E2E_NODE_BIN}")"
  E2E_EXEC_PATH="${PATH}"
  if [[ -d "${E2E_NODE_BIN_DIR}" ]]; then
    E2E_EXEC_PATH="${E2E_NODE_BIN_DIR}:${E2E_EXEC_PATH}"
  fi
  NODE_MAJOR="$("${E2E_NODE_BIN}" -p "process.versions.node.split('.')[0]")"
  if [[ "${NODE_MAJOR}" -gt 22 ]]; then
    echo "[release-gate-local] fail: RUN_E2E=1 is not supported on Node ${NODE_MAJOR}."
    echo "[release-gate-local] hint: use Node 20 or 22 for deterministic Playwright + Next runtime."
    echo "[release-gate-local] hint: current node=$("${E2E_NODE_BIN}" -v)"
    exit 1
  fi
  E2E_RUNTIME_MODE="playwright_managed_local_web_server"
  if [[ -n "${E2E_BASE_URL:-}" ]]; then
    E2E_RUNTIME_MODE="external_base_url"
    E2E_BASE_URL_PROBE_PATH="${E2E_BASE_URL_PROBE_PATH:-/}"
    E2E_BASE_URL_PROBE_TIMEOUT_SECONDS="${E2E_BASE_URL_PROBE_TIMEOUT_SECONDS:-20}"
    if [[ "${E2E_BASE_URL_PROBE_PATH}" != /* ]]; then
      E2E_BASE_URL_PROBE_PATH="/${E2E_BASE_URL_PROBE_PATH}"
    fi
    E2E_PROBE_URL="${E2E_BASE_URL%/}${E2E_BASE_URL_PROBE_PATH}"
    echo "[release-gate-local] probing e2e base url: ${E2E_PROBE_URL}"
    if ! curl -fsS --max-time "${E2E_BASE_URL_PROBE_TIMEOUT_SECONDS}" "${E2E_PROBE_URL}" >/dev/null; then
      echo "[release-gate-local] fail: E2E_BASE_URL probe failed."
      echo "[release-gate-local] hint: ensure app server is running and reachable."
      echo "[release-gate-local] hint: set E2E_BASE_URL_PROBE_PATH to a lightweight path (default: /)."
      exit 1
    fi
  else
    echo "[release-gate-local] E2E_BASE_URL not set; relying on Playwright local webServer."
    E2E_WEB_SERVER_COMMAND="${E2E_WEB_SERVER_COMMAND:-NEXT_PUBLIC_API_URL=http://localhost:3000/api ./node_modules/.bin/next dev --webpack -H 127.0.0.1 --port 3000}"
  fi
  E2E_AUTO_INSTALL_BROWSER="${E2E_AUTO_INSTALL_BROWSER:-1}"
  E2E_ALLOW_BROWSER_DOWNLOAD_FAILURE="${E2E_ALLOW_BROWSER_DOWNLOAD_FAILURE:-0}"
  E2E_TIMEOUT_SECONDS="${E2E_TIMEOUT_SECONDS:-420}"
  E2E_TIMEOUT_GRACE_SECONDS="${E2E_TIMEOUT_GRACE_SECONDS:-10}"
  E2E_TEST_TIMEOUT_MS="${E2E_TEST_TIMEOUT_MS:-45000}"
  E2E_BROWSER_CACHE_SOURCE="env_override"
  E2E_PROJECT_BROWSERS_PATH="${FRONTEND_DIR}/.playwright-browsers"
  if [[ -z "${PLAYWRIGHT_BROWSERS_PATH+x}" ]]; then
    if find "${E2E_PROJECT_BROWSERS_PATH}" -maxdepth 1 -type d -name 'chromium-*' | grep -q .; then
      PLAYWRIGHT_BROWSERS_PATH="${E2E_PROJECT_BROWSERS_PATH}"
      E2E_BROWSER_CACHE_SOURCE="frontend_project_cache"
      echo "[release-gate-local] reusing frontend Playwright browser cache: ${PLAYWRIGHT_BROWSERS_PATH}"
    else
      PLAYWRIGHT_BROWSERS_PATH="/tmp/haven-playwright-browsers"
      E2E_BROWSER_CACHE_SOURCE="tmp_release_gate_cache"
    fi
  fi
  echo "[release-gate-local] e2e node source: ${E2E_NODE_SOURCE}"
  echo "[release-gate-local] e2e node binary: ${E2E_NODE_BIN}"
  echo "[release-gate-local] e2e node version: $("${E2E_NODE_BIN}" -v)"
  echo "[release-gate-local] e2e runtime mode: ${E2E_RUNTIME_MODE}"
  echo "[release-gate-local] e2e browser cache source: ${E2E_BROWSER_CACHE_SOURCE}"
  echo "[release-gate-local] running e2e against ${E2E_BASE_URL:-http://localhost:3000}"
  if [[ -n "${E2E_WEB_SERVER_COMMAND:-}" ]]; then
    echo "[release-gate-local] e2e web server command: ${E2E_WEB_SERVER_COMMAND}"
  fi
  echo "[release-gate-local] e2e browser auto-install: ${E2E_AUTO_INSTALL_BROWSER}"
  echo "[release-gate-local] e2e allow browser download failure: ${E2E_ALLOW_BROWSER_DOWNLOAD_FAILURE}"
  echo "[release-gate-local] e2e timeout seconds: ${E2E_TIMEOUT_SECONDS} (grace=${E2E_TIMEOUT_GRACE_SECONDS})"
  echo "[release-gate-local] playwright test timeout ms: ${E2E_TEST_TIMEOUT_MS}"
  echo "[release-gate-local] playwright browsers path: ${PLAYWRIGHT_BROWSERS_PATH}"
  rm -f "${E2E_LOG_PATH}" "${E2E_SUMMARY_PATH}"
  set +e
  PATH="${E2E_EXEC_PATH}" \
  CI=1 \
  PLAYWRIGHT_AUTO_INSTALL="${E2E_AUTO_INSTALL_BROWSER}" \
  PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH}" \
  E2E_WEB_SERVER_COMMAND="${E2E_WEB_SERVER_COMMAND:-}" \
  E2E_TEST_TIMEOUT_MS="${E2E_TEST_TIMEOUT_MS}" \
  E2E_TIMEOUT_SECONDS="${E2E_TIMEOUT_SECONDS}" \
  E2E_TIMEOUT_GRACE_SECONDS="${E2E_TIMEOUT_GRACE_SECONDS}" \
  "${E2E_NODE_BIN}" scripts/run-e2e-with-timeout.mjs 2>&1 | tee "${E2E_LOG_PATH}"
  E2E_EXIT_CODE=${PIPESTATUS[0]}
  set -e
  PATH="${E2E_EXEC_PATH}" "${E2E_NODE_BIN}" scripts/summarize-e2e-result.mjs \
    --log-path "${E2E_LOG_PATH}" \
    --exit-code "${E2E_EXIT_CODE}" \
    --summary-path "${E2E_SUMMARY_PATH}"
  PATH="${E2E_EXEC_PATH}" "${E2E_NODE_BIN}" scripts/check-e2e-summary-schema.mjs \
    --summary-path "${E2E_SUMMARY_PATH}" \
    --required-schema-version v1
  E2E_CLASSIFICATION="$(PATH="${E2E_EXEC_PATH}" "${E2E_NODE_BIN}" -e "const fs=require('fs');const p='${E2E_SUMMARY_PATH}';if(!fs.existsSync(p)){process.stdout.write('unavailable');process.exit(0);}const payload=JSON.parse(fs.readFileSync(p,'utf8'));process.stdout.write(String(payload.classification||'unknown'));")"
  if [[ "${E2E_EXIT_CODE}" -ne 0 ]]; then
    if [[ "${E2E_CLASSIFICATION}" == "browser_download_network" && "${E2E_ALLOW_BROWSER_DOWNLOAD_FAILURE}" == "1" && "${STRICT_E2E_REQUIRED}" != "1" ]]; then
      echo "[release-gate-local] e2e degraded: browser download network failure allowed by override."
      echo "[release-gate-local] summary: ${E2E_SUMMARY_PATH}"
    else
      echo "[release-gate-local] e2e failed (classification=${E2E_CLASSIFICATION})."
      echo "[release-gate-local] summary: ${E2E_SUMMARY_PATH}"
      exit "${E2E_EXIT_CODE}"
    fi
  fi
else
  echo "[release-gate-local] skip e2e (set RUN_E2E=1; E2E_BASE_URL optional)"
  rm -f "${E2E_LOG_PATH}" "${E2E_SUMMARY_PATH}"
  cat >"${E2E_LOG_PATH}" <<'EOF'
[release-gate-local] frontend e2e skipped by configuration
EOF
  node scripts/summarize-e2e-result.mjs \
    --log-path "${E2E_LOG_PATH}" \
    --exit-code "nan" \
    --summary-path "${E2E_SUMMARY_PATH}" \
    --summary-title "Frontend e2e smoke (skipped)"
fi

GATE_ORCHESTRATION_SUMMARY_PATH="${GATE_ORCHESTRATION_SUMMARY_PATH:-/tmp/release-gate-orchestration-summary-local.json}"
RUNTIME_COMPONENT_KIND="$(release_gate_component_kind optional)"
E2E_COMPONENT_KIND="$(release_gate_component_kind optional)"
cd "${BACKEND_DIR}"
"${BACKEND_PYTHON}" scripts/build_gate_orchestration_summary.py \
  --mode release-local \
  --output "${GATE_ORCHESTRATION_SUMMARY_PATH}" \
  --component "worktree_materialization,${WORKTREE_MATERIALIZATION_SUMMARY_PATH:-/tmp/worktree-materialization-summary-local.json},required" \
  --component "override,/tmp/release-gate-override-summary-local.json,required" \
  --component "slo,${SLO_BURN_RATE_SUMMARY_PATH:-/tmp/slo-burn-rate-summary-local.json},required" \
  --component "openapi_snapshot,${OPENAPI_SNAPSHOT_PATH:-/tmp/openapi-contract-snapshot-local.json},optional" \
  --component "api_contract,${API_CONTRACT_SOT_SUMMARY_PATH:-/tmp/api-contract-sot-summary-local.json},required" \
  --component "api_contract_snapshot,${API_CONTRACT_SNAPSHOT_SUMMARY_PATH:-/tmp/api-contract-snapshot-summary-local.json},required" \
  --component "idempotency_coverage,${IDEMPOTENCY_COVERAGE_SUMMARY_PATH:-/tmp/idempotency-coverage-summary-local.json},required" \
  --component "idempotency_convergence,${IDEMPOTENCY_CONVERGENCE_SUMMARY_PATH:-/tmp/idempotency-contract-convergence-summary-local.json},required" \
  --component "bola_coverage,${BOLA_COVERAGE_SUMMARY_PATH:-/tmp/bola-coverage-summary-local.json},required" \
  --component "rate_limit_policy,${RATE_LIMIT_POLICY_SUMMARY_PATH:-/tmp/rate-limit-policy-summary-local.json},required" \
  --component "service_tier,${SERVICE_TIER_SUMMARY_PATH:-/tmp/service-tier-gate-summary-local.json},required" \
  --component "ai_quality_source,${AI_QUALITY_FETCH_SUMMARY_PATH:-/tmp/ai-quality-snapshot-fetch-summary.json},required" \
  --component "ai_quality_gate,${AI_QUALITY_GATE_SUMMARY_PATH:-/tmp/ai-quality-snapshot-gate-summary-local.json},required" \
  --component "ai_runtime,${AI_RUNTIME_SUMMARY_PATH:-/tmp/ai-runtime-gate-summary-local.json},required" \
  --component "ai_router_multinode_stress,${AI_ROUTER_MULTINODE_STRESS_SUMMARY_PATH:-/tmp/ai-router-multinode-stress-summary-local.json},optional" \
  --component "ai_router_runtime_persist,${AI_ROUTER_RUNTIME_PERSIST_SUMMARY_PATH:-/tmp/ai-router-runtime-persist-summary-local.json},optional" \
  --component "timeline_perf,${TIMELINE_PERF_SUMMARY_PATH:-/tmp/timeline-perf-gate-summary-local.json},optional" \
  --component "core_loop,${CORE_LOOP_SNAPSHOT_SUMMARY_PATH:-/tmp/core-loop-snapshot-release-gate-local-summary.json},required" \
  --component "timeline_runtime,${TIMELINE_RUNTIME_SUMMARY_PATH:-/tmp/timeline-runtime-alert-summary-local.json},${RUNTIME_COMPONENT_KIND}" \
  --component "outbox_health,${OUTBOX_HEALTH_SUMMARY_PATH:-/tmp/notification-outbox-health-summary-local.json},${RUNTIME_COMPONENT_KIND}" \
  --component "outbox_slo,${OUTBOX_SLO_SUMMARY_PATH:-/tmp/outbox-slo-summary-local.json},${RUNTIME_COMPONENT_KIND}" \
  --component "outbox_self_heal,${OUTBOX_SELF_HEAL_SUMMARY_PATH:-/tmp/outbox-self-heal-summary-local.json},${RUNTIME_COMPONENT_KIND}" \
  --component "observability_contract,${OBSERVABILITY_CONTRACT_SUMMARY_PATH:-/tmp/observability-contract-summary-local.json},${RUNTIME_COMPONENT_KIND}" \
  --component "data_rights_drill,${DATA_RIGHTS_FIRE_DRILL_OUTPUT:-/tmp/data-rights-fire-drill-local.json},optional" \
  --component "data_retention_bundle,${DATA_RETENTION_BUNDLE_SUMMARY_PATH:-/tmp/data-retention-bundle-summary-local.json},optional" \
  --component "growth_cost,${GROWTH_COST_SNAPSHOT_PATH:-/tmp/growth-cost-snapshot-local.json},optional" \
  --component "full_pytest_stability,${FULL_PYTEST_STABILITY_SUMMARY_PATH:-/tmp/full-pytest-stability-summary-local.json},optional" \
  --component "quick_backend,${QUICK_BACKEND_CONTRACT_SUMMARY_PATH:-/tmp/release-gate-local-quick-backend-tests-summary.json},optional" \
  --component "frontend_e2e,${E2E_SUMMARY_PATH:-/tmp/frontend-e2e-local-summary.json},${E2E_COMPONENT_KIND}" \
  --metadata "profile=${RELEASE_GATE_SECURITY_PROFILE}" \
  --metadata "protected_branch=${RELEASE_GATE_PROTECTED_BRANCH}"
echo "[release-gate-local] gate orchestration summary: ${GATE_ORCHESTRATION_SUMMARY_PATH}"

GATE_NOISE_SUMMARY_PATH="/tmp/release-gate-noise-summary-local.json"
rm -f "${GATE_NOISE_SUMMARY_PATH}"
GATE_NOISE_ARGS=(
  "--orchestration-summary" "${GATE_ORCHESTRATION_SUMMARY_PATH}"
  "--output" "${GATE_NOISE_SUMMARY_PATH}"
  "--allow-missing-summary"
)
if [[ "${RELEASE_GATE_PROTECTED_BRANCH}" == "1" || "${CI:-}" == "true" || "${CI:-}" == "1" || "${RELEASE_GATE_FAIL_ON_REQUIRED_DEGRADED:-0}" == "1" ]]; then
  GATE_NOISE_ARGS+=("--fail-on-required-degraded")
fi
if [[ "${RELEASE_GATE_PROTECTED_BRANCH}" == "1" || "${CI:-}" == "true" || "${CI:-}" == "1" || "${RELEASE_GATE_FAIL_ON_REQUIRED_SKIPPED:-0}" == "1" ]]; then
  GATE_NOISE_ARGS+=("--fail-on-required-skipped")
fi
"${BACKEND_PYTHON}" scripts/summarize_release_gate_noise.py "${GATE_NOISE_ARGS[@]}"

if [[ -z "${RELEASE_GATE_CLEAN_EVIDENCE_NOISE+x}" ]]; then
  if [[ "${CI:-}" == "true" || "${CI:-}" == "1" ]]; then
    RELEASE_GATE_CLEAN_EVIDENCE_NOISE="0"
  else
    RELEASE_GATE_CLEAN_EVIDENCE_NOISE="1"
  fi
fi
if [[ "${RELEASE_GATE_CLEAN_EVIDENCE_NOISE}" == "1" ]]; then
  echo "[release-gate-local] evidence noise cleanup: enabled"
  bash "${ROOT_DIR}/scripts/clean-evidence-noise.sh"
else
  echo "[release-gate-local] evidence noise cleanup: disabled"
fi
