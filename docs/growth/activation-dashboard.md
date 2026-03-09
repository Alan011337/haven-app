# Activation Funnel Dashboard (P1)

## Why
- 明確追蹤 `signup -> bind -> first journal -> first deck` 漏斗轉換，定位流失節點。
- 讓 Growth 轉換資料可以每日自動產生、可回放、可在 release 前檢查品質。

## Funnel Stages
1. `signup_completed`
2. `partner_bound`
3. `first_journal_created`
4. `first_deck_response`

## Runtime Contract
- 服務實作：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/growth_activation_runtime.py`
  - cohort 定義：`users.terms_accepted_at` 在視窗內且未 soft-delete。
  - stage count：`users.partner_id`、`journals`、`card_responses`（都排除 `deleted_at`）。
  - companion referral funnel：`growth_referral_events` 的 `LANDING_VIEW/SIGNUP/COUPLE_INVITE/BIND`。
- 快照腳本：`/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_growth_activation_funnel_snapshot.py`
  - 輸出：`docs/growth/evidence/activation-funnel-snapshot-<timestamp>.json`
  - 最新指標：`docs/growth/evidence/activation-funnel-snapshot-latest.json`
- 定時工作流：`/Users/alanzeng/Desktop/Projects/Haven/.github/workflows/growth-activation-funnel-snapshot.yml`
  - 每日排程執行，並上傳 artifact。

## Referral Companion Funnel (View -> Signup -> Bind)
- 資料來源：`growth_referral_events`
- 事件型別：`LANDING_VIEW`、`SIGNUP`、`BIND`
- 關鍵欄位：`inviter_user_id`、`actor_user_id`、`created_at`

## Query Sketch (Server-side)
```sql
WITH base AS (
  SELECT u.id AS user_id, u.created_at AS signup_at
  FROM users u
  WHERE u.deleted_at IS NULL
),
bind_stage AS (
  SELECT b.user_id, MIN(b.created_at) AS bind_at
  FROM (
    SELECT id AS user_id, created_at FROM users WHERE partner_id IS NOT NULL
  ) b
  GROUP BY b.user_id
),
journal_stage AS (
  SELECT j.user_id, MIN(j.created_at) AS first_journal_at
  FROM journals j
  WHERE j.deleted_at IS NULL
  GROUP BY j.user_id
),
deck_stage AS (
  SELECT r.user_id, MIN(r.created_at) AS first_deck_at
  FROM card_responses r
  WHERE r.deleted_at IS NULL
  GROUP BY r.user_id
)
SELECT
  COUNT(*) AS signup_users,
  COUNT(bind_stage.user_id) AS bound_users,
  COUNT(journal_stage.user_id) AS first_journal_users,
  COUNT(deck_stage.user_id) AS first_deck_users
FROM base
LEFT JOIN bind_stage ON bind_stage.user_id = base.user_id
LEFT JOIN journal_stage ON journal_stage.user_id = base.user_id
LEFT JOIN deck_stage ON deck_stage.user_id = base.user_id;
```

## DoD
- 每日可產生一次 activation funnel 快照（含四階段人數）。
- 儀表板查詢以 UTC 為準，且排除 soft-deleted 資料。
- 查詢與事件命名對齊 `docs/data/events.md`。
- 有 workflow contract 測試與 snapshot script 測試，避免排程/輸出路徑漂移。

## Local Verification
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
DATABASE_URL=sqlite:///./test.db \
OPENAI_API_KEY=test-key \
SECRET_KEY=01234567890123456789012345678901 \
ABUSE_GUARD_STORE_BACKEND=memory \
PYTHONUTF8=1 PYTHONPATH=. \
.venv-gate/bin/python scripts/run_growth_activation_funnel_snapshot.py \
  --window-days 30 \
  --output /tmp/activation-funnel-snapshot.json \
  --latest-path /tmp/activation-funnel-snapshot-latest.json
```

## Rollback
- 立即關閉：`disable_growth_activation_dashboard=true`
- 功能回退：還原 `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/growth_activation_runtime.py` 與 `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_growth_activation_funnel_snapshot.py`
- 排程回退：停用 `growth-activation-funnel-snapshot` workflow

## Debug Checklist
1. Bind 轉換率異常低：
   - 檢查 invite code 產生與配對 API 成功率。
2. Journal/Deck 首次行為偏低：
   - 檢查 onboarding 導引與核心 CTA 可見性。
3. 與產品事件追蹤不一致：
   - 檢查 SQL 篩選與前端事件定義是否同版。
