#!/usr/bin/env bash
set -euo pipefail

LOCAL_DEV_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${LOCAL_DEV_LIB_DIR}/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
FRONTEND_DIR="${REPO_ROOT}/frontend"
LOCAL_RUNTIME_ENV_FILE="${REPO_ROOT}/config/local-dev-runtime.env"

source_shell_env_file() {
  local env_file="$1"
  if [[ -f "${env_file}" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "${env_file}"
    set +a
  fi
}

load_local_runtime_config() {
  if [[ ! -f "${LOCAL_RUNTIME_ENV_FILE}" ]]; then
    echo "[local-dev-lib] fail: missing ${LOCAL_RUNTIME_ENV_FILE}" >&2
    return 1
  fi

  set -a
  # shellcheck source=/dev/null
  source "${LOCAL_RUNTIME_ENV_FILE}"
  set +a

  : "${HAVEN_LOCAL_DEV_FRONTEND_HOST:?}"
  : "${HAVEN_LOCAL_DEV_FRONTEND_PORT:?}"
  : "${HAVEN_LOCAL_DEV_BACKEND_HOST:?}"
  : "${HAVEN_LOCAL_DEV_BACKEND_PORT:?}"
  : "${HAVEN_LOCAL_DEV_DATABASE_MODE:?}"
  : "${HAVEN_LOCAL_DEV_POSTGRES_HOST:?}"
  : "${HAVEN_LOCAL_DEV_POSTGRES_PORT:?}"
  : "${HAVEN_LOCAL_DEV_POSTGRES_DATABASE:?}"
  : "${HAVEN_LOCAL_DEV_POSTGRES_USER:?}"
  : "${HAVEN_LOCAL_DEV_POSTGRES_PASSWORD:?}"
  : "${HAVEN_LOCAL_DEV_POSTGRES_SERVICE:?}"
  : "${HAVEN_LOCAL_DEV_POSTGRES_COMPOSE_PROJECT:?}"
  : "${HAVEN_LOCAL_DEV_POSTGRES_COMPOSE_FILE:?}"
}

local_dev_database_mode() {
  printf '%s\n' "${HAVEN_LOCAL_DEV_DATABASE_MODE}"
}

local_dev_database_url() {
  if [[ "$(local_dev_database_mode)" != "postgres" ]]; then
    echo "[local-dev-lib] fail: unsupported HAVEN_LOCAL_DEV_DATABASE_MODE=${HAVEN_LOCAL_DEV_DATABASE_MODE}" >&2
    return 1
  fi
  printf 'postgresql://%s:%s@%s:%s/%s\n' \
    "${HAVEN_LOCAL_DEV_POSTGRES_USER}" \
    "${HAVEN_LOCAL_DEV_POSTGRES_PASSWORD}" \
    "${HAVEN_LOCAL_DEV_POSTGRES_HOST}" \
    "${HAVEN_LOCAL_DEV_POSTGRES_PORT}" \
    "${HAVEN_LOCAL_DEV_POSTGRES_DATABASE}"
}

local_dev_backend_origin() {
  printf 'http://%s:%s\n' "${HAVEN_LOCAL_DEV_BACKEND_HOST}" "${HAVEN_LOCAL_DEV_BACKEND_PORT}"
}

local_dev_frontend_origin() {
  printf 'http://%s:%s\n' "${HAVEN_LOCAL_DEV_FRONTEND_HOST}" "${HAVEN_LOCAL_DEV_FRONTEND_PORT}"
}

local_dev_api_url() {
  printf '%s/api\n' "$(local_dev_backend_origin)"
}

local_dev_ws_url() {
  printf 'ws://%s:%s\n' "${HAVEN_LOCAL_DEV_BACKEND_HOST}" "${HAVEN_LOCAL_DEV_BACKEND_PORT}"
}

local_dev_postgres_compose_file() {
  local raw_path="${HAVEN_LOCAL_DEV_POSTGRES_COMPOSE_FILE:?}"
  if [[ "${raw_path}" = /* ]]; then
    printf '%s\n' "${raw_path}"
  else
    printf '%s\n' "${REPO_ROOT}/${raw_path}"
  fi
}

local_dev_postgres_service() {
  printf '%s\n' "${HAVEN_LOCAL_DEV_POSTGRES_SERVICE}"
}

docker_compose_available() {
  docker compose version >/dev/null 2>&1
}

run_local_dev_docker_compose() {
  local compose_file
  compose_file="$(local_dev_postgres_compose_file)"
  docker compose \
    -f "${compose_file}" \
    -p "${HAVEN_LOCAL_DEV_POSTGRES_COMPOSE_PROJECT}" \
    "$@"
}

prepare_local_runtime_env() {
  source_shell_env_file "${BACKEND_DIR}/.env"
  source_shell_env_file "${FRONTEND_DIR}/.env.local"
  load_local_runtime_config

  export HAVEN_LOCAL_DEV_MODE=1
  export HAVEN_LOCAL_DEV_DB_MODE
  HAVEN_LOCAL_DEV_DB_MODE="$(local_dev_database_mode)"
  export ENV=development
  export ENVIRONMENT=development

  export HOST="${HAVEN_LOCAL_DEV_BACKEND_HOST}"
  export PORT="${HAVEN_LOCAL_DEV_BACKEND_PORT}"

  export DATABASE_URL
  DATABASE_URL="$(local_dev_database_url)"
  unset DATABASE_READ_REPLICA_URL || true

  export NEXT_PUBLIC_API_URL
  NEXT_PUBLIC_API_URL="$(local_dev_api_url)"
  export NEXT_PUBLIC_WS_URL
  NEXT_PUBLIC_WS_URL="$(local_dev_ws_url)"

  export ABUSE_GUARD_STORE_BACKEND=memory
  export ABUSE_GUARD_REDIS_URL=
  export EVENTS_LOG_INGEST_STORE_BACKEND=memory
  export EVENTS_LOG_INGEST_REDIS_URL=
  export AI_ROUTER_SHARED_STATE_BACKEND=memory
  export AI_ROUTER_REDIS_URL=
  export REDIS_URL=

  export ASYNC_JOURNAL_ANALYSIS="${ASYNC_JOURNAL_ANALYSIS:-0}"
  export RELOAD="${RELOAD:-0}"
  export PYTHONUTF8=1
  export PYTHONPATH="${BACKEND_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
}

node22_path_maybe() {
  local node22_dir="/opt/homebrew/opt/node@22/bin"
  if [[ -d "${node22_dir}" ]]; then
    printf '%s\n' "${node22_dir}"
  fi
}

print_local_runtime_summary() {
  printf '[local-dev] frontend_origin=%s\n' "$(local_dev_frontend_origin)"
  printf '[local-dev] backend_origin=%s\n' "$(local_dev_backend_origin)"
  printf '[local-dev] api_url=%s\n' "$(local_dev_api_url)"
  printf '[local-dev] database_mode=%s\n' "$(local_dev_database_mode)"
  printf '[local-dev] database_url=%s\n' "$(local_dev_database_url)"
  printf '[local-dev] storage_mode=%s\n' "${HAVEN_LOCAL_DEV_STORAGE_MODE:-unknown}"
}
