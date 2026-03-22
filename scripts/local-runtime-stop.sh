#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./local-dev-lib.sh
source "${SCRIPT_DIR}/local-dev-lib.sh"

prepare_local_runtime_env

managed_dev_command() {
  local command="$1"
  case "${command}" in
    *"npm run dev"*|*"next dev"*|*"next-server"*|*"run_uvicorn.py"*|*"run_uvicorn_worker.py"*|*"uvicorn app.main:app"*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

collect_managed_pids_for_port() {
  local port="$1"
  local seed_pids
  seed_pids="$(lsof -ti "tcp:${port}" -sTCP:LISTEN || true)"
  if [[ "${port}" == "${HAVEN_LOCAL_DEV_FRONTEND_PORT}" ]]; then
    seed_pids="${seed_pids}
$(ps -axo pid=,command= | awk 'index($0, "npm run dev -- --hostname") || index($0, "next dev") || index($0, "next-server") {print $1}')"
  elif [[ "${port}" == "${HAVEN_LOCAL_DEV_BACKEND_PORT}" ]]; then
    seed_pids="${seed_pids}
$(ps -axo pid=,command= | awk 'index($0, "uvicorn app.main:app") || index($0, "run_uvicorn.py") || index($0, "run_uvicorn_worker.py") {print $1}')"
  fi
  if [[ -z "${seed_pids}" ]]; then
    return 0
  fi

  local collected=""
  local pid=""
  while read -r pid; do
    [[ -z "${pid}" ]] && continue
    local current_pid="${pid}"
    while [[ -n "${current_pid}" && "${current_pid}" != "1" ]]; do
      local command
      command="$(ps -o command= -p "${current_pid}" 2>/dev/null || true)"
      if [[ -z "${command}" ]] || ! managed_dev_command "${command}"; then
        break
      fi
      case " ${collected} " in
        *" ${current_pid} "*) ;;
        *) collected="${collected} ${current_pid}" ;;
      esac
      current_pid="$(ps -o ppid= -p "${current_pid}" 2>/dev/null | tr -d ' ' || true)"
    done
  done <<< "${seed_pids}"

  printf '%s\n' "${collected}" | xargs echo -n 2>/dev/null || true
}

stop_port_listener() {
  local port="$1"
  local pids
  pids="$(collect_managed_pids_for_port "${port}")"
  if [[ -z "${pids}" ]]; then
    echo "[local-runtime-stop] port ${port}: already clear"
    return 0
  fi
  echo "[local-runtime-stop] port ${port}: killing ${pids}"
  # shellcheck disable=SC2086
  kill ${pids} 2>/dev/null || true
}

wait_until_port_clears() {
  local port="$1"
  for _ in $(seq 1 20); do
    if ! lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "[local-runtime-stop] port ${port}: clear"
      return 0
    fi
    sleep 0.25
  done
  echo "[local-runtime-stop] fail: port ${port} still has a listener" >&2
  return 1
}

force_kill_port_listener() {
  local port="$1"
  local pids
  pids="$(collect_managed_pids_for_port "${port}")"
  if [[ -z "${pids}" ]]; then
    return 0
  fi
  echo "[local-runtime-stop] port ${port}: forcing kill ${pids}"
  # shellcheck disable=SC2086
  kill -9 ${pids} 2>/dev/null || true
}

stop_port_listener "${HAVEN_LOCAL_DEV_FRONTEND_PORT}"
stop_port_listener "${HAVEN_LOCAL_DEV_BACKEND_PORT}"
if ! wait_until_port_clears "${HAVEN_LOCAL_DEV_FRONTEND_PORT}"; then
  force_kill_port_listener "${HAVEN_LOCAL_DEV_FRONTEND_PORT}"
  wait_until_port_clears "${HAVEN_LOCAL_DEV_FRONTEND_PORT}"
fi
if ! wait_until_port_clears "${HAVEN_LOCAL_DEV_BACKEND_PORT}"; then
  force_kill_port_listener "${HAVEN_LOCAL_DEV_BACKEND_PORT}"
  wait_until_port_clears "${HAVEN_LOCAL_DEV_BACKEND_PORT}"
fi

bash "${SCRIPT_DIR}/local-dev-db.sh" stop || true
