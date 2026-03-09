# P2-D. 智慧引導基礎 (Life Coach Basics) — 完成對照表

本文件對應 P2-D 開發清單與實作位置。

---

## ✅ 主動關懷邏輯 (Active Care)

- **DoD**：Backend Cron 偵測雙方連續 3 天無互動 → 推送輕鬆破冰話題或抽卡邀請。
- **實作**：
  - **腳本**：`backend/scripts/run_active_care_dispatch.py` — 每日執行（建議 cron 09:00）：找出有伴侶且「過去 3 天內雙方皆無日記、皆無卡片回答」的配對，對雙方各發一則 `active_care` 通知（破冰／抽卡邀請文案）。
  - **門檻**：`ACTIVE_CARE_NO_INTERACTION_DAYS = 3`；「無互動」= 雙方在 cutoff 之後無 `Journal` 且無 `CardResponse`。
  - **通知**：`backend/app/services/notification.py` — `action_type="active_care"`，文案「好久沒一起互動了，抽一張牌或寫一句話給對方吧～」；`build_partner_notification_payload` 支援 `event_type="active_care"`；`docs/security/notification-trigger-matrix.json` 已含 `active_care`（target: both，throttle 86400）。
  - **去重**：`scope_id = active_care:{today.isoformat()}`，每對每天最多各收一則。
- **Rollback**：停跑 cron；或從 matrix 關閉 `active_care` trigger。

---

## ✅ 衝突緩解模式 (Conflict Resolution)

- **DoD**：AI 偵測日記高風險關鍵字 → 切換調解模式，引導雙方回答引導式問題以換位思考。
- **實作**：
  - **關鍵字偵測**：`backend/app/services/conflict_detection.py` — `CONFLICT_RISK_KEYWORDS`（分手、討厭、生氣、恨、離婚、結束、不想在一起、受夠、絕望、放棄、不愛了、冷戰、吵架、爭吵等）；`detect_conflict_risk(content)` 回傳 bool。
  - **分析流程**：`backend/app/queue/journal_tasks.py` — 日記分析完成後呼叫 `detect_conflict_risk`，寫入 `Analysis.conflict_risk_detected`；若為 True 且為有效伴侶，呼叫 `trigger_mediation(session, user_id_1, user_id_2, triggered_by_journal_id)`。
  - **調解 session**：`backend/app/services/mediation_runtime.py` — `trigger_mediation` 建立 `MediationSession`；`MEDIATION_GUIDED_QUESTIONS` 三題（此刻你最希望對方理解的是什麼？／換成對方角度他可能感受什麼？／你願意為關係做的一件小事？）；`get_mediation_status`、`record_mediation_answers`。
  - **通知**：分析 job commit 後對雙方各發 `mediation_invite` 通知；`notification.py` 與 trigger matrix 已支援 `mediation_invite`。
  - **API**：`backend/app/api/routers/mediation.py` — `GET /api/mediation/status`（回傳 in_mediation、questions、my_answered、partner_answered、session_id）、`POST /api/mediation/answers?session_id=...`（記錄當前使用者已作答）。
  - **資料表**：`backend/app/models/mediation_session.py` — `MediationSession`（user_id_1、user_id_2、triggered_by_journal_id、user_1_answered_at、user_2_answered_at）。
- **前端**：可依 `GET /api/mediation/status` 顯示「調解模式」區塊與引導題，並以 `POST /api/mediation/answers` 送出作答。
- **Rollback**：關閉 matrix 之 `mediation_invite`；或於分析 job 內略過 `trigger_mediation` 與通知。

---

## ✅ [LEGAL-01] Digital Breakup Protocol（數位分手協議）

- **DoD**：產品與法務對齊之數位分手流程（解除連結、資料保留／刪除、可選冷靜期）。
- **實作**：
  - **文件**：`docs/legal/digital-breakup-protocol.md` — 解除伴侶連結、資料保留與刪除、可選冷靜期；與條款之關係；實作對照（後端 partner_id 解除、前端設定頁、條款提及）。
  - **後端**：解除伴侶邏輯（如 `app.api.routers.users.routes` 中 PATCH /me 或專用 unpair）；BOLA 與 `verify_active_partner_id` 確保解除後無法存取對方資料。
- **Rollback**：文件還原；解除流程若已上線可保留，僅調整文案或冷靜期。

---

## ✅ [LEGAL-02] Legacy Contact（數位遺產聯絡人）

- **DoD**：用戶可設定數位遺產聯絡人；驗證與流程依 runbook。
- **實作**：
  - **文件**：`docs/legal/legacy-contact.md` — 設定、驗證與流程、隱私；實作對照。
  - **後端**：`User.legacy_contact_email`（已存在）；`UserUpdate.legacy_contact_email`；`PATCH /api/users/me` 可更新 `legacy_contact_email`（見 `update_user_me`）。
  - **前端**：設定頁可提供「數位遺產聯絡人」欄位（選填）與說明；法務與隱私政策需載明數位遺產政策與申請方式。
- **Rollback**：停用設定欄位；欄位保留不影響登入或日常通知。

---

## ✅ [PRD-RISK-01] The Graceful Exit（優雅退場）

- **DoD**：產品流程說明：解除連結、通知、資料保留、可選冷靜期。
- **實作**：
  - **文件**：`docs/prd/GRACEFUL_EXIT.md` — 解除伴侶、通知與狀態、資料與保留、可選冷靜期；與 LEGAL-01 之關係；實作對照（後端 unpair、前端設定頁、partner_unbound 通知）。
- **Rollback**：文件還原。

---

## 總結

| 項目 | 狀態 | 主要檔案／備註 |
|------|------|----------------|
| 主動關懷 (Active Care) | ✅ | run_active_care_dispatch.py、notification active_care、trigger matrix |
| 衝突緩解 (Conflict Resolution) | ✅ | conflict_detection、mediation_runtime、journal_tasks、mediation API、trigger matrix mediation_invite |
| LEGAL-01 數位分手協議 | ✅ | docs/legal/digital-breakup-protocol.md、後端解除邏輯對照 |
| LEGAL-02 數位遺產聯絡人 | ✅ | docs/legal/legacy-contact.md、User.legacy_contact_email、PATCH /me |
| PRD-RISK-01 優雅退場 | ✅ | docs/prd/GRACEFUL_EXIT.md |

**Cron 建議**：  
- `run_active_care_dispatch.py`：每日 09:00（依部署環境設定 cron 或排程）。  
**Test**：  
- 單元測試可覆蓋 `detect_conflict_risk`、`trigger_mediation`、`get_mediation_status`、`record_mediation_answers`；Active Care 腳本可手動執行並檢查日誌與通知。
