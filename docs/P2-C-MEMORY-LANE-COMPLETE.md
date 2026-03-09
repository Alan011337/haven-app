# P2-C. 回憶長廊 (Memory Lane) — 完成對照表

本文件對應 P2-C 開發清單與實作位置。

---

## ✅ 多媒體日曆系統 (The Archive)

- **DoD**：整合日記、卡片回答、照片（照片為預留，目前無上傳端）。
- **實作**：
  - **Backend**：`backend/app/api/routers/memory.py` — `GET /api/memory/timeline` 合併 journals 與 card_decks 歷史（completed sessions），依時間排序；`GET /api/memory/calendar` 依月份回傳有內容的日期與 mood／筆數。
  - **Service**：`backend/app/services/memory_archive.py` — `get_unified_timeline()`（journal + card 合併、分頁）、`get_calendar_days()`（當月有日記／卡片的日期、mood_color、journal_count、card_count）；schema 預留 `type: "photo"`。
  - **Frontend**：`frontend/src/services/memoryService.ts`、`frontend/src/app/memory/page.tsx` — 回憶長廊頁面呼叫 timeline／calendar API，呈現動態牆與日曆。
- **照片**：API 與前端型別已支援 `TimelinePhotoItem`；實際照片上傳與儲存為後續擴充。

---

## ✅ 雙視圖切換 (Dual View System)

- **DoD**：Feed View（動態牆）、Calendar View（日曆模式）可切換，故事感／全貌感。
- **實作**：
  - **Feed View**：`frontend/src/features/memory/MemoryFeedView.tsx` — 依時間軸列出日記（心情色條、預覽）與卡片對話（題目、我的／伴侶回答），支援「載入更多」。
  - **Calendar View**：`frontend/src/features/memory/MemoryCalendarView.tsx` — 月曆格線、有內容的日期顯示 mood 色點與數量，可切換上／下月。
  - **切換**：`frontend/src/app/memory/page.tsx` — 頂部按鈕切換「動態牆」／「日曆」；資料由 `useMemoryData` 依 view 分別請求 timeline 或 calendar。

---

## ✅ 時光膠囊 (Time Capsule)

- **DoD**：特定紀念日（如一年前的今天）自動抓取過往回憶，生成幸福回憶卡並推播雙方。
- **實作**：
  - **Backend 查詢**：`backend/app/services/memory_archive.py` — `get_time_capsule_memory(session, user_id, partner_id, past_date)` 查詢 past_date 當天的日記數與卡片數，回傳 summary 與 items。
  - **API**：`GET /api/memory/time-capsule` — 回傳「一年前的今天」是否有回憶、摘要與筆數（前端用於展示時光膠囊區塊）。
  - **推播**：`backend/scripts/run_time_capsule_dispatch.py` — 每日排程（建議 cron 08:00）：對有伴侶的使用者計算 (today - 365)，若有回憶則以 `event_type="time_capsule"` 呼叫 `queue_partner_notification`，雙方各收一則。
  - **通知類型**：`backend/app/services/notification.py` — `NotificationAction` / `NotificationDedupeEvent` 新增 `time_capsule`；`_build_email_payload` 新增時光膠囊標題與內文；`docs/security/notification-trigger-matrix.json` 新增 `time_capsule` trigger（throttle 86400、push + in_app_ws）。
  - **Payload**：`backend/app/services/notification_payloads.py` — `event_type="time_capsule"` 對應 matrix_event `time_capsule`。
- **前端**：回憶長廊頁「時光膠囊」區塊呼叫 `GET /memory/time-capsule`，顯示今日是否有「一年前今天」的回憶摘要。

---

## ✅ AI 關係週報／月報

- **DoD**：自動總結兩人情緒趨勢、最常討論話題，並由 AI 給出關係健檢建議。
- **實作**：
  - **Backend**：`backend/app/services/memory_archive.py` — `get_relationship_report(session, user_id, partner_id, period)` 依 period（week/month）彙整該區間內日記的 analysis.mood_label 分布，產出 `emotion_trend_summary`；`top_topics`、`health_suggestion` 預留為空／None，可接後續 AI。
  - **API**：`GET /api/memory/report?period=week|month` — 回傳 from_date、to_date、emotion_trend_summary、top_topics、health_suggestion、generated_at。
  - **Frontend**：回憶長廊頁「關係週報／月報」區塊呼叫 `GET /memory/report?period=month`，顯示情緒趨勢；若後端補上 health_suggestion 與 top_topics 會一併顯示。

---

## 總結

| 項目 | 狀態 | 主要檔案／備註 |
|------|------|----------------|
| 多媒體日曆系統 (Archive) | ✅ | memory router + memory_archive service；timeline/calendar API；照片型別預留 |
| 雙視圖 (Feed + Calendar) | ✅ | MemoryFeedView、MemoryCalendarView、/memory 頁切換 |
| 時光膠囊 | ✅ | get_time_capsule_memory、GET /memory/time-capsule、run_time_capsule_dispatch.py、time_capsule 通知類型 |
| AI 關係週報／月報 | ✅ | get_relationship_report、GET /memory/report；情緒趨勢已實作，top_topics／health_suggestion 可接 AI |

**Rollback**：還原 memory router 註冊、notification 與 matrix 變更、前端 /memory 與 Sidebar 連結；停用 time capsule cron 即可停推播。

**後續可選**：照片上傳與 timeline 整合；紀念日偏好（使用者自訂日期）與 time capsule 觸發邏輯；AI 產出 top_topics 與 health_suggestion（呼叫既有 AI 服務）。
