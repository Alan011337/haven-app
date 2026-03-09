# Backup Restore Drill Runbook (OPS-BACKUP-01/02)

Last updated: 2026-02-23

## Goal

建立「可演練、可驗證、可回滾」的備份還原流程，確保加密備份策略與還原演練證據可被 CI/Release Gate 檢查。

1. 備份策略必須宣告加密、排程、保留天數。
2. 還原演練必須在 non-prod 乾跑，產生證據檔。
3. Security gate 必須驗證 `backup-restore-drill` 證據新鮮度。

## Dry-Run Steps

1. 執行本地演練：
   - `./scripts/backup-restore-drill.sh`
2. 驗證還原演練證據：
   - `cd backend && .venv-gate/bin/python scripts/validate_security_evidence.py --kind backup-restore-drill --contract-mode strict`
3. 確認來源證據（`data-restore-drill`）未過期：
   - 檢查 `source_evidence_path` 與 `source_evidence_generated_at`。

## Pass Criteria

1. `backup-restore-drill-*.json` 中 `all_passed=true`。
2. 必要檢查全部通過：
   - `runbook_present`
   - `rollback_plan_present`
   - `backup_policy_present`
   - `encryption_policy_enforced`
   - `restore_workflow_declared`
   - `source_restore_evidence_fresh`
   - `nonprod_dry_run`
3. Security gate 可通過最新演練證據新鮮度檢查（預設 `BACKUP_RESTORE_DRILL_EVIDENCE_MAX_AGE_DAYS=120`）。

## CI Automation

1. Workflow: `/Users/alanzeng/Desktop/Projects/Haven/.github/workflows/backup-restore-drill.yml`
2. Schedule: `0 4 1 */3 *`（每季 UTC）。
3. 失敗時：上傳演練 artifacts，並建立/更新 alert issue。

## Rollback Plan

1. 若演練失敗，禁止進入任何 production restore/purge 操作。
2. 先把高風險資料生命週期功能維持在保守模式：
   - `DATA_SOFT_DELETE_ENABLED=false`
3. 先重跑來源演練，確保資料刪除/還原鏈路一致：
   - `./scripts/data-restore-drill.sh`
4. 重跑備份還原演練：
   - `./scripts/backup-restore-drill.sh`
5. 若 production 已執行錯誤還原，依 `docs/ops/incident-response-playbook.md` 啟動事故流程，回復到最近一次可驗證備份，並重新執行資料完整性檢查後再開流量。

## Evidence Artifacts

輸出於 `/Users/alanzeng/Desktop/Projects/Haven/docs/security/evidence/`：

1. `backup-restore-drill-*.json`
2. `backup-restore-drill-*.md`

關鍵欄位：

1. `source_evidence_kind`
2. `source_evidence_path`
3. `source_evidence_generated_at`
4. `source_evidence_max_age_days`
5. `backup_encryption_required`
6. `backup_retention_days`
7. `checks_total / checks_passed / checks_failed`
8. `all_passed`
