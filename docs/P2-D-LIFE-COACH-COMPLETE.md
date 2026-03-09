# P2-D. 智慧引導基礎 (Life Coach Basics) — 完成對照表

本文件對應 P2-D 開發清單與實作位置。

---

## ✅ 主動關懷邏輯 (Active Care)

- **DoD**：雙方連續 3 天無互動時，Backend Cron 偵測並推送破冰話題或抽卡邀請。
- **實作**：
  - **偵測**：`backend/app/services/active_care.py` — `get_last_pair_interaction_at()`（取雙方最近一則日記或卡片回應時間）、`pairs_with_no_interaction_3_days()`（列出超過 3 天無互動的伴侶對）。
  - **派送**：`backend/scripts/run_active_care_dispatch.py` — 每日執行（建議 cron 09:00）：對每對符合條件者，以 `event_type="active_care"` 呼叫 `queue_partner_notification`，雙方各收一則（標題／內文見 notification 內建文案）。
  - **通知**：`backend/app/services/notification.py` — `NotificationAction` / `NotificationDedupeEvent` 新增 `active_care`；`_build_email_payload` 新增對應標題與內文；`docs/security/notification-trigger-matrix.json` 新增 `active_care` trigger（throttle 86400、push + in_app_ws）。
- **Rollback**：停跑 cron；必要時關閉 matrix 內 `active_care` 的 enabled。

---

## ✅ 衝突緩解模式 (Conflict Resolution)

- **DoD**：日記出現高風險關鍵字時，切換為調解模式，引導雙方回答引導式問題以換位思考。
- **實作**：
  - **關鍵字偵測**：`backend/app/services/conflict_detection.py` — `detect_conflict_risk(content)`，關鍵字包含「分手、討厭、生氣、恨、離婚、結束、不想在一起、受夠、絕望、放棄、不愛了、冷戰、吵架、爭吵」等（可依產品調整）。
  - **寫入分析**：`backend/app/queue/journal_tasks.py` — 在分析完成後對日記內容呼叫 `detect_conflict_risk`，將結果寫入 `Analysis.conflict_risk_detected`；若為 True 且用戶有伴侶，呼叫 `trigger_mediation()` 並在 commit 後對雙方發送 `mediation_invite` 通知。
  - **調解狀態**：`backend/app/models/mediation_session.py` — `MediationSession`（user_id_1/2、triggered_by_journal_id、created_at、user_1/2_answered_at）；`backend/app/services/mediation_runtime.py` — `trigger_mediation()`、`get_mediation_status()`、`record_mediation_answers()`；引導式問題為 `MEDIATION_GUIDED_QUESTIONS`（三題）。
  - **API**：`backend/app/api/routers/mediation.py` — `GET /api/mediation/status`（是否在調解中、問題列表、我方／伴侶是否已回答）、`POST /api/mediation/answers?session_id=`（記錄當前用戶已提交回答）。
  - **通知**：`mediation_invite` 類型與 matrix trigger（throttle 3600）；payload 由 `notification_payloads` 支援。
- **Migration**：`backend/alembic/versions/g1p2d0000001_active_care_mediation_legacy.py` — 新增 `analyses.conflict_risk_detected`、表 `mediation_sessions`。
- **Rollback**：關閉 matrix 內 `mediation_invite`；可選 revert migration（需先停用調解流程）。

---

## ✅ [LEGAL-01] Digital Breakup Protocol（數位分手協議）

- **DoD**：產品與法務對齊之數位分手流程與資料邊界說明。
- **實作**：
  - **文件**：`docs/legal/digital-breakup-protocol.md` — 解除伴侶連結、資料保留與刪除、可選冷靜期；與條款之關係；實作對照（後端解除邏輯、前端設定頁、合規條款）。
  - **後端**：既有 `partner_id` 雙向解除邏輯（如 `app.api.routers.users.routes` 中解除伴侶流程）已滿足「解除連結」；本項以文件與合規為主。

---

## ✅ [LEGAL-02] Legacy Contact（數位遺產聯絡人）

- **DoD**：用戶可設定數位遺產聯絡人；驗證與流程由 runbook 定義。
- **實作**：
  - **欄位**：`backend/app/models/user.py` — `User.legacy_contact_email`（選填）；Migration g1p2d0000001 新增 `users.legacy_contact_email`。
  - **API**：`backend/app/api/routers/users/routes.py` — `PATCH /api/users/me` 接受 `MeUpdateBody`（`full_name`、`legacy_contact_email`）；`GET /api/users/me` 回傳含 `legacy_contact_email`（`UserPublic` 已含該欄位）。
  - **文件**：`docs/legal/legacy-contact.md` — 設定方式、驗證與申請流程、隱私原則、實作對照與法務 runbook 對齊。
- **Rollback**：移除 PATCH 對 legacy_contact_email 的寫入；欄位可保留不使用。

---

## ✅ [PRD-RISK-01] The Graceful Exit（優雅退場）

- **DoD**：離開產品時之清晰路徑（解除伴侶、匯出、刪除帳號）與文件對齊。
- **實作**：
  - **文件**：`docs/product/graceful-exit.md` — 使用者路徑（解除伴侶、匯出資料、刪除帳號）、產品原則、與 LEGAL-01 / LEGAL-02 / DATA_RIGHTS 對齊。
  - **產品**：既有資料匯出與帳號刪除流程；本項以文件與 UX 對齊為主，前端可依文件補「匯出／刪除帳號」入口與確認流程。

---

## 總結

| 項目 | 狀態 | 主要檔案／備註 |
|------|------|----------------|
| 主動關懷 (Active Care) | ✅ | active_care.py、run_active_care_dispatch.py、notification active_care |
| 衝突緩解 (Conflict Resolution) | ✅ | conflict_detection.py、mediation_session、mediation_runtime、journal_tasks、mediation API、mediation_invite |
| LEGAL-01 數位分手協議 | ✅ | docs/legal/digital-breakup-protocol.md、既有解除邏輯 |
| LEGAL-02 數位遺產聯絡人 | ✅ | users.legacy_contact_email、PATCH /me、docs/legal/legacy-contact.md |
| PRD-RISK-01 優雅退場 | ✅ | docs/product/graceful-exit.md |

**Test**：Backend 可跑 `pytest backend/tests/ -q`；主動關懷／調解可手動觸發腳本與 API 驗證。**Rollback**：見上；必要時關閉 matrix trigger、停跑 cron、還原 migration。
