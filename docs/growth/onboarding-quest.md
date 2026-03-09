# ACT-01: 7-Day Onboarding Quest

## Why
- 將新用戶 onboarding 轉成可量測的 7-step 任務，降低「註冊後不互動」流失。
- 後端作為 single source of truth，避免前端自行推導造成進度不一致。
- 以 kill-switch 控制，確保異常時可立即降級。

## How
- 新增 runtime：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/growth_onboarding_quest_runtime.py`
  - 依使用者與伴侶資料計算 7 個 step 的完成狀態。
  - 進度欄位：`completed_steps`, `total_steps`, `progress_percent`。
  - 記錄結構化 log：`onboarding_quest_evaluated ...`。
  - 記錄 runtime metric counters：`growth_onboarding_quest_*`。
- 新增 API：`GET /api/users/onboarding-quest`
  - 路由：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/users.py`
  - Schema：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/schemas/growth.py`
- 新增 feature flag + kill-switch：
  - `growth_onboarding_quest_enabled`
  - `disable_growth_onboarding_quest`
  - 定義位置：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/feature_flags.py`
  - 契約覆蓋：`/Users/alanzeng/Desktop/Projects/Haven/docs/security/growth-kill-switch-coverage.json`

## What
- API 回傳資料（摘要）：
  - `enabled`
  - `has_partner_context`
  - `kill_switch_active`
  - `completed_steps`
  - `total_steps`
  - `progress_percent`
  - `steps[]`（含 `key/title/description/quest_day/completed/reason/dedupe_key/metadata`）

## DoD
1. API 可在已登入狀態穩定回傳 onboarding quest 進度。
2. kill-switch 開啟時不拋錯，回傳 `enabled=false`、`steps=[]`。
3. overpost `user_id` 不影響結果（仍只讀 current user）。
4. 測試通過（見下方命令）。
5. 不輸出 email/token 等敏感資料到 payload/log。

## Test Plan
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_onboarding_quest_api.py \
  tests/test_feature_flags.py \
  tests/test_feature_flags_api.py \
  tests/test_growth_kill_switch_coverage_contract.py
```

## Failure / Degradation
- 若資料不足（例如尚未綁定伴侶），step 以 `reason=partner_required|partner_not_bound` 表示，服務仍回 200。
- 若功能需緊急關閉：`disable_growth_onboarding_quest=true`，API 降級為 disabled payload。

## Rollback
1. 即時回滾（無需 deploy）：
   - 設定 `disable_growth_onboarding_quest=true`
2. 程式回退：
   - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/services/growth_onboarding_quest_runtime.py`
   - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/users.py`
   - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/schemas/growth.py`
   - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/services/feature_flags.py`
   - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_onboarding_quest_api.py`
