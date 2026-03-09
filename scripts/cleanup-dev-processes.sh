#!/usr/bin/env bash
set -euo pipefail

APPLY=0
FORCE=0

for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    --force) FORCE=1 ;;
    *)
      echo "[cleanup-dev-processes] fail: unknown argument: ${arg}"
      echo "usage: scripts/cleanup-dev-processes.sh [--apply] [--force]"
      exit 2
      ;;
  esac
done

PATTERN='release-gate-local\.sh|release-gate\.sh|security-gate\.sh|refresh-security-evidence-local\.sh|billing-reconciliation\.sh|pytest -q -p no:cacheprovider|run-test-e2e\.mjs|playwright test|next dev --webpack -H 0\.0\.0\.0'

process_output="$(ps -axo pid,command 2>/dev/null || true)"
if [[ -z "${process_output}" ]]; then
  echo "[cleanup-dev-processes] warning: unable to read process list; skipping"
  exit 0
fi

PROCESS_ROWS=()
while IFS= read -r row; do
  [[ -z "${row}" ]] && continue
  PROCESS_ROWS+=("${row}")
done < <(printf '%s\n' "${process_output}" | rg -e "${PATTERN}" | rg -v "rg -e|cleanup-dev-processes.sh" || true)

if [[ "${#PROCESS_ROWS[@]}" -eq 0 ]]; then
  echo "[cleanup-dev-processes] no matching processes"
  exit 0
fi

echo "[cleanup-dev-processes] matched processes:"
for row in "${PROCESS_ROWS[@]}"; do
  echo "  ${row}"
done

if [[ "${APPLY}" != "1" ]]; then
  echo "[cleanup-dev-processes] dry-run only. Re-run with --apply to terminate."
  exit 0
fi

PIDS=()
for row in "${PROCESS_ROWS[@]}"; do
  pid="$(awk '{print $1}' <<<"${row}")"
  if [[ -n "${pid}" ]]; then
    PIDS+=("${pid}")
  fi
done

if [[ "${#PIDS[@]}" -eq 0 ]]; then
  echo "[cleanup-dev-processes] no pid extracted"
  exit 0
fi

echo "[cleanup-dev-processes] sending SIGTERM to: ${PIDS[*]}"
kill "${PIDS[@]}" 2>/dev/null || true
sleep 1

if [[ "${FORCE}" == "1" ]]; then
  STILL_RUNNING=()
  while IFS= read -r pid; do
    [[ -z "${pid}" ]] && continue
    STILL_RUNNING+=("${pid}")
  done < <(ps -axo pid,command 2>/dev/null | rg -e "${PATTERN}" | rg -v "rg -e|cleanup-dev-processes.sh" | awk '{print $1}' || true)
  if [[ "${#STILL_RUNNING[@]}" -gt 0 ]]; then
    echo "[cleanup-dev-processes] force mode: sending SIGKILL to: ${STILL_RUNNING[*]}"
    kill -9 "${STILL_RUNNING[@]}" 2>/dev/null || true
  fi
fi

echo "[cleanup-dev-processes] done"
