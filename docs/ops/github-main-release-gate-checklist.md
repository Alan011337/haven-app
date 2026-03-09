# GitHub Main Release Gate Checklist (30s)

## 目標 / Goal
- 快速確認 `main` 分支是否達到可上線 gate。  
- Quickly confirm whether `main` satisfies launch gate status.

## 點擊步驟 / Click path
1. 打開 GitHub repository -> `Actions`.  
   Open repository -> `Actions`.
2. 點 `Release Gate` workflow。  
   Click `Release Gate` workflow.
3. 在 branch/filter 選 `main`，看最新一筆 run。  
   Filter to `main`, inspect the latest run.
4. 確認 run 狀態是綠色 `Success`。  
   Ensure latest run is green `Success`.

## Job 必須全綠 / Required green jobs
- `backend-gate`
- `frontend-gate`
- `frontend-e2e` (on `main` this is required, not soft-fail)

## 快速失敗定位 / Fast failure triage
- `backend-gate` fail: 看 `Backend security gate` 或 `Backend tests` step。
- `backend-gate` 若出現 `key-rotation-drill` 失敗：先執行 `bash scripts/key-rotation-drill.sh` 產生最新證據，再重跑。
- `backend-gate` 內的 SLO 問題可直接看 `SLO burn-rate gate summary`（job summary 會顯示 result/ws/cuj/abuse_economics/reasons）。
- `backend-gate` 內的 tier policy 問題看 `Service tier budget gate summary`：
  - `target_tier` / `release_intent` 會明確顯示當前 gate 契約。
  - `tier_error_budget_freeze_enforced=yes` 且 `release_freeze=yes` 時，`feature` 會被阻擋。
  - `hotfix/security/bugfix` 需符合 override 契約才可放行。
- 本機若沒有監控 URL，可用 `SLO_GATE_HEALTH_SLO_FILE=<path>` 提供 health snapshot JSON 做 dry-run；`main` 仍建議走 `SLO_GATE_HEALTH_SLO_URL`。
- `backend-gate` 內的 launch signoff 問題看 `Launch signoff artifact gate` / `Launch signoff gate summary`（會顯示 artifact age 與 failure reasons）。
- `backend-gate` 內的 AI quality 問題先看 `AI quality snapshot freshness gate summary`：
  - `result=fail` 代表 evidence 缺失/過舊/契約錯誤（會擋 release）
  - `result=degraded` 代表品質退化但不阻斷核心 CUJ（需追蹤後續改善）
  - `evidence_source_result / evidence_source_run_id / evidence_source_artifact_id` 可追到 daily artifact 來源是否正常
  - 緊急 hotfix 若需放寬缺失證據檢查，使用 `RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE=1`（仍需 `RELEASE_GATE_HOTFIX_OVERRIDE=1` + `RELEASE_GATE_OVERRIDE_REASON`）
- `frontend-gate` fail: 看 `Frontend env check` 或 `Frontend typecheck` step。
- `frontend-e2e` fail: 看 `Install Playwright browsers` / `Build frontend` / `Run e2e smoke`。
- `frontend-e2e` 先看 `Frontend e2e summary`（result/classification/next_action），再下載 artifact `frontend-e2e-log` 看完整輸出。
- `frontend-e2e` 也要看 `Frontend e2e summary schema gate`：
  - fail 代表 summary artifact 契約破壞（欄位/schema_version 不相容），屬於流程阻斷級問題。

## Frontend E2E Degraded / Override 決策樹（main）
1. 先看 `Frontend e2e summary` 的 `classification`。
2. 若 `classification=browser_download_network`：
   - 先重跑一次 workflow（排除暫時性 DNS/網路抖動）。
   - 若連續失敗：確認 `Cache Playwright browsers` 命中率與 runner 對 `cdn.playwright.dev` 的 DNS/egress。
   - 需要緊急發版時：優先改用已命中的 runner/cached environment 重新跑，不建議跳過 e2e gate。
3. 若 `classification=app_unreachable` 或 `cuj_assertion_timeout`：
   - 視為產品回歸風險，必須修復後重跑，不可 override。
4. 若 `classification=test_or_runtime_failure`：
   - 下載 `frontend-e2e-log` + `frontend-e2e-summary` artifact 進行根因分析，修復後重跑。
5. 任何 `schema gate` 失敗：
   - 視為 CI 契約破壞，必須先修復 summary schema（`schema_version=v1` + required keys）再繼續。

## Local Override Policy（release-gate-local）
- `release-gate-local.sh` 對 launch signoff / CUJ synthetic evidence 預設也是 fail-closed。
- 僅限 `classification=browser_download_network` 時，可設 `E2E_ALLOW_BROWSER_DOWNLOAD_FAILURE=1` 暫時降級。
- 降級只允許本地演練或緊急排障，不可當成 main 合併條件替代。
- 本地仍強制執行 `check-e2e-summary-schema.mjs`，`schema_version` 不符會直接失敗。
- 若要暫時放寬 launch/cuj 證據缺失，需顯式設：
  - `RELEASE_GATE_ALLOW_MISSING_LAUNCH_SIGNOFF=1` 或 `RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE=1`
  - 並同時設 `RELEASE_GATE_HOTFIX_OVERRIDE=1` + `RELEASE_GATE_OVERRIDE_REASON=<ticket/incident>`
