# Chaos Drill Spec (TEST-01 / OPS-03 / OPS-04)

Last updated: 2026-02-26

## Goal

每週固定演練高風險情境，確保 oncall 在故障時可快速降級與回復（反脆弱 Antifragile）：

1. `ai_provider_outage`（AI provider 中斷）
2. `ws_storm`（WebSocket 連線風暴）
3. **Vicky Disconnect**（伴侶/連線中斷演練）：Phase 1 上線前每週五下午進行 tabletop 或乾跑，模擬一側使用者 WebSocket 斷線或「伴侶離線」情境，驗證降級、重連與通知流程。

## Drill Scope

1. 只允許 non-production 乾跑（tabletop + config simulation）。
2. 不執行破壞性資料操作。
3. 每次演練都要產生證據 JSON/Markdown 與 action items。

## Dry-Run Steps

1. 執行 drill：
   - `./scripts/chaos-drill.sh`
2. 驗證證據：
   - `cd backend && .venv-gate/bin/python scripts/validate_security_evidence.py --kind chaos-drill --contract-mode strict`
3. 確認 incident SOP 與 report template 存在且可用：
   - `docs/ops/incident-response-playbook.md`
   - `docs/ops/chaos-drill-report-template.md`

## Pass Criteria

1. `chaos-drill-*.json` 中 `all_passed=true`。
2. 必要檢查全部通過：
   - `runbook_present`
   - `incident_playbook_ai_outage_present`
   - `incident_playbook_ws_storm_present`
   - `report_template_present`
   - `workflow_schedule_declared`
   - `nonprod_dry_run`
3. Security gate 驗證最新 chaos evidence 新鮮度（預設 `CHAOS_DRILL_EVIDENCE_MAX_AGE_DAYS=14`）。

## CI Automation（OPS-04 Chaos Engineering Pipeline）

1. Workflow: `.github/workflows/chaos-drill.yml`
2. Schedule: 每週五 UTC 09:00（cron `0 9 * * 5`），對應台灣時間下午 17:00，與「Vicky Disconnect」演練時段對齊。
3. 失敗時：上傳 artifacts 並建立/更新 alert issue。
4. **Vicky Disconnect**：每週五下午除 CI 自動 drill 外，建議進行一次 tabletop 或乾跑（見 incident playbook「伴侶/連線中斷」小節），確保反脆弱流程可執行。

## Rollback Plan

1. drill 失敗時禁止放寬任何保護閾值。
2. 先維持保守防護設定：
   - `AI_ROUTER_ENABLE_FALLBACK=true`
   - `WS_MESSAGE_RATE_LIMIT_COUNT` 維持較低值
3. 依 incident playbook 逐項修復後重跑：
   - `./scripts/chaos-drill.sh`
4. 若演練造成非預期副作用，立即回復最近穩定 config 並停用當次變更（feature flag/config rollback）。

## Evidence Artifacts

輸出於 `/Users/alanzeng/Desktop/Projects/Haven/docs/security/evidence/`：

1. `chaos-drill-*.json`
2. `chaos-drill-*.md`

關鍵欄位：

1. `required_drills`
2. `executed_drills`
3. `checks_total / checks_passed / checks_failed`
4. `all_passed`
