# Gamification Replay Protection（P1-E）

## Why
- 防止同一天重送相同 Journal 內容在多裝置重複加分。
- 讓分數邏輯可追溯，方便稽核與回滾。

## How
- 新增 `gamification_score_events` 事件表，使用 `dedupe_key` 唯一索引擋重複計分。
- Journal 分數改為「先計算候選分數，再執行 `apply_journal_score_once`」。
- 去重鍵組成：`event_type + user_id + event_date + normalized_content_hash`。
- 新增 `GET /api/users/gamification-summary`（server-side 唯讀計算）：
  - `streak_days`：雙方同日都有 Journal 才算。
  - `best_streak_days`：歷史最長連續雙方共同記錄天數。
  - `level/love_bar_percent`：由 `savings_score` 推導。

## What
- Model：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/models/gamification_score_event.py`
- Migration：`/Users/alanzeng/Desktop/Projects/Haven/backend/alembic/versions/e8f9a0b1c2d3_add_gamification_score_events_table.py`
- Service：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/gamification.py`
- Journal API：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/api/journals.py`
- Summary API：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/users.py` (`GET /api/users/gamification-summary`)
- Frontend hook/UI：`/Users/alanzeng/Desktop/Projects/Haven/frontend/src/services/api-client.ts`、`/Users/alanzeng/Desktop/Projects/Haven/frontend/src/app/page.tsx`
- Tests：`/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_gamification_replay_protection.py`
- Tests：`/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_gamification_summary_api.py`

## DoD
- 同日同內容 Journal 第二次提交不再加分。
- 空白差異（多空白）視為同內容，仍不重複加分。
- 不同內容仍可正常加分。
- 審計事件需包含 `score_replay_blocked`。
- `GET /api/users/gamification-summary` 必須只回 current_user 上下文（不可 overpost user_id）。

## Debug Checklist
1. 為何分數沒有增加：
   - 查 `JOURNAL_CREATE` 審計 metadata 的 `score_replay_blocked` 是否為 true。
2. 去重疑似失效：
   - 查 `gamification_score_events` 是否存在重複 `dedupe_key`（理論上不可能）。
3. 併發重送問題：
   - 查 DB unique constraint 是否生效，以及 IntegrityError 是否被轉為 replay-blocked。
