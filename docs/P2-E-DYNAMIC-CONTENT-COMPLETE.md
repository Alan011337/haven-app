# P2-E. 進階內容 — [AUTO-CONTENT] Dynamic Content Injection 完成對照

本文件對應 P2-E「每週生成 5 張時事卡片」Pipeline 與實作位置。

---

## ✅ [AUTO-CONTENT] Dynamic Content Injection

- **DoD**：建立 Pipeline 每週生成 5 張「時事卡片」。
- **實作**：
  - **Pipeline 邏輯**：`backend/app/services/dynamic_content_pipeline.py`
    - `_ensure_trending_deck(session)`：取得或建立名為「時事」的 `CardDeck`，回傳 `deck_id`。
    - `_generate_trending_cards_via_ai()`：呼叫 OpenAI（gpt-4o-mini）產生 5 筆時事卡片（title、description、question）；若 API 不可用則使用內建 fallback 的 5 張固定題目。
    - `run_weekly_injection(session)`：確保時事牌組存在 → 呼叫 AI 取得 5 筆 → 寫入 `Card`（category=DAILY_VIBE、is_ai_generated=True、deck_id=時事、tags=["時事","動態"]），回傳寫入張數。
  - **每週腳本**：`backend/scripts/run_dynamic_content_weekly.py` — 以 `Session` 呼叫 `run_weekly_injection` 並 commit；建議以 cron 每週執行（例如週一 04:00）。
  - **牌組列表 API**：`GET /api/card-decks/list` — 回傳所有牌組 `{id, name, description}`，前端可依 `name === "時事"` 取得 `deck_id`，再以 `GET /api/card-decks/{deck_id}/draw` 抽時事卡。
- **抽卡**：既有 `GET /api/card-decks/{deck_id}/draw` 從該牌組隨機取一張卡；時事牌組每週注入 5 張新卡後即可被抽到。
- **Rollback**：停跑每週腳本即可；既有卡片保留。若要移除時事牌組，需自 DB 刪除該 deck 及其 cards（注意 FK）。

---

## 總結

| 項目 | 狀態 | 主要檔案／備註 |
|------|------|----------------|
| 時事牌組取得/建立 | ✅ | dynamic_content_pipeline._ensure_trending_deck |
| AI 生成 5 張時事卡 | ✅ | _generate_trending_cards_via_ai（OpenAI + fallback） |
| 每週寫入 cards | ✅ | run_weekly_injection |
| 每週執行腳本 | ✅ | run_dynamic_content_weekly.py |
| 牌組列表 API | ✅ | GET /api/card-decks/list |

**Cron 建議**：每週一次，例如 `0 4 * * 1`（週一 04:00）。執行：`cd backend && PYTHONPATH=. python scripts/run_dynamic_content_weekly.py`。  
**依賴**：`OPENAI_API_KEY`（可選；未設定或失敗時使用 fallback 題目）。
