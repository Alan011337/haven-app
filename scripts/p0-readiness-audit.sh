#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
EVIDENCE_DIR="${ROOT_DIR}/docs/security/evidence"
RUN_RUNTIME_GATES="${RUN_RUNTIME_GATES:-0}"
P0_READINESS_MODE="${P0_READINESS_MODE:-contract}" # contract | checklist
CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS="${CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS:-36}"
P0_READINESS_LOG_DIR="${P0_READINESS_LOG_DIR:-/tmp/p0-readiness-audit}"

mkdir -p "${EVIDENCE_DIR}"
mkdir -p "${P0_READINESS_LOG_DIR}"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
report_path="${EVIDENCE_DIR}/p0-readiness-${timestamp}.json"
latest_path="${EVIDENCE_DIR}/p0-readiness-latest.json"

declare -a check_ids=()
declare -a check_statuses=()
declare -a check_details=()
declare -a release_open_lines=()
declare -a release_open_texts=()
declare -a launch_open_lines=()
declare -a launch_open_texts=()

add_check() {
  local id="$1"
  local status="$2"
  local detail="$3"
  check_ids+=("${id}")
  check_statuses+=("${status}")
  check_details+=("${detail}")
}

run_contract_check() {
  local check_id="$1"
  local description="$2"
  shift 2
  local log_path="${P0_READINESS_LOG_DIR}/${check_id}.log"
  if "$@" >"${log_path}" 2>&1; then
    add_check "${check_id}" "pass" "${description} (log: ${log_path})"
    return 0
  fi
  add_check "${check_id}" "fail" "${description} failed (log: ${log_path})"
  return 1
}

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

