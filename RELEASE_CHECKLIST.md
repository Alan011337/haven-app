# Haven Release Checklist

## SLO / Reliability Gates
- [ ] `backend/scripts/check_slo_burn_rate_gate.py` passed.
  - verify `ws`, `ws_burn_rate`, `cuj` statuses are not degraded.
  - on `main` / protected release branches, enforce `--require-sufficient-data` (insufficient data must fail).
  - verify `abuse_economics` status is not `block` (or set `SLO_GATE_FAIL_ON_ABUSE_WARN=true` for strict warn blocking).
  - if local run lacks monitoring URL, provide `SLO_GATE_HEALTH_SLO_FILE` and confirm summary `source_type=file`.
- [ ] `backend/scripts/check_error_budget_freeze_gate.py` passed.
- [ ] `backend/scripts/check_launch_signoff_gate.py` passed (artifact fresh).
- [ ] `backend/scripts/check_cuj_synthetic_evidence_gate.py` passed (synthetic evidence fresh + contract-valid).
- [ ] `backend/scripts/check_ai_quality_snapshot_freshness_gate.py` passed (`degraded` allowed, stale/missing invalid evidence must fail).
- [ ] Canary guard plan validated (`docs/sre/canary.md`).

## Security Gates
- [ ] `backend/scripts/security-gate.sh` passed.
- [ ] API authz matrix tests passed (BOLA focus).
- [ ] Field-level encryption guard passed (`FIELD_LEVEL_ENCRYPTION_ENABLED=true` + valid `FIELD_LEVEL_ENCRYPTION_KEY` in prod).
- [ ] No new sensitive log regressions.
- [ ] `bash scripts/key-rotation-drill.sh` passed and `key-rotation-drill` evidence is fresh.

## Billing Correctness Gates
- [ ] Billing webhook signature/idempotency tests passed.
- [ ] Reconciliation audit script passed.
- [ ] Ledger/entitlement consistency verified.
- [ ] Store compliance contract passed (`backend/scripts/check_store_compliance_contract.py`) and launch signoff artifact includes `store_compliance_contract_passed`.
- [ ] Grace/account-hold policy contract passed (`backend/scripts/check_billing_grace_account_hold_policy_contract.py`) and provider hold/recovery tests stay green.

## Data Rights / Legal
- [ ] Access/export/erase drill evidence fresh and valid.
- [ ] Deletion lifecycle policy checks passed.

## Release Safety
- [ ] Rollback path documented for this release.
- [ ] Feature flags prepared for new high-risk paths.
- [ ] Notification outbox replay drill verified (optional preflight):
  - `python backend/scripts/run_notification_outbox_dispatch.py --replay-dead --replay-limit 20 --reset-attempt-count --replay-only`
- [ ] Events retention dry-run reviewed:
  - `python backend/scripts/run_events_log_retention.py --retention-days 120 --batch-size 2000`
- [ ] Events retention apply preflight contract validated (only if apply is needed):
  - `python backend/scripts/run_events_log_retention.py --retention-days 120 --batch-size 500 --apply --confirm-apply events-log-retention-apply --expected-cutoff-unix <dry-run-cutoff> --max-apply-batch-size 5000 --max-apply-matched 50000`
- [ ] Monthly `events-log-retention-drill` workflow artifact reviewed (latest dry-run evidence available).
- [ ] Backend perf baseline checked (recommended):
  - `python backend/scripts/run_perf_baseline.py --iterations 30 --fail-on-budget-breach --output /tmp/backend-perf-baseline.json`
- [ ] Incident runbook owner on-call acknowledged.
- [ ] Evidence submission policy applied:
  - `docs/security/evidence/*-latest.json` 視為 pipeline/local gate 產物，不作為人工提交必要檔案。
  - 發版前確認必要固定證據檔（drill/audit/report）已提交；`*-latest.json` 若僅為本次本地 gate 更新，請還原：
    - `bash scripts/clean-evidence-noise.sh`