- 若 launch artifact 檔案存在但 `overall_ready=false`，`ALLOW_MISSING_LAUNCH_SIGNOFF=1` 不會略過此失敗；本地 dry-run 可改用 `LAUNCH_SIGNOFF_ARTIFACT_PATH=/tmp/nonexistent-launch-signoff.json` 搭配 override 契約演練。

## Local Backend Test Mode（release-gate-local）
- 預設 (`RUN_FULL_BACKEND_PYTEST=0`) 會執行 quick contract tests：
  - `test_release_gate_workflow_contract.py`
  - `test_security_gate_contract.py`
  - `test_frontend_e2e_summary_schema_gate_script.py`
  - `test_frontend_e2e_summary_contract.py`
  - `test_frontend_e2e_summary_script.py`
- quick mode 會輸出 `/tmp/release-gate-local-quick-backend-tests-summary.json` 並做 schema gate：
  - `backend/scripts/check_quick_backend_contract_summary.py --summary-file /tmp/release-gate-local-quick-backend-tests-summary.json --required-schema-version v1`
- 如需完全略過 quick tests，才設 `RUN_QUICK_BACKEND_CONTRACT_TESTS=0`。
- 需要完整回歸時，設 `RUN_FULL_BACKEND_PYTEST=1`（會跑 full backend pytest）。

## 通過判定 / Pass criteria
- 最新 `main` 的 `Release Gate` run = `Success`
- 三個 job 都是綠色
- 無 rerun in-progress

## 補充 / Notes
- PR 上 `frontend-e2e` 可以 soft-fail，但 `main` 不可。  
- `frontend-e2e` may be soft-fail on PR, but must pass on `main`.
- 同 repo 的 PR：SLO burn-rate gate 會 fail-closed（需要 `SLO_GATE_HEALTH_SLO_URL`）。
- Fork PR：SLO burn-rate gate 允許 `--allow-missing-url`，避免 fork 無法讀取 secrets 而全失敗。
- `release-gate.sh` 的 SLO burn-rate gate 預設是 fail-closed；若 `SLO_GATE_HEALTH_SLO_URL` 缺失會直接失敗。僅在緊急 hotfix 才可用 `RELEASE_GATE_ALLOW_MISSING_SLO_URL=1` 臨時放寬。  
- `release-gate.sh` now fails closed for SLO burn-rate checks; missing `SLO_GATE_HEALTH_SLO_URL` fails the gate unless emergency override is explicitly set.
- `main` 與正式 `release-gate.sh` 的 SLO burn-rate gate 預設採 monitor-only 處理 `insufficient_data`；真正阻擋 release 的是 `degraded` / `block`。若要做更嚴格的 sufficient-data 演練，才顯式設 `RELEASE_GATE_REQUIRE_SLO_SUFFICIENT_DATA=1` 或 `--require-sufficient-data`。
- `release-gate.sh` 與 GitHub workflow 都會執行 `check_service_tier_budget_gate.py`；預設 `RELEASE_TARGET_TIER=tier_0`、`RELEASE_INTENT=feature`。
- `check_slo_burn_rate_gate.py` 支援本機 `SLO_GATE_HEALTH_SLO_FILE`（或 `--payload-file`）作為 URL 缺失時的替代來源；summary 會標示 `source_type=file`。
- `release-gate.sh` 的 launch signoff 與 CUJ synthetic evidence 都預設 fail-closed；只允許在緊急修補時暫時設 `RELEASE_GATE_ALLOW_MISSING_LAUNCH_SIGNOFF=1` 或 `RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE=1`。
- 任何 gate 放寬都必須同時提供：`RELEASE_GATE_HOTFIX_OVERRIDE=1` + `RELEASE_GATE_OVERRIDE_REASON=<ticket/incident>`；否則腳本直接失敗。
- `RELEASE_GATE_OVERRIDE_REASON` 預設需符合 ticket-like 格式（英數 + `._-`，無空白）；必要時可用 `RELEASE_GATE_OVERRIDE_REASON_PATTERN` 指定組織內格式。
- GitHub `Release Gate` workflow 也有 `Release gate hotfix override contract` step；主線(`main`)預設 fail-closed，若放寬會在 step summary 顯示 `hotfix_override`、`override_reason_present`、`override_reason_pattern`、`enabled_relaxations`。
- 本機 `release-gate.sh` 的 AI quality 證據來源可切 `RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE=daily_artifact`（預設 `local_snapshot`）；若用 daily artifact 可加 `RELEASE_GATE_AI_QUALITY_EVIDENCE_REPO` 指定 repo。
- 本機 `release-gate-local.sh` 也支援同樣的 AI quality 證據來源切換（`local_snapshot` / `daily_artifact`）。
