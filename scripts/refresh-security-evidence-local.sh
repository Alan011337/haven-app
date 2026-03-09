#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

run_step() {
  local label="$1"
  local cmd="$2"
  echo "[refresh-security-evidence-local] ${label}"
  bash -lc "${cmd}"
}

REFRESH_CUJ_EVIDENCE="${REFRESH_CUJ_EVIDENCE:-1}"
REFRESH_BILLING_RECON_EVIDENCE="${REFRESH_BILLING_RECON_EVIDENCE:-1}"
REFRESH_AUDIT_RETENTION_EVIDENCE="${REFRESH_AUDIT_RETENTION_EVIDENCE:-1}"

if [[ "${REFRESH_CUJ_EVIDENCE}" == "1" ]]; then
  run_step \
    "refresh cuj synthetic evidence" \
    "cd \"${ROOT_DIR}\" && bash scripts/generate-cuj-synthetic-evidence-local.sh"
fi

if [[ "${REFRESH_BILLING_RECON_EVIDENCE}" == "1" ]]; then
  run_step \
    "refresh billing reconciliation evidence" \
    "cd \"${ROOT_DIR}\" && bash scripts/billing-reconciliation.sh"
fi

if [[ "${REFRESH_AUDIT_RETENTION_EVIDENCE}" == "1" ]]; then
  run_step \
    "refresh audit-log retention evidence" \
    "cd \"${ROOT_DIR}\" && bash scripts/audit-log-retention.sh"
fi

echo "[refresh-security-evidence-local] result: pass"
