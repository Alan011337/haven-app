#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_PYTHONPATH="${BACKEND_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
source "${BACKEND_DIR}/../scripts/gate-common.sh"

cd "${BACKEND_DIR}"

can_bootstrap_python() {
  local candidate="$1"
  PYTHONUTF8=1 PYTHONPATH="${BACKEND_PYTHONPATH}" "${candidate}" scripts/run_with_timeout.py \
    --timeout-seconds "${SECURITY_GATE_BOOTSTRAP_TIMEOUT_SECONDS:-10}" \
    --heartbeat-seconds "${SECURITY_GATE_BOOTSTRAP_HEARTBEAT_SECONDS:-4}" \
    --step-name "bootstrap_python_preflight" \
    -- "${candidate}" -c "import sys; assert sys.version_info >= (3, 11)" \
    >/dev/null 2>&1
}

if [[ -n "${PYTHON_BIN:-}" ]]; then
  if [[ "${PYTHON_BIN}" == */* ]]; then
    if [[ ! -x "${PYTHON_BIN}" ]]; then
      echo "[security-gate] fail: PYTHON_BIN is not executable: ${PYTHON_BIN}"
      exit 1
    fi
  elif ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "[security-gate] fail: PYTHON_BIN command not found: ${PYTHON_BIN}"
    exit 1
  fi
  if ! can_bootstrap_python "${PYTHON_BIN}"; then
    echo "[security-gate] fail: PYTHON_BIN failed bootstrap preflight: ${PYTHON_BIN}"
    echo "[security-gate] hint: PYTHONUTF8=1 PYTHONPATH=. ${PYTHON_BIN} -c \"import sys; assert sys.version_info >= (3, 11)\""
    exit 1
  fi
else
  for candidate in ".venv-gate/bin/python" "venv/bin/python" "python3" "python"; do
    if [[ "${candidate}" == */* ]] && [[ ! -x "${candidate}" ]]; then
      continue
    fi
    if ! command -v "${candidate}" >/dev/null 2>&1 && [[ "${candidate}" != */* ]]; then
      continue
    fi
    if can_bootstrap_python "${candidate}"; then
      PYTHON_BIN="${candidate}"
      break
    fi
    echo "[security-gate] skip python candidate (preflight failed): ${candidate}"
  done
fi

if [[ -z "${PYTHON_BIN:-}" ]]; then
  echo "[security-gate] fail: no usable python interpreter found."
  echo "[security-gate] hint: set PYTHON_BIN to a working interpreter path."
  exit 1
fi

echo "[security-gate] backend python: ${PYTHON_BIN}"
echo "[security-gate] backend bootstrap: PYTHONUTF8=1, PYTHONPATH includes ${BACKEND_DIR}"
export PYTHONUTF8=1
export PYTHONPATH="${BACKEND_PYTHONPATH}"

SECURITY_GATE_PROFILE="${SECURITY_GATE_PROFILE:-full}"
if [[ "${SECURITY_GATE_PROFILE}" != "full" && "${SECURITY_GATE_PROFILE}" != "fast" ]]; then
  echo "[security-gate] fail: unsupported SECURITY_GATE_PROFILE=${SECURITY_GATE_PROFILE} (expected fast|full)"
  exit 1
fi
echo "[security-gate] profile: ${SECURITY_GATE_PROFILE}"

SECURITY_GATE_STEP_TIMEOUT_SECONDS="${SECURITY_GATE_STEP_TIMEOUT_SECONDS:-240}"
SECURITY_GATE_HEARTBEAT_SECONDS="${SECURITY_GATE_HEARTBEAT_SECONDS:-30}"
SECURITY_GATE_PYTEST_TIMEOUT_SECONDS="${SECURITY_GATE_PYTEST_TIMEOUT_SECONDS:-1200}"
SECURITY_GATE_API_INVENTORY_TIMEOUT_SECONDS="${SECURITY_GATE_API_INVENTORY_TIMEOUT_SECONDS:-300}"
SECURITY_GATE_RETRY_TIMEOUT_ONCE="${SECURITY_GATE_RETRY_TIMEOUT_ONCE:-1}"
SECURITY_GATE_SUMMARY_PATH="${SECURITY_GATE_SUMMARY_PATH:-/tmp/security-gate-summary.ndjson}"

: > "${SECURITY_GATE_SUMMARY_PATH}"
echo "[security-gate] summary_path: ${SECURITY_GATE_SUMMARY_PATH}"

append_step_summary() {
  local step_name="$1"
  local step_kind="$2"
  local exit_code="$3"
  local duration_seconds="$4"
  local status="pass"
  if [[ "${exit_code}" -ne 0 ]]; then
    status="fail"
  fi
  printf '{"step":"%s","kind":"%s","status":"%s","exit_code":%s,"duration_seconds":%s}\n' \
    "${step_name}" "${step_kind}" "${status}" "${exit_code}" "${duration_seconds}" \
    >> "${SECURITY_GATE_SUMMARY_PATH}"
}

run_python_step() {
  local step_name="$1"
  shift
  local timeout_seconds="${SECURITY_GATE_STEP_TIMEOUT_SECONDS}"
  if [[ "${1:-}" == "--timeout" ]]; then
    timeout_seconds="${2:-${SECURITY_GATE_STEP_TIMEOUT_SECONDS}}"
    shift 2
  fi
  local started_at elapsed return_code
  started_at="$(date +%s)"
  set +e
  "${PYTHON_BIN}" scripts/run_with_timeout.py \
    --timeout-seconds "${timeout_seconds}" \
    --heartbeat-seconds "${SECURITY_GATE_HEARTBEAT_SECONDS}" \
    --step-name "${step_name}" \
    -- "${PYTHON_BIN}" "$@"
  return_code=$?
  set -e
  if [[ "${return_code}" -eq 124 && "${SECURITY_GATE_RETRY_TIMEOUT_ONCE}" == "1" ]]; then
    echo "[security-gate] retry once after timeout: step=${step_name}"
    set +e
    "${PYTHON_BIN}" scripts/run_with_timeout.py \
      --timeout-seconds "${timeout_seconds}" \
      --heartbeat-seconds "${SECURITY_GATE_HEARTBEAT_SECONDS}" \
      --step-name "${step_name}_retry" \
      -- "${PYTHON_BIN}" "$@"
    return_code=$?
    set -e
  fi
  elapsed="$(( $(date +%s) - started_at ))"
  append_step_summary "${step_name}" "python" "${return_code}" "${elapsed}"
  return "${return_code}"
}

run_pytest_step() {
  local step_name="$1"
  shift
  local started_at elapsed return_code
  started_at="$(date +%s)"
  set +e
  "${PYTHON_BIN}" scripts/pytest_guard.py \
    --timeout-seconds "${SECURITY_GATE_PYTEST_TIMEOUT_SECONDS}" \
    --heartbeat-seconds "${SECURITY_GATE_HEARTBEAT_SECONDS}" \
    --step-name "${step_name}" \
    -- "$@"
  return_code=$?
  set -e
  if [[ "${return_code}" -eq 124 && "${SECURITY_GATE_RETRY_TIMEOUT_ONCE}" == "1" ]]; then
    echo "[security-gate] retry once after timeout: step=${step_name}"
    set +e
    "${PYTHON_BIN}" scripts/pytest_guard.py \
      --timeout-seconds "${SECURITY_GATE_PYTEST_TIMEOUT_SECONDS}" \
      --heartbeat-seconds "${SECURITY_GATE_HEARTBEAT_SECONDS}" \
      --step-name "${step_name}_retry" \
      -- "$@"
    return_code=$?
    set -e
  fi
  elapsed="$(( $(date +%s) - started_at ))"
  append_step_summary "${step_name}" "pytest" "${return_code}" "${elapsed}"
  return "${return_code}"
}

run_shared_contract_cluster() {
  local include_observability="${1:-0}"
  run_python_step "check_owasp_api_top10_mapping_contract" scripts/check_owasp_api_top10_mapping_contract.py
  run_python_step "check_api_contract_snapshot" scripts/check_api_contract_snapshot.py
  run_python_step "check_frontend_api_transport_contract" scripts/check_frontend_api_transport_contract.py
  run_python_step "check_frontend_security_headers_contract" scripts/check_frontend_security_headers_contract.py
  run_python_step "check_frontend_polling_governance_contract" scripts/check_frontend_polling_governance_contract.py
  run_python_step "check_frontend_test_coverage_floor" scripts/check_frontend_test_coverage_floor.py
  run_python_step "check_env_secret_manifest_contract" scripts/check_env_secret_manifest_contract.py
  run_python_step "check_duplicate_suffix_files" scripts/check_duplicate_suffix_files.py
  run_python_step "check_module_size_budget" scripts/check_module_size_budget.py
  run_python_step "check_runtime_switch_contract" scripts/check_runtime_switch_contract.py
  run_python_step "check_idempotency_normalization_contract" scripts/check_idempotency_normalization_contract.py
  run_python_step "check_event_tracking_privacy_contract" scripts/check_event_tracking_privacy_contract.py
  run_python_step "check_event_registry_contract" scripts/check_event_registry_contract.py
  run_python_step "check_core_loop_event_contract" scripts/check_core_loop_event_contract.py
  run_python_step "check_supply_chain_workflow_contract" scripts/check_supply_chain_workflow_contract.py
  if [[ "${include_observability}" == "1" ]]; then
    run_python_step "check_observability_live_contract" scripts/check_observability_live_contract.py \
      --health-slo-url "${SLO_GATE_HEALTH_SLO_URL:-}" \
      --bearer-token "${SLO_GATE_BEARER_TOKEN:-}" \
      --allow-missing-url \
      --summary-path /tmp/observability-live-contract-summary.json
  fi
  run_python_step "check_feature_flag_governance_contract" scripts/check_feature_flag_governance_contract.py
  run_python_step "check_endpoint_authorization_matrix" scripts/check_endpoint_authorization_matrix.py
  run_python_step "check_read_authorization_matrix" scripts/check_read_authorization_matrix.py
  run_python_step "check_data_rights_contract" scripts/check_data_rights_contract.py
  run_python_step "check_ai_router_policy_contract" scripts/check_ai_router_policy_contract.py
  run_python_step "check_store_compliance_contract" scripts/check_store_compliance_contract.py
  run_python_step "check_cuj_synthetic_contract" scripts/check_cuj_synthetic_contract.py
}

run_fast_pytest_contract_suite() {
  run_pytest_step "security_gate_fast_pytest" -q -p no:cacheprovider \
    tests/security/test_bola_matrix.py \
    tests/security/test_bola_subject_matrix.py \
    tests/test_security_gate_contract.py \
    tests/test_env_secret_manifest_contract.py \
    tests/test_duplicate_suffix_files_contract.py \
    tests/test_cleanup_dev_processes_script_contract.py \
    tests/test_dev_doctor_script_contract.py \
    tests/test_module_size_budget_contract.py \
    tests/test_generate_env_secret_manifest_script_contract.py \
    tests/test_idempotency_normalization_contract.py \
    tests/test_frontend_api_transport_contract.py \
    tests/test_frontend_security_headers_contract.py \
    tests/test_event_tracking_privacy_contract.py \
    tests/test_event_registry_contract.py \
    tests/test_core_loop_event_contract.py \
    tests/test_supply_chain_workflow_contract.py \
    tests/test_observability_live_contract_script.py \
    tests/test_feature_flag_governance_contract.py \
    tests/test_frontend_idempotency_helper_contract.py \
    tests/test_frontend_timeline_loadmore_guard_contract.py \
    tests/test_health_endpoint.py \
    tests/test_structured_logging_contract.py \
    tests/test_ai_router_metrics.py \
    tests/test_offline_idempotency_normalization.py \
    tests/test_timeline_runtime_metrics.py \
    tests/test_timeline_runtime_alert_gate_script.py \
    tests/test_api_idempotency_migration_contract.py \
    tests/test_api_idempotency_persistence.py \
    tests/test_events_log_rollup.py \
    tests/test_events_log_rollup_script.py \
    tests/test_events_log_lifecycle_script.py \
    tests/test_events_ingest_guard_store.py \
    tests/test_memory_timeline_query_count_guard.py \
    tests/test_rate_limit_scope_builder.py \
    tests/test_test_profile_script_contract.py \
    tests/test_migration_rehearsal_report_script.py \
    tests/test_pytest_guard_script.py \
    tests/test_memory_timeline_date_range_filters.py \
    tests/test_health_ws_sli.py \
    tests/test_socket_manager_backpressure.py \
    tests/test_ws_abuse_guard.py \
    tests/test_ai_router_degraded_chaos.py \
    tests/test_worker_lock_state.py \
    tests/test_billing_router_structure.py \
    tests/test_users_router_structure.py \
    tests/test_notification_outbox_maintenance_script.py \
    tests/test_notification_outbox_dead_replay_audit_script.py \
    tests/test_notification_outbox_health_snapshot_script.py \
    tests/test_notification_outbox_self_heal_workflow_contract.py \
    tests/test_oncall_runtime_snapshot_script.py \
    tests/test_router_registration_contract.py \
    tests/test_clean_evidence_noise_script_contract.py \
    tests/test_read_authorization_matrix_export_script.py
}

if [[ "${SECURITY_GATE_SKIP_IMPORT_SMOKE:-0}" == "1" ]]; then
  echo "[security-gate] skip import smoke (SECURITY_GATE_SKIP_IMPORT_SMOKE=1)"
else
  echo "[security-gate] import smoke: app.main"
  run_python_step "import_smoke_app_main" -c "import app.main"
fi

if [[ "${SECURITY_GATE_SKIP_CRITICAL_RUFF:-0}" == "1" ]]; then
  echo "[security-gate] skip critical ruff gate (SECURITY_GATE_SKIP_CRITICAL_RUFF=1)"
else
  if ! command -v ruff >/dev/null 2>&1; then
    echo "[security-gate] fail: ruff is required for critical lint gate."
    echo "[security-gate] hint: install ruff or set SECURITY_GATE_SKIP_CRITICAL_RUFF=1 for local debugging only."
    exit 1
  fi
  echo "[security-gate] critical lint gate (F821/F841/E9)"
  ruff check . --select F821,F841,E9 --output-format concise
fi

if [[ "${API_INVENTORY_AUTO_WRITE:-0}" == "1" ]]; then
  echo "[security-gate] api inventory: auto-write enabled"
  run_python_step "api_inventory_write" --timeout "${SECURITY_GATE_API_INVENTORY_TIMEOUT_SECONDS}" scripts/export_api_inventory.py --write --emit-timings
else
run_python_step "api_inventory_check" --timeout "${SECURITY_GATE_API_INVENTORY_TIMEOUT_SECONDS}" scripts/export_api_inventory.py --check --emit-timings
fi
run_python_step "export_endpoint_authz_matrix" scripts/export_endpoint_authorization_matrix.py --check-current
run_python_step "export_read_authz_matrix" scripts/export_read_authorization_matrix.py --check-current
run_python_step "check_file_hygiene_contract" scripts/check_file_hygiene_contract.py
run_python_step "export_memory_timeline_query_baseline" scripts/export_memory_timeline_query_baseline.py --output /tmp/memory-timeline-query-baseline.json --fail-on-missing-index --fail-on-date-function --fail-on-full-scan
run_python_step "check_gate_consistency_contract" scripts/check_gate_consistency_contract.py
run_python_step "check_security_gate_steps_manifest" scripts/check_security_gate_steps_manifest.py
run_python_step "check_deploy_source_of_truth" scripts/check_deploy_source_of_truth.py

if [[ "${SECURITY_GATE_PROFILE}" == "fast" ]]; then
  echo "[security-gate] fast profile: running core policy checks"
  run_shared_contract_cluster
  run_fast_pytest_contract_suite
  exit 0
fi

run_python_step "check_function_level_authorization" scripts/check_function_level_authorization.py
run_shared_contract_cluster 1
run_python_step "check_data_retention_contract" scripts/check_data_retention_contract.py
run_python_step "check_data_classification_contract" scripts/check_data_classification_contract.py
run_python_step "check_data_deletion_lifecycle_contract" scripts/check_data_deletion_lifecycle_contract.py
run_python_step "check_api_inventory_owner_attestation" scripts/check_api_inventory_owner_attestation.py
run_python_step "check_threat_model_contract" scripts/check_threat_model_contract.py
run_python_step "check_abuse_economics_contract" scripts/check_abuse_economics_contract.py
run_python_step "check_prompt_abuse_policy_contract" scripts/check_prompt_abuse_policy_contract.py
run_python_step "check_encryption_posture_contract" scripts/check_encryption_posture_contract.py
run_python_step "check_consent_receipt_contract" scripts/check_consent_receipt_contract.py
run_python_step "check_prompt_rollout_policy_contract" scripts/check_prompt_rollout_policy_contract.py
run_python_step "check_ai_persona_policy_contract" scripts/check_ai_persona_policy_contract.py
run_python_step "check_ai_cost_quality_policy_contract" scripts/check_ai_cost_quality_policy_contract.py
run_python_step "check_ai_eval_framework_contract" scripts/check_ai_eval_framework_contract.py
run_python_step "check_ai_eval_release_gate" scripts/check_ai_eval_release_gate.py
run_python_step "run_hybrid_eval_report" scripts/run_hybrid_eval_report.py --output /tmp/hybrid-eval-report.json
run_python_step "check_prompt_rollout_stop_loss" scripts/check_prompt_rollout_stop_loss.py
run_python_step "check_admin_least_privilege" scripts/check_admin_least_privilege.py
run_python_step "check_billing_edge_policy_contract" scripts/check_billing_edge_policy_contract.py
run_python_step "check_store_enforcement_hooks_contract" scripts/check_store_enforcement_hooks_contract.py
run_python_step "check_ai_eval_scenario_matrix_contract" scripts/check_ai_eval_scenario_matrix_contract.py
run_python_step "check_ai_eval_golden_set_contract" scripts/check_ai_eval_golden_set_contract.py
run_python_step "check_store_compliance_doc_contract" scripts/check_store_compliance_doc_contract.py
run_python_step "check_billing_grace_account_hold_policy_contract" scripts/check_billing_grace_account_hold_policy_contract.py
run_python_step "check_pricing_experiment_policy_contract" scripts/check_pricing_experiment_policy_contract.py
run_python_step "check_growth_kill_switch_coverage_contract" scripts/check_growth_kill_switch_coverage_contract.py
run_python_step "check_sre_tier_policy_contract" scripts/check_sre_tier_policy_contract.py
run_python_step "check_abuse_model_contract" scripts/check_abuse_model_contract.py
run_python_step "check_safety_ui_policy_contract" scripts/check_safety_ui_policy_contract.py
run_python_step "check_legal_compliance_bundle_contract" scripts/check_legal_compliance_bundle_contract.py
run_python_step "check_secrets_key_management_contract" scripts/check_secrets_key_management_contract.py
run_python_step "check_cuj_synthetic_evidence_gate" scripts/check_cuj_synthetic_evidence_gate.py --allow-missing-evidence
run_python_step "validate_security_evidence_p0_drill" scripts/validate_security_evidence.py \
  --kind p0-drill \
  --contract-mode strict \
  --max-age-days "${P0_DRILL_EVIDENCE_MAX_AGE_DAYS:-35}"
run_python_step "validate_security_evidence_data_rights_fire_drill" scripts/validate_security_evidence.py \
  --kind data-rights-fire-drill \
  --contract-mode strict \
  --max-age-days "${DATA_RIGHTS_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS:-35}"
run_python_step "validate_security_evidence_billing_fire_drill" scripts/validate_security_evidence.py \
  --kind billing-fire-drill \
  --contract-mode strict \
  --max-age-days "${BILLING_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS:-35}"
run_python_step "validate_security_evidence_billing_reconciliation" scripts/validate_security_evidence.py \
  --kind billing-reconciliation \
  --contract-mode strict \
  --max-age-days "${BILLING_RECON_EVIDENCE_MAX_AGE_DAYS:-14}"
run_python_step "validate_security_evidence_billing_console_drift" scripts/validate_security_evidence.py \
  --kind billing-console-drift \
  --contract-mode strict \
  --max-age-days "${BILLING_CONSOLE_DRIFT_EVIDENCE_MAX_AGE_DAYS:-14}"
run_python_step "validate_security_evidence_audit_log_retention" scripts/validate_security_evidence.py \
  --kind audit-log-retention \
  --contract-mode strict \
  --max-age-days "${AUDIT_RETENTION_EVIDENCE_MAX_AGE_DAYS:-14}"
run_python_step "validate_security_evidence_data_soft_delete_purge" scripts/validate_security_evidence.py \
  --kind data-soft-delete-purge \
  --contract-mode strict \
  --max-age-days "${DATA_SOFT_DELETE_PURGE_EVIDENCE_MAX_AGE_DAYS:-14}"
run_python_step "validate_security_evidence_key_rotation_drill" scripts/validate_security_evidence.py \
  --kind key-rotation-drill \
  --contract-mode strict \
  --max-age-days "${KEY_ROTATION_DRILL_EVIDENCE_MAX_AGE_DAYS:-35}"
run_python_step "validate_security_evidence_data_restore_drill" scripts/validate_security_evidence.py \
  --kind data-restore-drill \
  --contract-mode strict \
  --max-age-days "${DATA_RESTORE_DRILL_EVIDENCE_MAX_AGE_DAYS:-35}"
run_python_step "validate_security_evidence_backup_restore_drill" scripts/validate_security_evidence.py \
  --kind backup-restore-drill \
  --contract-mode strict \
  --max-age-days "${BACKUP_RESTORE_DRILL_EVIDENCE_MAX_AGE_DAYS:-120}"
run_python_step "validate_security_evidence_chaos_drill" scripts/validate_security_evidence.py \
  --kind chaos-drill \
  --contract-mode strict \
  --max-age-days "${CHAOS_DRILL_EVIDENCE_MAX_AGE_DAYS:-14}"

echo "[security-gate] EVAL-01 golden set gate"
run_python_step "run_ai_eval_golden_set_snapshot" scripts/run_ai_eval_golden_set_snapshot.py \
  --results ../docs/security/ai-eval-golden-set-results.json \
  --output /tmp/ai-eval-golden-set-snapshot.json \
  --latest-path /tmp/ai-eval-golden-set-latest.json \
  --summary-path /tmp/ai-eval-golden-set-summary.json \
  --fail-on-degraded

run_pytest_step "security_gate_full_pytest" -q -p no:cacheprovider \
  tests/security/test_bola_matrix.py \
  tests/security/test_bola_subject_matrix.py \
  tests/test_api_inventory_contract.py \
  tests/test_api_contract_snapshot_gate.py \
  tests/test_function_level_authorization_policy.py \
  tests/test_owasp_api_top10_mapping_contract_policy.py \
  tests/test_endpoint_authorization_matrix_policy.py \
  tests/test_read_authorization_matrix_policy.py \
  tests/test_data_rights_contract_policy.py \
  tests/test_data_retention_contract_policy.py \
  tests/test_data_classification_contract_policy.py \
  tests/test_data_deletion_lifecycle_contract_policy.py \
  tests/test_threat_model_contract_policy.py \
  tests/test_abuse_economics_contract_policy.py \
  tests/test_prompt_abuse_policy_contract.py \
  tests/test_encryption_posture_contract_policy.py \
  tests/test_consent_receipt_contract_policy.py \
  tests/test_prompt_rollout_policy_contract.py \
  tests/test_ai_persona_policy_contract.py \
  tests/test_ai_router_policy_contract.py \
  tests/test_ai_cost_quality_policy_contract.py \
  tests/test_ai_eval_framework_contract_policy.py \
  tests/test_ai_eval_scenario_matrix_contract_policy.py \
  tests/test_ai_eval_golden_set_contract_policy.py \
  tests/test_ai_eval_golden_set_snapshot_script.py \
  tests/test_ai_eval_scenario_matrix_snapshot_script.py \
  tests/test_store_compliance_contract_policy.py \
  tests/test_billing_grace_account_hold_policy_contract.py \
  tests/test_pricing_experiment_policy_contract.py \
  tests/test_growth_kill_switch_coverage_contract.py \
  tests/test_pricing_experiment_dry_run.py \
  tests/test_pricing_experiment_runtime.py \
  tests/test_pricing_experiment_guardrail_snapshot.py \
  tests/test_pricing_experiment_guardrail_workflow_contract.py \
  tests/test_core_loop_snapshot_workflow_contract.py \
  tests/test_events_log_retention.py \
  tests/test_events_log_rollup.py \
  tests/test_events_log_retention_script.py \
  tests/test_events_log_rollup_script.py \
  tests/test_events_log_lifecycle_script.py \
  tests/test_events_log_retention_workflow_contract.py \
  tests/test_abuse_model_contract_policy.py \
  tests/test_safety_ui_policy_contract.py \
  tests/test_legal_compliance_bundle_contract_policy.py \
  tests/test_secrets_key_management_contract_policy.py \
  tests/test_cuj_synthetic_contract_policy.py \
  tests/test_cuj_synthetic_evidence_gate.py \
  tests/test_release_gate_workflow_contract.py \
  tests/test_api_v2_envelope_contract.py \
  tests/test_security_gate_contract.py \
  tests/test_env_secret_manifest_contract.py \
  tests/test_duplicate_suffix_files_contract.py \
  tests/test_cleanup_dev_processes_script_contract.py \
  tests/test_dev_doctor_script_contract.py \
  tests/test_module_size_budget_contract.py \
  tests/test_generate_env_secret_manifest_script_contract.py \
  tests/test_idempotency_normalization_contract.py \
  tests/test_structured_logging_contract.py \
  tests/test_ai_router_metrics.py \
  tests/test_offline_idempotency_normalization.py \
  tests/test_timeline_runtime_metrics.py \
  tests/test_timeline_runtime_alert_gate_script.py \
  tests/test_notification_outbox_health_snapshot_script.py \
  tests/test_notification_outbox_self_heal_workflow_contract.py \
  tests/test_router_registration_contract.py \
  tests/test_clean_evidence_noise_script_contract.py \
  tests/test_quick_backend_contract_summary_gate.py \
  tests/test_frontend_e2e_summary_schema_gate_script.py \
  tests/test_frontend_e2e_summary_contract.py \
  tests/test_frontend_e2e_summary_script.py \
  tests/test_frontend_api_transport_contract.py \
  tests/test_event_tracking_privacy_contract.py \
  tests/test_core_loop_event_contract.py \
  tests/test_supply_chain_workflow_contract.py \
  tests/test_observability_live_contract_script.py \
  tests/test_feature_flag_governance_contract.py \
  tests/test_frontend_idempotency_helper_contract.py \
  tests/test_frontend_timeline_loadmore_guard_contract.py \
  tests/test_release_gate_override_contract.py \
  tests/test_api_idempotency_migration_contract.py \
  tests/test_api_idempotency_persistence.py \
  tests/test_ai_quality_snapshot_workflow_contract.py \
  tests/test_data_soft_delete_purge_service.py \
  tests/test_api_inventory_owner_attestation_policy.py \
  tests/test_admin_authorization_matrix.py \
  tests/test_user_authorization_matrix.py \
  tests/test_user_pairing_authorization_matrix.py \
  tests/test_auth_token_endpoint_security.py \
  tests/test_journal_authorization_matrix.py \
  tests/test_card_authorization_matrix.py \
  tests/test_card_read_authorization_matrix.py \
  tests/test_card_resource_consumption_guard.py \
  tests/test_card_deck_resource_consumption_guard.py \
  tests/test_memory_timeline_query_count_guard.py \
  tests/test_rate_limit_scope_dimensions.py \
  tests/test_rate_limit_scope_builder.py \
  tests/test_card_deck_authorization_matrix.py \
  tests/test_auth_token_misuse_regression.py \
  tests/test_auth_token_misuse_write_paths.py \
  tests/test_security_evidence_validation.py \
  tests/test_security_evidence_utils.py \
  tests/test_billing_console_drift_audit.py \
  tests/test_billing_console_drift_workflow_contract.py \
  tests/test_key_rotation_drill_audit.py \
  tests/test_data_restore_drill_audit.py \
  tests/test_backup_restore_drill_audit.py \
  tests/test_backup_restore_drill_workflow_contract.py \
  tests/test_chaos_drill_audit.py \
  tests/test_chaos_drill_workflow_contract.py \
  tests/test_launch_signoff_gate.py \
  tests/test_slo_burn_rate_gate.py \
  tests/test_canary_guard.py \
  tests/test_user_field_level_authorization.py \
  tests/test_websocket_auth_guard.py \
  tests/test_security_headers.py \
  tests/test_audit_log_baseline.py \
  tests/test_audit_log_security_controls.py \
  tests/test_audit_log_billing_notification_controls.py \
  tests/test_abuse_budget_policy.py \
  tests/test_push_abuse_budget_policy.py \
  tests/test_abuse_economics_runtime.py \
  tests/test_push_sli_runtime.py \
  tests/test_rate_limit_runtime_metrics.py \
  tests/test_health_endpoint.py \
  tests/test_cuj_sli_runtime.py \
  tests/test_billing_idempotency_api.py \
  tests/test_billing_authorization_matrix.py \
  tests/test_billing_webhook_security.py \
  tests/test_users_router_structure.py \
  tests/test_billing_entitlement_parity.py \
  tests/test_cuj_event_ingest_api.py \
  tests/test_events_ingest_guard_store.py \
  tests/test_cuj_synthetics.py \
  tests/test_data_rights_api.py \
  tests/test_field_level_encryption.py \
  tests/test_user_consent_receipt_api.py \
  tests/test_onboarding_quest_api.py \
  tests/test_first_delight_api.py \
  tests/test_sync_nudges_api.py \
  tests/test_notification_authorization_matrix.py \
  tests/test_notification_api.py \
  tests/test_notification_outbox.py \
  tests/test_notification_outbox_migration.py \
  tests/test_notification_outbox_recovery_script.py \
  tests/test_notification_outbox_dispatch_script.py \
  tests/test_notification_outbox_dead_replay_audit_script.py \
  tests/test_oncall_runtime_snapshot_script.py \
  tests/test_timeline_hot_path_indexes_migration.py \
  tests/test_notification_multichannel_runtime.py \
  tests/test_runtime_metrics_cardinality_guard.py \
  tests/test_dynamic_content_pipeline.py \
  tests/test_perf_baseline_script.py \
  tests/test_journal_notification_rules.py::JournalNotificationRulesTests::test_create_journal_rate_limited_by_ip_dimension \
  tests/test_journal_notification_rules.py::JournalNotificationRulesTests::test_create_journal_rate_limited_by_device_dimension \
  tests/test_journal_notification_rules.py::JournalNotificationRulesTests::test_create_journal_rate_limited_by_partner_pair_dimension \
  tests/test_card_mode_isolation.py::CardModeIsolationTests::test_cards_respond_rate_limited_by_ip_dimension \
  tests/test_card_mode_isolation.py::CardModeIsolationTests::test_cards_respond_rate_limited_by_device_dimension \
  tests/test_card_mode_isolation.py::CardModeIsolationTests::test_deck_respond_rate_limited_by_partner_pair_dimension \
  tests/test_card_mode_isolation.py::CardModeIsolationTests::test_deck_respond_rejects_non_participant \
  tests/test_log_redaction.py \
  tests/test_ai_schema_contract.py \
  tests/test_ai_safety_logic.py \
  tests/test_ai_schema_fuzz.py \
  tests/test_prompt_abuse_policy.py \
  tests/test_ai_persona.py \
  tests/test_ai_router.py \
  tests/test_ai_router_runtime.py \
  tests/test_ai_router_degraded_chaos.py \
  tests/test_ai_gemini_adapter.py \
  tests/test_ai_provider_fallback_integration.py \
  tests/test_ai_quality_monitor.py \
  tests/test_ai_eval_drift_detector_script.py \
  tests/test_fetch_latest_ai_quality_snapshot_evidence.py \
  tests/test_ai_quality_snapshot_script.py \
  tests/test_ai_quality_snapshot_freshness_gate.py \
  tests/test_safety_regression.py \
  tests/test_ai_safety_redteam.py \
  tests/test_prompt_supply_chain.py \
  tests/test_ai_eval_release_gate.py \
  tests/test_hybrid_eval_report.py \
  tests/test_prompt_rollout_stop_loss.py \
  tests/test_admin_least_privilege.py \
  tests/test_billing_edge_policy_contract.py \
  tests/test_store_enforcement_hooks_contract.py \
  tests/test_test_profile_script_contract.py \
  tests/test_migration_rehearsal_report_script.py