collect_release_open_items() {
  while IFS= read -r raw; do
    [[ -z "${raw}" ]] && continue
    release_open_lines+=("${raw%%|*}")
    release_open_texts+=("$(printf '%s' "${raw#*|}" | sed 's/[[:space:]]*$//')")
  done < <(awk '/^- \[ \]/{print NR "|" $0}' "${ROOT_DIR}/RELEASE_CHECKLIST.md")
}

collect_launch_open_items() {
  while IFS= read -r raw; do
    [[ -z "${raw}" ]] && continue
    launch_open_lines+=("${raw%%|*}")
    launch_open_texts+=("$(printf '%s' "${raw#*|}" | sed 's/[[:space:]]*$//')")
  done < <(awk '/^\| ☐ \|/{print NR "|" $0}' "${ROOT_DIR}/docs/P0-LAUNCH-GATE.md")
}

collect_release_open_items
collect_launch_open_items

release_open_items="${#release_open_lines[@]}"
launch_open_items="${#launch_open_lines[@]}"

if [[ "${P0_READINESS_MODE}" == "checklist" ]]; then
  if [[ "${release_open_items}" == "0" ]]; then
    add_check "release_checklist_complete" "pass" "RELEASE_CHECKLIST has no open items"
  else
    add_check "release_checklist_complete" "fail" "RELEASE_CHECKLIST has ${release_open_items} open items"
  fi

  if [[ "${launch_open_items}" == "0" ]]; then
    add_check "launch_gate_complete" "pass" "P0 launch gate has no unchecked items"
  else
    add_check "launch_gate_complete" "fail" "P0 launch gate has ${launch_open_items} unchecked items"
  fi
else
  run_contract_check \
    "release_checklist_complete" \
    "backend security gate passed; release checklist open items=${release_open_items} (non-blocking in contract mode)" \
    env PYTHONUTF8=1 PYTHONPATH="${ROOT_DIR}/backend${PYTHONPATH:+:${PYTHONPATH}}" bash -lc "cd '${ROOT_DIR}/backend' && ./scripts/security-gate.sh"

  run_contract_check \
    "launch_gate_complete" \
    "launch contract gates passed (strict CUJ evidence + override contract); launch gate open items=${launch_open_items} (non-blocking in contract mode)" \
    env PYTHONUTF8=1 PYTHONPATH="${ROOT_DIR}/backend${PYTHONPATH:+:${PYTHONPATH}}" bash -lc "cd '${ROOT_DIR}/backend' && .venv-gate/bin/python scripts/check_release_gate_override_contract.py && .venv-gate/bin/python scripts/check_cuj_synthetic_evidence_gate.py --require-pass --max-age-hours '${CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS}'"
fi

run_contract_check \
  "store_compliance_contract_passed" \
  "store compliance contract passed (BILL-STORE-01)" \
  env PYTHONUTF8=1 PYTHONPATH="${ROOT_DIR}/backend${PYTHONPATH:+:${PYTHONPATH}}" bash -lc "cd '${ROOT_DIR}/backend' && if [[ -x .venv-gate/bin/python ]]; then .venv-gate/bin/python scripts/check_store_compliance_contract.py; elif [[ -x venv/bin/python ]]; then venv/bin/python scripts/check_store_compliance_contract.py; else python3 scripts/check_store_compliance_contract.py; fi"

if [[ "${RUN_RUNTIME_GATES}" == "1" ]]; then
  if RELEASE_GATE_ALLOW_MISSING_LAUNCH_SIGNOFF=1 \
    RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE=1 \
    RELEASE_GATE_HOTFIX_OVERRIDE=1 \
    RELEASE_GATE_OVERRIDE_REASON="P0-READINESS-AUDIT" \
    LAUNCH_SIGNOFF_ARTIFACT_PATH="/tmp/nonexistent-launch-signoff.json" \
    E2E_ALLOW_BROWSER_DOWNLOAD_FAILURE=1 \
    bash "${ROOT_DIR}/scripts/release-gate-local.sh"; then
    add_check "release_gate_local_runtime" "pass" "release-gate-local.sh passed"
  else
    add_check "release_gate_local_runtime" "fail" "release-gate-local.sh failed"
  fi
else
  add_check "release_gate_local_runtime" "skip" "RUN_RUNTIME_GATES=1 to execute runtime gate"
fi

overall_ready="true"
for status in "${check_statuses[@]}"; do
  if [[ "${status}" == "fail" ]]; then
    overall_ready="false"
    break
  fi
done

{
  printf '{\n'
  printf '  "generated_at_utc": "%s",\n' "${timestamp}"
  printf '  "run_runtime_gates": %s,\n' "$([[ "${RUN_RUNTIME_GATES}" == "1" ]] && echo "true" || echo "false")"
  printf '  "overall_ready": %s,\n' "${overall_ready}"
  printf '  "checks": [\n'

  for i in "${!check_ids[@]}"; do
    id_escaped="$(json_escape "${check_ids[$i]}")"
    status_escaped="$(json_escape "${check_statuses[$i]}")"
    detail_escaped="$(json_escape "${check_details[$i]}")"
    comma=","
    if [[ "${i}" -eq "$((${#check_ids[@]} - 1))" ]]; then
      comma=""
    fi
    printf '    {"id":"%s","status":"%s","detail":"%s"}%s\n' \
      "${id_escaped}" "${status_escaped}" "${detail_escaped}" "${comma}"
  done

  printf '  ],\n'
  printf '  "open_items": {\n'
  printf '    "release_checklist": [\n'

  for i in "${!release_open_lines[@]}"; do
    text_escaped="$(json_escape "${release_open_texts[$i]}")"
    comma=","
    if [[ "${i}" -eq "$((${#release_open_lines[@]} - 1))" ]]; then
      comma=""
    fi
    printf '      {"file":"RELEASE_CHECKLIST.md","line":%s,"text":"%s"}%s\n' \
      "${release_open_lines[$i]}" "${text_escaped}" "${comma}"
  done

  printf '    ],\n'
  printf '    "launch_gate": [\n'

  for i in "${!launch_open_lines[@]}"; do
    text_escaped="$(json_escape "${launch_open_texts[$i]}")"
    comma=","
    if [[ "${i}" -eq "$((${#launch_open_lines[@]} - 1))" ]]; then
      comma=""
    fi
    printf '      {"file":"docs/P0-LAUNCH-GATE.md","line":%s,"text":"%s"}%s\n' \
      "${launch_open_lines[$i]}" "${text_escaped}" "${comma}"
  done

  printf '    ]\n'
  printf '  }\n'
  printf '}\n'
} > "${report_path}"

cp "${report_path}" "${latest_path}"

echo "[p0-readiness-audit] report: ${report_path}"
echo "[p0-readiness-audit] latest: ${latest_path}"
echo "[p0-readiness-audit] overall_ready: ${overall_ready}"
for i in "${!check_ids[@]}"; do
  echo "  - ${check_ids[$i]}: ${check_statuses[$i]} (${check_details[$i]})"
done

if [[ "${release_open_items}" -gt 0 ]]; then
  echo "[p0-readiness-audit] first open release checklist items:"
  preview_count=5
  if [[ "${release_open_items}" -lt "${preview_count}" ]]; then
    preview_count="${release_open_items}"
  fi
  for ((i = 0; i < preview_count; i++)); do
    echo "    - RELEASE_CHECKLIST.md:${release_open_lines[$i]} ${release_open_texts[$i]}"
  done
fi

if [[ "${launch_open_items}" -gt 0 ]]; then
  echo "[p0-readiness-audit] first open launch gate items:"
  preview_count=5
  if [[ "${launch_open_items}" -lt "${preview_count}" ]]; then
    preview_count="${launch_open_items}"
  fi
  for ((i = 0; i < preview_count; i++)); do
    echo "    - docs/P0-LAUNCH-GATE.md:${launch_open_lines[$i]} ${launch_open_texts[$i]}"
  done
fi

if [[ "${overall_ready}" == "true" ]]; then
  exit 0
fi
exit 1
