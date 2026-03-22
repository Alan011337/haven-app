#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./local-dev-lib.sh
source "${SCRIPT_DIR}/local-dev-lib.sh"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/local-dev-db.sh start
  bash scripts/local-dev-db.sh stop
  bash scripts/local-dev-db.sh migrate
  bash scripts/local-dev-db.sh reset
  bash scripts/local-dev-db.sh status
EOF
}

fail_missing_docker_compose() {
  cat <<'EOF' >&2
[local-dev-db] fail: docker compose is required for canonical localhost Postgres.
[local-dev-db] install Docker Desktop or another Docker engine with Compose support,
[local-dev-db] then rerun: bash scripts/local-dev-db.sh start
EOF
  exit 1
}

ensure_docker_compose() {
  if ! docker_compose_available; then
    fail_missing_docker_compose
  fi
}

run_alembic_for_local_dev() {
  cd "${BACKEND_DIR}"
  ./scripts/run-alembic.sh --mode fresh-bootstrap upgrade head
}

wait_for_local_postgres_ready() {
  local service
  service="$(local_dev_postgres_service)"
  for _ in $(seq 1 45); do
    if run_local_dev_docker_compose exec -T "${service}" \
      pg_isready \
      -U "${HAVEN_LOCAL_DEV_POSTGRES_USER}" \
      -d "${HAVEN_LOCAL_DEV_POSTGRES_DATABASE}" >/dev/null 2>&1; then
      echo "[local-dev-db] ok: local Postgres is ready"
      return 0
    fi
    sleep 1
  done

  echo "[local-dev-db] fail: local Postgres did not become ready in time" >&2
  run_local_dev_docker_compose logs --tail 80 "${service}" || true
  return 1
}

ensure_local_db_started() {
  ensure_docker_compose
  echo "[local-dev-db] start: launching canonical local Postgres"
  run_local_dev_docker_compose up -d "$(local_dev_postgres_service)"
  wait_for_local_postgres_ready
}

stop_local_db() {
  if ! docker_compose_available; then
    echo "[local-dev-db] stop: docker compose unavailable; skipping"
    return 0
  fi
  echo "[local-dev-db] stop: stopping canonical local Postgres"
  run_local_dev_docker_compose stop "$(local_dev_postgres_service)" >/dev/null 2>&1 || true
}

prepare_local_runtime_env

command="${1:-}"
case "${command}" in
  start)
    ensure_local_db_started
    ;;
  stop)
    stop_local_db
    ;;
  migrate)
    ensure_local_db_started
    echo "[local-dev-db] migrate: upgrading canonical local Postgres schema"
    run_alembic_for_local_dev
    ;;
  reset)
    ensure_docker_compose
    echo "[local-dev-db] reset: recreating canonical local Postgres volume"
    run_local_dev_docker_compose down -v --remove-orphans
    ensure_local_db_started
    run_alembic_for_local_dev
    ;;
  status)
    print_local_runtime_summary
    if docker_compose_available; then
      run_local_dev_docker_compose ps
    else
      echo "[local-dev-db] status=docker-compose-unavailable"
    fi
    ;;
  *)
    usage
    exit 1
    ;;
esac
