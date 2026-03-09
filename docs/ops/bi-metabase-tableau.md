# BI 整合：Metabase / Tableau 與 Retention Cohorts

**P2-I [ADMIN-03]**：將 DB 數據用於 BI 分析（Metabase 或 Tableau），並支援 Retention Cohort 分析。

---

## 1. 連線方式

### 1.1 建議：唯讀資料庫角色

- **目的**：BI 工具僅能讀取，不得寫入或刪除。
- **作法**（以 Supabase/Postgres 為例）：
  1. 在 DB 建立專用角色，例如 `bi_readonly`。
  2. 授予 `CONNECT` 於目標 database，`USAGE` 於 schema（如 `public`），`SELECT` 於需分析之 table（見下表）。
  3. 不授予 `INSERT` / `UPDATE` / `DELETE` / `DDL`。

```sql
-- 範例（依實際 DB 調整）
CREATE ROLE bi_readonly WITH LOGIN PASSWORD '...';
GRANT CONNECT ON DATABASE your_db TO bi_readonly;
GRANT USAGE ON SCHEMA public TO bi_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO bi_readonly;
```

### 1.2 Metabase

- **連線**：新增 PostgreSQL 資料來源，主機/埠/資料庫名與現有 `DATABASE_URL` 一致，帳密使用上述唯讀角色。
- **注意**：若 Metabase 與 App 共用同一 DB，強烈建議使用唯讀帳號，避免誤寫。

### 1.3 Tableau

- **連線**：Tableau 新增 PostgreSQL 連線，同樣使用唯讀角色之連線字串。
- **抽取（Extract）**：可對大表做定期抽取以減輕 DB 負載，排程建議避開應用高峰。

---

## 2. 可分析之資料（參考）

| 資料來源 | 說明 |
|----------|------|
| `users` | 註冊、`created_at`、`partner_id`（配對）、軟刪除 `deleted_at` |
| `journals` | 日記、`user_id`、`created_at`、內容不建議直接給 BI（PII）；可僅用計數與時間 |
| `card_responses` / `card_sessions` | 抽卡與回答行為、時間 |
| `audit_events` | 審計事件、行為類型、時間 |
| `notification_events` | 通知發送與狀態（若需分析觸達） |

PII 與敏感欄位應依資料分類政策限制 BI 存取或遮罩；必要時僅匯出聚合或匿名化結果。

---

## 3. Retention Cohorts 定義與查詢範例

### 3.1 名詞

- **Cohort**：以「註冊週」或「註冊日」為一組用戶。
- **Retention**：該組在註冊後第 N 天（或第 N 週）是否仍有指定行為（例如寫日記、抽卡、登入）。

### 3.2 註冊週 Cohort + D1/D7/D30 留存（行為：有寫日記）

```sql
-- 範例：每週註冊的用戶數，以及該週用戶在 D1/D7/D30 有寫日記的人數
WITH signups AS (
  SELECT
    id AS user_id,
    date_trunc('week', created_at) AS signup_week,
    created_at
  FROM users
  WHERE deleted_at IS NULL
),
cohort_activity AS (
  SELECT
    s.signup_week,
    s.user_id,
    MAX(CASE WHEN j.created_at::date <= s.created_at::date + 1 THEN 1 ELSE 0 END) AS d1_journal,
    MAX(CASE WHEN j.created_at::date <= s.created_at::date + 7 THEN 1 ELSE 0 END) AS d7_journal,
    MAX(CASE WHEN j.created_at::date <= s.created_at::date + 30 THEN 1 ELSE 0 END) AS d30_journal
  FROM signups s
  LEFT JOIN journals j ON j.user_id = s.user_id AND j.deleted_at IS NULL
  GROUP BY s.signup_week, s.user_id
)
SELECT
  signup_week,
  COUNT(*) AS cohort_size,
  SUM(d1_journal) AS d1_retained,
  SUM(d7_journal) AS d7_retained,
  SUM(d30_journal) AS d30_retained,
  ROUND(100.0 * SUM(d1_journal) / NULLIF(COUNT(*), 0), 2) AS d1_pct,
  ROUND(100.0 * SUM(d7_journal) / NULLIF(COUNT(*), 0), 2) AS d7_pct,
  ROUND(100.0 * SUM(d30_journal) / NULLIF(COUNT(*), 0), 2) AS d30_pct
FROM cohort_activity
GROUP BY signup_week
ORDER BY signup_week DESC;
```

### 3.3 依產品需求調整

- 可將「有寫日記」改為「有抽卡」「有配對」等，或改為「任意 API 活動」（需有對應事件表或 audit）。
- 時間窗口可改為「日」或「週」；Cohort 可改為「註冊日」。

---

## 4. ETL 與排程（可選）

- 若需定期同步到資料倉儲：可撰寫腳本（例如 Python 或 SQL）自 DB 匯出聚合表或 Cohort 結果到檔案／另一 DB，再由 Metabase/Tableau 連線該倉儲。
- 排程建議使用 cron 或 CI/workflow，並避開應用尖峰；連線同樣建議使用唯讀角色。

---

## 5. 安全與合規

- BI 連線與 ETL 使用**唯讀**帳號，不持有寫入權限。
- 依 `docs/security` 資料分類與 PII 政策，限制或遮罩敏感欄位。
- 存取 BI 工具的人員與範圍應納入存取控制與稽核。
