#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
BACKEND_PYTHONPATH="${BACKEND_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

cd "${BACKEND_DIR}"

can_bootstrap_python() {
  local candidate="$1"
  PYTHONUTF8=1 PYTHONPATH="${BACKEND_PYTHONPATH}" "${candidate}" -c \
    "import signal; signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError())); signal.alarm(8); import fastapi; import pydantic_settings; import sqlmodel.orm.session; import openai; signal.alarm(0)" \
    >/dev/null 2>&1
}

if [[ -n "${BACKEND_PYTHON_BIN:-}" ]]; then
  if [[ "${BACKEND_PYTHON_BIN}" == */* ]]; then
    if [[ ! -x "${BACKEND_PYTHON_BIN}" ]]; then
      echo "[release-gate] fail: BACKEND_PYTHON_BIN is not executable: ${BACKEND_PYTHON_BIN}"
      exit 1
    fi
  elif ! command -v "${BACKEND_PYTHON_BIN}" >/dev/null 2>&1; then
    echo "[release-gate] fail: BACKEND_PYTHON_BIN command not found: ${BACKEND_PYTHON_BIN}"
    exit 1
  fi
  if ! can_bootstrap_python "${BACKEND_PYTHON_BIN}"; then
    echo "[release-gate] fail: BACKEND_PYTHON_BIN failed bootstrap preflight."
    echo "[release-gate] hint: PYTHONUTF8=1 PYTHONPATH=. ${BACKEND_PYTHON_BIN} -c \"import fastapi; import pydantic_settings; import sqlmodel.orm.session; import openai\""
    exit 1
  fi
  PYTHON_BIN="${BACKEND_PYTHON_BIN}"
else
  for candidate in ".venv-gate/bin/python" "venv/bin/python" "python3"; do
    if [[ "${candidate}" == */* ]] && [[ ! -x "${candidate}" ]]; then
      continue
    fi
    if [[ "${candidate}" != */* ]] && ! command -v "${candidate}" >/dev/null 2>&1; then
      continue
    fi
    if can_bootstrap_python "${candidate}"; then
      PYTHON_BIN="${candidate}"
      break
    fi
    echo "[release-gate] skip python candidate (preflight failed): ${candidate}"
  done
fi

if [[ -z "${PYTHON_BIN:-}" ]]; then
  echo "[release-gate] fail: no usable backend python interpreter found."
  exit 1
fi

echo "[release-gate] backend python: ${PYTHON_BIN}"
echo "[release-gate] backend bootstrap: PYTHONUTF8=1, PYTHONPATH includes ${BACKEND_DIR}"
export PYTHONUTF8=1
export PYTHONPATH="${BACKEND_PYTHONPATH}"
export FLY_APP_NAME="${FLY_APP_NAME:-haven-api-prod}"
RELEASE_GATE_STEP_TIMEOUT_SECONDS="${RELEASE_GATE_STEP_TIMEOUT_SECONDS:-900}"
RELEASE_GATE_HEARTBEAT_SECONDS="${RELEASE_GATE_HEARTBEAT_SECONDS:-45}"

run_python_gate_step() {
  local step_name="$1"
  shift
  "${PYTHON_BIN}" scripts/run_with_timeout.py \
    --timeout-seconds "${RELEASE_GATE_STEP_TIMEOUT_SECONDS}" \
    --heartbeat-seconds "${RELEASE_GATE_HEARTBEAT_SECONDS}" \
    --step-name "${step_name}" \
    -- "${PYTHON_BIN}" "$@"
}

run_shell_gate_step() {
  local step_name="$1"
  shift
  "${PYTHON_BIN}" scripts/run_with_timeout.py \
    --timeout-seconds "${RELEASE_GATE_STEP_TIMEOUT_SECONDS}" \
    --heartbeat-seconds "${RELEASE_GATE_HEARTBEAT_SECONDS}" \
    --step-name "${step_name}" \
    -- "$@"
}

require_release_env_var() {
  local env_name="$1"
  local hint="$2"
  if [[ -n "${!env_name:-}" ]]; then
    return 0
  fi
  echo "[release-gate] fail: missing required deploy env ${env_name}"
  echo "[release-gate] hint: ${hint}"
  exit 1
}

if [[ -z "${SLO_GATE_HEALTH_SLO_URL:-}" && -n "${FLY_APP_NAME:-}" ]]; then
  export SLO_GATE_HEALTH_SLO_URL="https://${FLY_APP_NAME}.fly.dev/health/slo"
  echo "[release-gate] defaulted SLO_GATE_HEALTH_SLO_URL from FLY_APP_NAME"
  echo "[release-gate] slo health url: ${SLO_GATE_HEALTH_SLO_URL}"
fi

run_python_gate_step "check_release_gate_override_contract" scripts/check_release_gate_override_contract.py \
  --summary-path /tmp/release-gate-override-summary.json

run_python_gate_step "check_env" scripts/check_env.py
run_python_gate_step "check_env_secret_manifest_contract" scripts/check_env_secret_manifest_contract.py
require_release_env_var "FLY_API_TOKEN" "export FLY_API_TOKEN=<token>"
require_release_env_var "CORS_ORIGINS" "export CORS_ORIGINS='[\"https://example.com\"]'"
echo "[release-gate] deploy preflight gate: fail-closed"
run_shell_gate_step "deploy_fly_backend_preflight" \
  env FLY_DEPLOY_PREFLIGHT_ONLY=1 \
  "${ROOT_DIR}/scripts/deploy-fly-backend.sh"
run_shell_gate_step "security_gate" env PYTHON_BIN="${PYTHON_BIN}" ./scripts/security-gate.sh
SLO_BURN_RATE_SUMMARY_PATH="/tmp/slo-burn-rate-summary.json"
rm -f "${SLO_BURN_RATE_SUMMARY_PATH}"
RELEASE_GATE_REQUIRE_SLO_SUFFICIENT_DATA="${RELEASE_GATE_REQUIRE_SLO_SUFFICIENT_DATA:-0}"
if [[ "${RELEASE_GATE_ALLOW_MISSING_SLO_URL:-0}" == "1" ]]; then
  echo "[release-gate] slo burn-rate gate: override enabled (allow missing URL)"
  "${PYTHON_BIN}" scripts/check_slo_burn_rate_gate.py \
    --allow-missing-url \
    --summary-path "${SLO_BURN_RATE_SUMMARY_PATH}"
else
  echo "[release-gate] slo burn-rate gate: fail-closed"
  if [[ "${RELEASE_GATE_REQUIRE_SLO_SUFFICIENT_DATA}" == "1" ]]; then
    echo "[release-gate] slo burn-rate gate: require sufficient data"
    "${PYTHON_BIN}" scripts/check_slo_burn_rate_gate.py \
      --require-sufficient-data \
      --summary-path "${SLO_BURN_RATE_SUMMARY_PATH}"
  else
    echo "[release-gate] slo burn-rate gate: monitor insufficient_data"
    "${PYTHON_BIN}" scripts/check_slo_burn_rate_gate.py \
      --summary-path "${SLO_BURN_RATE_SUMMARY_PATH}"
  fi
fi
"${PYTHON_BIN}" scripts/check_error_budget_freeze_gate.py
SERVICE_TIER_SUMMARY_PATH="/tmp/service-tier-gate-summary.json"
rm -f "${SERVICE_TIER_SUMMARY_PATH}"
"${PYTHON_BIN}" scripts/check_service_tier_budget_gate.py \
  --summary-path "${SERVICE_TIER_SUMMARY_PATH}"
SERVICE_TIER_SUMMARY_PATH="${SERVICE_TIER_SUMMARY_PATH}" \
"${PYTHON_BIN}" - <<'PY'
import json
import os
from pathlib import Path

summary_file = Path(os.environ["SERVICE_TIER_SUMMARY_PATH"])
if not summary_file.exists():
    print("[release-gate] service tier summary")
    print("  result: unavailable")
    print("  reason: summary_file_missing")
    raise SystemExit(0)

try:
    payload = json.loads(summary_file.read_text(encoding="utf-8"))
except Exception:
    print("[release-gate] service tier summary")
    print("  result: unavailable")
    print("  reason: summary_parse_error")
    raise SystemExit(0)

meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
reasons = payload.get("reasons") or []
print("[release-gate] service tier summary")
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
  echo "[release-gate] launch signoff gate: override enabled (allow missing artifact)"
  "${PYTHON_BIN}" scripts/check_launch_signoff_gate.py \
    --allow-missing-artifact \
    --require-ready \
    --max-age-days "${LAUNCH_SIGNOFF_MAX_AGE_DAYS:-14}"
else
  echo "[release-gate] launch signoff gate: fail-closed"
  "${PYTHON_BIN}" scripts/check_launch_signoff_gate.py \
    --require-ready \
    --max-age-days "${LAUNCH_SIGNOFF_MAX_AGE_DAYS:-14}"
fi

if [[ "${RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE:-0}" == "1" ]]; then
  echo "[release-gate] cuj synthetic evidence gate: override enabled (allow missing evidence)"
  "${PYTHON_BIN}" scripts/check_cuj_synthetic_evidence_gate.py \
    --allow-missing-evidence \
    --require-pass \
    --max-age-hours "${CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS:-36}"
else
  echo "[release-gate] cuj synthetic evidence gate: fail-closed"
  "${PYTHON_BIN}" scripts/check_cuj_synthetic_evidence_gate.py \
    --require-pass \
    --max-age-hours "${CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS:-36}"
fi

AI_QUALITY_EVIDENCE_PATH="/tmp/ai-quality-snapshot-latest.json"
AI_QUALITY_EVIDENCE_SOURCE="${RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE:-local_snapshot}"
AI_QUALITY_FETCH_SUMMARY_PATH="/tmp/ai-quality-snapshot-fetch-summary.json"
AI_QUALITY_GATE_SUMMARY_PATH="/tmp/ai-quality-snapshot-gate-summary.json"

rm -f "${AI_QUALITY_FETCH_SUMMARY_PATH}" "${AI_QUALITY_GATE_SUMMARY_PATH}"

if [[ "${AI_QUALITY_EVIDENCE_SOURCE}" == "daily_artifact" ]]; then
  echo "[release-gate] ai quality evidence source: daily_artifact"
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
  "${PYTHON_BIN}" scripts/fetch_latest_ai_quality_snapshot_evidence.py "${fetch_args[@]}"
elif [[ "${AI_QUALITY_EVIDENCE_SOURCE}" == "local_snapshot" ]]; then
  echo "[release-gate] ai quality evidence source: local_snapshot"
  "${PYTHON_BIN}" scripts/run_ai_quality_snapshot.py \
    --allow-missing-current \
    --output "${AI_QUALITY_EVIDENCE_PATH}"
  AI_QUALITY_FETCH_SUMMARY_PATH="${AI_QUALITY_FETCH_SUMMARY_PATH}" \
  AI_QUALITY_EVIDENCE_PATH="${AI_QUALITY_EVIDENCE_PATH}" \
  "${PYTHON_BIN}" - <<'PY'
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
  echo "[release-gate] fail: invalid RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE: ${AI_QUALITY_EVIDENCE_SOURCE}"
  echo "[release-gate] hint: supported values are local_snapshot or daily_artifact"
  exit 1
fi

if [[ "${RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE:-0}" == "1" ]]; then
  echo "[release-gate] ai quality snapshot gate: override enabled (allow missing evidence)"
  "${PYTHON_BIN}" scripts/check_ai_quality_snapshot_freshness_gate.py \
    --evidence "${AI_QUALITY_EVIDENCE_PATH}" \
    --allow-missing-evidence \
    --max-age-hours "${AI_QUALITY_SNAPSHOT_MAX_AGE_HOURS:-36}" \
    --summary-path "${AI_QUALITY_GATE_SUMMARY_PATH}"
else
  echo "[release-gate] ai quality snapshot gate: fail-closed"
  "${PYTHON_BIN}" scripts/check_ai_quality_snapshot_freshness_gate.py \
    --evidence "${AI_QUALITY_EVIDENCE_PATH}" \
    --max-age-hours "${AI_QUALITY_SNAPSHOT_MAX_AGE_HOURS:-36}" \
    --summary-path "${AI_QUALITY_GATE_SUMMARY_PATH}"
fi

AI_QUALITY_FETCH_SUMMARY_PATH="${AI_QUALITY_FETCH_SUMMARY_PATH}" \
AI_QUALITY_GATE_SUMMARY_PATH="${AI_QUALITY_GATE_SUMMARY_PATH}" \
"${PYTHON_BIN}" - <<'PY'
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

print("[release-gate] ai quality summary")
print(f"  source_result: {fetch_payload.get('result', 'unknown')}")
print(f"  source_reason: {', '.join(fetch_payload.get('reasons') or ['none'])}")
print(f"  source_type: {fetch_meta.get('source', 'artifact_fetch')}")
print(f"  gate_result: {gate_payload.get('result', 'unknown')}")
print(f"  evaluation_result: {gate_meta.get('evaluation_result', 'unknown')}")
print(f"  evidence_age_hours: {gate_meta.get('age_hours', 'unknown')}")
PY

CORE_LOOP_SNAPSHOT_PATH="/tmp/core-loop-snapshot-release-gate.json"
CORE_LOOP_SNAPSHOT_SUMMARY_PATH="/tmp/core-loop-snapshot-release-gate-summary.json"
CORE_LOOP_SNAPSHOT_DATABASE_URL="${CORE_LOOP_SNAPSHOT_DATABASE_URL:-sqlite:///./test.db}"
rm -f "${CORE_LOOP_SNAPSHOT_PATH}" "${CORE_LOOP_SNAPSHOT_SUMMARY_PATH}"
set +e
DATABASE_URL="${CORE_LOOP_SNAPSHOT_DATABASE_URL}" "${PYTHON_BIN}" scripts/run_core_loop_snapshot.py \
  --window-days "${CORE_LOOP_SNAPSHOT_WINDOW_DAYS:-1}" \
  --output "${CORE_LOOP_SNAPSHOT_PATH}" \
  --latest-path "${CORE_LOOP_SNAPSHOT_PATH}"
CORE_LOOP_SNAPSHOT_EXIT_CODE=$?
set -e

CORE_LOOP_SNAPSHOT_PATH="${CORE_LOOP_SNAPSHOT_PATH}" \
CORE_LOOP_SNAPSHOT_SUMMARY_PATH="${CORE_LOOP_SNAPSHOT_SUMMARY_PATH}" \
CORE_LOOP_SNAPSHOT_EXIT_CODE="${CORE_LOOP_SNAPSHOT_EXIT_CODE}" \
"${PYTHON_BIN}" - <<'PY'
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
print("[release-gate] core loop snapshot summary")
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

"${PYTHON_BIN}" -m pytest -q -p no:cacheprovider

cd "${ROOT_DIR}/frontend"
npm run check:env
TYPECHECK_TIMEOUT_MS="${TYPECHECK_TIMEOUT_MS:-180000}" npm run typecheck

if [[ "${RUN_E2E:-0}" == "1" ]]; then
  E2E_NODE_BIN="${E2E_NODE_BIN:-node}"
  E2E_EXEC_PATH="${PATH}"
  NODE_MAJOR="$("${E2E_NODE_BIN}" -p "process.versions.node.split('.')[0]")"
  if [[ "${NODE_MAJOR}" -gt 22 ]]; then
    if [[ -x "/opt/homebrew/opt/node@22/bin/node" ]]; then
      E2E_NODE_BIN="/opt/homebrew/opt/node@22/bin/node"
      E2E_EXEC_PATH="/opt/homebrew/opt/node@22/bin:${PATH}"
      NODE_MAJOR="$("${E2E_NODE_BIN}" -p "process.versions.node.split('.')[0]")"
      echo "[release-gate] e2e node source: homebrew_node22_auto"
    else
      echo "[release-gate] fail: RUN_E2E=1 is not supported on Node ${NODE_MAJOR}."
      echo "[release-gate] hint: use Node 20 or 22 for deterministic Playwright + Next runtime."
      echo "[release-gate] hint: current node=$(node -v)"
      exit 1
    fi
  else
    echo "[release-gate] e2e node source: current_path"
  fi
  E2E_PROJECT_BROWSERS_PATH="${ROOT_DIR}/frontend/.playwright-browsers"
  if [[ -z "${PLAYWRIGHT_BROWSERS_PATH+x}" && -d "${E2E_PROJECT_BROWSERS_PATH}" ]]; then
    PLAYWRIGHT_BROWSERS_PATH="${E2E_PROJECT_BROWSERS_PATH}"
    echo "[release-gate] reusing frontend Playwright browser cache: ${PLAYWRIGHT_BROWSERS_PATH}"
  fi
  echo "[release-gate] e2e node binary: ${E2E_NODE_BIN}"
  echo "[release-gate] e2e node version: $("${E2E_NODE_BIN}" -v)"
  echo "[release-gate] playwright browsers path: ${PLAYWRIGHT_BROWSERS_PATH:-default}"
  echo "[release-gate] RUN_E2E=1, running frontend smoke e2e"
  PATH="${E2E_EXEC_PATH}" \
  PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-}" \
  E2E_TIMEOUT_SECONDS="${E2E_TIMEOUT_SECONDS:-420}" \
  E2E_TIMEOUT_GRACE_SECONDS="${E2E_TIMEOUT_GRACE_SECONDS:-10}" \
  "${E2E_NODE_BIN}" scripts/run-e2e-with-timeout.mjs
else
  echo "[release-gate] skip frontend e2e (set RUN_E2E=1 to enable)"
fi

GATE_ORCHESTRATION_SUMMARY_PATH="${GATE_ORCHESTRATION_SUMMARY_PATH:-/tmp/release-gate-orchestration-summary.json}"
cd "${BACKEND_DIR}"
"${PYTHON_BIN}" scripts/build_gate_orchestration_summary.py \
  --mode release \
  --output "${GATE_ORCHESTRATION_SUMMARY_PATH}" \
  --component "override,/tmp/release-gate-override-summary.json,required" \
  --component "slo,${SLO_BURN_RATE_SUMMARY_PATH:-/tmp/slo-burn-rate-summary.json},required" \
  --component "service_tier,${SERVICE_TIER_SUMMARY_PATH:-/tmp/service-tier-gate-summary.json},required" \
  --component "ai_quality_source,${AI_QUALITY_FETCH_SUMMARY_PATH:-/tmp/ai-quality-snapshot-fetch-summary.json},required" \
  --component "ai_quality_gate,${AI_QUALITY_GATE_SUMMARY_PATH:-/tmp/ai-quality-snapshot-gate-summary.json},required" \
  --component "core_loop,${CORE_LOOP_SNAPSHOT_SUMMARY_PATH:-/tmp/core-loop-snapshot-release-gate-summary.json},required" \
  --metadata "profile=full"
echo "[release-gate] gate orchestration summary: ${GATE_ORCHESTRATION_SUMMARY_PATH}"
