#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./local-dev-lib.sh
source "${SCRIPT_DIR}/local-dev-lib.sh"

prepare_local_runtime_env

backend_origin="$(local_dev_backend_origin)"
frontend_origin="$(local_dev_frontend_origin)"
expected_api_url="$(local_dev_api_url)"
expected_db_url="$(local_dev_database_url)"
expected_db_port="${HAVEN_LOCAL_DEV_POSTGRES_PORT}"

if ! docker_compose_available; then
  echo "[local-runtime-verify] fail: docker compose is required for canonical local Postgres" >&2
  exit 1
fi

require_single_listener() {
  local port="$1"
  local label="$2"
  local pids
  pids="$(lsof -ti "tcp:${port}" -sTCP:LISTEN || true)"
  local count
  count="$(printf '%s\n' "${pids}" | sed '/^$/d' | wc -l | tr -d ' ')"
  if [[ "${count}" != "1" ]]; then
    echo "[local-runtime-verify] fail: expected exactly 1 ${label} listener on ${port}, found ${count}" >&2
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN || true
    return 1
  fi
  printf '%s\n' "${pids}" | sed '/^$/d'
}

extract_env_value() {
  local pid="$1"
  local key="$2"
  ps eww -p "${pid}" | tr ' ' '\n' | grep "^${key}=" | tail -n 1 | cut -d '=' -f 2-
}

extract_env_value_from_lineage() {
  local pid="$1"
  local key="$2"
  local current_pid="${pid}"
  for _ in $(seq 1 4); do
    [[ -z "${current_pid}" ]] && break
    local value
    value="$(extract_env_value "${current_pid}" "${key}" || true)"
    if [[ -n "${value}" ]]; then
      printf '%s\n' "${value}"
      return 0
    fi
    current_pid="$(ps -o ppid= -p "${current_pid}" | tr -d ' ' || true)"
    if [[ -z "${current_pid}" || "${current_pid}" == "1" ]]; then
      break
    fi
  done
  return 1
}

frontend_pid="$(require_single_listener "${HAVEN_LOCAL_DEV_FRONTEND_PORT}" "frontend")"
backend_pid="$(require_single_listener "${HAVEN_LOCAL_DEV_BACKEND_PORT}" "backend")"

frontend_api_url="$(extract_env_value_from_lineage "${frontend_pid}" "NEXT_PUBLIC_API_URL" || true)"
backend_database_url="$(extract_env_value_from_lineage "${backend_pid}" "DATABASE_URL" || true)"
backend_local_mode="$(extract_env_value_from_lineage "${backend_pid}" "HAVEN_LOCAL_DEV_MODE" || true)"

printf '[local-runtime-verify] frontend_pid=%s backend_pid=%s\n' "${frontend_pid}" "${backend_pid}"
printf '[local-runtime-verify] frontend_api_url=%s\n' "${frontend_api_url:-missing}"
printf '[local-runtime-verify] backend_database_url=%s\n' "${backend_database_url:-missing}"
printf '[local-runtime-verify] backend_local_mode=%s\n' "${backend_local_mode:-missing}"

if [[ "${frontend_api_url}" != "${expected_api_url}" ]]; then
  echo "[local-runtime-verify] fail: frontend NEXT_PUBLIC_API_URL mismatch" >&2
  exit 1
fi

if [[ "${backend_database_url}" != "${expected_db_url}" ]]; then
  echo "[local-runtime-verify] fail: backend DATABASE_URL mismatch" >&2
  exit 1
fi

if [[ "${backend_database_url}" == sqlite:* ]]; then
  echo "[local-runtime-verify] fail: backend still points to sqlite" >&2
  exit 1
fi

if [[ "${backend_database_url}" == *"pooler.supabase.com"* ]]; then
  echo "[local-runtime-verify] fail: backend still points to remote Supabase pooler" >&2
  exit 1
fi

if [[ "${backend_local_mode}" != "1" ]]; then
  echo "[local-runtime-verify] fail: backend missing HAVEN_LOCAL_DEV_MODE=1" >&2
  exit 1
fi

if ! lsof -nP -iTCP:"${expected_db_port}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[local-runtime-verify] fail: expected local Postgres listener on ${expected_db_port}" >&2
  exit 1
fi

if ! run_local_dev_docker_compose ps --services --filter status=running | grep -qx "$(local_dev_postgres_service)"; then
  echo "[local-runtime-verify] fail: canonical local Postgres compose service is not running" >&2
  exit 1
fi

curl -fsS --max-time 5 "${frontend_origin}/api/ping" >/dev/null
curl -fsS --max-time 5 "${backend_origin}/health/live" >/dev/null
curl -fsS --max-time 5 "${backend_origin}/health/ready" >/dev/null

printf '[local-runtime-verify] ok: frontend=%s backend=%s\n' "${frontend_origin}" "${backend_origin}"
