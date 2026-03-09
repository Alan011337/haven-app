# Re-engagement Hooks (P1)

## Why
- 把 `GROW-03` 從概念文件變成可執行的後端能力，先提供「社交分享卡片」與「時光膠囊」兩種 hook 推薦。
- 所有推薦都走 server-side feature flag + kill-switch，避免新策略影響核心 CUJ。

## How
- 服務：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/growth_reengagement_runtime.py`
  - hook 型別：`SOCIAL_SHARE_CARD`、`TIME_CAPSULE`
  - `SOCIAL_SHARE_CARD` 條件：
    - 雙方都至少有 1 篇日記
    - 伴侶 pair 在近 7 天有日記活動
  - `TIME_CAPSULE` 條件：
    - 伴侶雙方帳號年齡至少 30 天（用 `terms_accepted_at` 判定）
    - 伴侶合計至少 6 篇日記
    - 伴侶合計至少 2 筆卡片回覆
  - observability：
    - `growth_reengagement_runtime_metrics` 記錄評估總量、eligible 次數
    - 結構化 log：`reengagement_hooks_evaluated`
- API：`GET /api/users/reengagement-hooks`
  - 實作：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/users.py`
  - 回傳 `enabled/has_partner_context/kill_switch_active/hooks[]`
  - dedupe key 使用週/月 bucket + pair identifiers hash（不暴露 PII）
- Schema：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/schemas/growth.py`
  - `ReengagementHookType`
  - `ReengagementHookPublic`
  - `ReengagementHooksPublic`

## What
- API runtime + schema + unit/API tests
- 事件詞彙補齊：
  - `growth.reengagement.share_card_prompted.v1`
  - `growth.reengagement.time_capsule_prompted.v1`
  - 位置：`/Users/alanzeng/Desktop/Projects/Haven/docs/data/events.md`

## DoD
- endpoint 在有 partner context 時可回傳 2 種 hook 推薦結果。
- kill-switch `disable_growth_reengagement_hooks=true` 時，endpoint 不報錯並回傳 `enabled=false`。
- 測試覆蓋：
  - mature pair eligible
  - kill-switch disable
  - no-partner degraded behavior
  - unauthenticated access = 401
- metadata 不暴露 email/token/IP。

## Debug Checklist
1. API 永遠回空 hooks：
   - 檢查 `growth_reengagement_hooks_enabled` 是否為 `true`
   - 檢查 `disable_growth_reengagement_hooks` 是否被打開
2. `TIME_CAPSULE` 長期不觸發：
   - 檢查 `terms_accepted_at` 是否缺值
   - 檢查 pair journal/card response 是否低於門檻
3. 分享 hook 間歇失效：
   - 檢查近 7 天日記活動是否存在（soft-delete 不計入）

## Rollback
- 立即回滾：`disable_growth_reengagement_hooks=true`
- 程式回滾：
  - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/services/growth_reengagement_runtime.py`
  - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/users.py`
  - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/schemas/growth.py`
  - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_reengagement_hooks_api.py`
