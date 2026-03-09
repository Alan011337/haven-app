# P2-I. BI 與進階營運

**目標**：審核後台（Content Moderation Dashboard）與 BI 整合（Retention Cohorts / Metabase 或 Tableau），支援營運與合規。

---

## 範圍與完成狀態

| 項目 | 說明 | 產物 | 狀態 |
|------|------|------|------|
| **[ADMIN-02] Content Moderation Dashboard** | 針對 Whisper Wall 與 Deck Marketplace 的檢舉內容，建立人工審核介面。 | 後端：`ContentReport` 模型 + 檢舉/審核 API；前端：`/admin/moderation` 審核頁。 | ✅ 完成 |
| **[ADMIN-03] Business Intelligence (BI) Integration** | 將 DB 數據 ETL 到 Metabase 或 Tableau，分析 Retention Cohorts。 | 唯讀 DB 角色說明 + `docs/ops/bi-metabase-tableau.md`（連線、Cohort 查詢範例）。 | ✅ 完成 |

---

## 現況與前置

- **Admin**：已有 `GET /api/admin/audit-events`、`GET /api/admin/users/{user_id}/status`、`POST /api/admin/users/{user_id}/unbind`，依 `require_admin_user` 保護。
- **檢舉**：目前無 `ContentReport` 或檢舉 API；Whisper Wall / Deck Marketplace 若尚未上線，可先以「通用 UGC 檢舉」設計（resource_type = journal | card | 或預留 whisper_wall | deck_marketplace）。
- **BI**：有 `run_unit_economics_report.py`；無 Metabase/Tableau 連線或 Retention Cohort 產物。

---

## 已實作摘要

### [ADMIN-02]
- **後端**：`backend/app/models/content_report.py`（ContentReport、ContentReportStatus、ContentReportResourceType）；遷移 `g1p2i0000001_content_reports.py`。`POST /api/reports`（使用者提交檢舉）、`GET /api/admin/moderation/queue`、`POST /api/admin/moderation/{report_id}/resolve`（審核）；授權矩陣與測試見 `test_reports_authorization_matrix.py`、`test_admin_authorization_matrix.py`。
- **前端**：`frontend/src/app/admin/moderation/page.tsx`（佇列列表、狀態篩選、通過/駁回/隱藏）；設定頁連結「內容審核（管理員）」→ `/admin/moderation`。

### [ADMIN-03]
- **文件**：`docs/ops/bi-metabase-tableau.md`（唯讀角色、Metabase/Tableau 連線、Retention Cohort SQL 範例、安全與合規提醒）。

---

## 後續

- Whisper Wall / Deck Marketplace 產品定義確定後，將檢舉 `resource_type` 與前後端標籤對齊。
- BI：若需每日 ETL 到資料倉儲，可再加排程與文件。