- [ ] If pricing experiment is enabled, verify `growth_pricing_experiment_enabled=true` and `disable_pricing_experiment=false`, and keep rollback toggle ready.
- [ ] If any release gate relaxation is used, set `RELEASE_GATE_HOTFIX_OVERRIDE=1` and `RELEASE_GATE_OVERRIDE_REASON`, and record the reason in release notes.
- [ ] Verify GitHub `Release Gate` summary includes `Release gate hotfix override contract` with expected `hotfix_override` / `override_reason_present` / `override_reason_pattern` / `enabled_relaxations` values.
- [ ] Verify launch signoff gate runs with `require_ready=true` on `main` (non-ready artifact must fail).
- [ ] Verify CUJ synthetic evidence gate runs with `require_pass=true` on `main` (fail result must fail gate).
- [ ] Verify `frontend-e2e` includes `Frontend e2e summary schema gate` pass (schema contract intact).
- [ ] Download artifact `frontend-e2e-summary` and verify `schema_version=v1` with required keys (`result`, `exit_code`, `classification`, `log_available`, `next_action`).
- [ ] If `frontend-e2e` fails with `classification=browser_download_network`, record DNS/egress evidence and rerun once before any release decision.
- [ ] If `frontend-e2e` fails with `classification=e2e_process_timeout`, attach the e2e log, identify the stuck step, and rerun with adjusted `E2E_TIMEOUT_SECONDS` only after documenting the reason.
- [ ] When enabling e2e in release gates (`RUN_E2E=1`), set explicit timeout guardrails:
  - `E2E_TIMEOUT_SECONDS` (default `420`)
  - `E2E_TIMEOUT_GRACE_SECONDS` (default `10`)
  - keep values in release notes for reproducibility.
- [ ] Ensure release runner uses Node 20/22 for frontend e2e; gate is fail-fast on Node >22 when `RUN_E2E=1`.
- [ ] If AI quality snapshot evidence check must be temporarily relaxed, use `RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE=1` only with hotfix override + incident reason.
- [ ] Verify `AI quality snapshot freshness gate` summary includes `evidence_source_result` / `evidence_source_run_id` / `evidence_source_artifact_id`.
- [ ] Verify `Core loop snapshot gate` summary includes `evaluation_result` / `daily_loop_completion_rate` / `dual_reveal_pair_rate`.
- [ ] Core loop degraded result should be treated as non-blocking signal (summary `non_blocking_on_degraded=yes`), not release hard-fail.
- [ ] Verify timeline runtime summary exists (`/tmp/timeline-runtime-alert-summary-local.json`) and clamp ratio is within threshold (`warn<=0.15`, `critical<=0.30`, evaluated only when `query_total>=20`).
- [ ] Verify outbox health summary exists (`/tmp/notification-outbox-health-summary-local.json`) and review `depth`/`dead_letter_rate` drift before release.
- [ ] If running local `release-gate.sh` in CI-like mode, set `RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE=daily_artifact` and verify evidence fetch succeeds.
- [ ] If running `release-gate-local.sh` in CI-like mode, set `RELEASE_GATE_ALLOW_MISSING_SLO_URL=0` (fail-closed for missing SLO URL).
- [ ] If using `release-gate-local.sh` for quick local loops, optionally use `RELEASE_GATE_SECURITY_PROFILE=fast`; use `full` before merge/release.
- [ ] In `release-gate.sh` output, confirm `ai quality summary` fields are coherent: `source_result` + `gate_result` + `evaluation_result`.
- [ ] If running `release-gate-local.sh` in CI-like mode, use `RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE=daily_artifact` and verify evidence fetch result (or explicit allow-missing override).
- [ ] For `release-gate-local.sh`, confirm `ai quality summary` shows coherent `source_result` + `gate_result` + `evaluation_result` (e.g., source skip should not appear as gate pass with stale evidence).
- [ ] For `release-gate-local.sh` default mode, verify quick backend contract tests executed (`test_release_gate_workflow_contract.py` + `test_security_gate_contract.py` + `test_frontend_e2e_summary_*`).
- [ ] Verify local quick backend contract summary schema gate passed (`check_quick_backend_contract_summary.py` with `schema_version=v1`).
- [ ] If intentionally skipping quick backend tests, record reason and set `RUN_QUICK_BACKEND_CONTRACT_TESTS=0` explicitly.
- [ ] If full backend regression is required, run with `RUN_FULL_BACKEND_PYTEST=1` and attach result summary.
- [ ] Ensure `RELEASE_GATE_OVERRIDE_REASON` follows ticket format (or set `RELEASE_GATE_OVERRIDE_REASON_PATTERN` explicitly before override).
