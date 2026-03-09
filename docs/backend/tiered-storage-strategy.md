# ARCH-01: Tiered Storage Strategy (分層儲存)

## 目標

冷熱分離：近期資料於主庫提供低延遲讀寫；超過一定時間之資料封存至 S3 (Cold Tier)，用於合規、還原與離線分析，減少主庫容量與成本。

---

## 1. 分層定義

- **Hot（熱）**：最近 3 個月（可配置，建議 90 天）內的 `journals`、`card_responses` 等，保留於主庫 PostgreSQL；所有線上 API 僅查詢熱資料。
- **Cold（冷）**：超過 3 個月的資料，匯出至 S3，格式為 JSONL（或 Parquet）；主庫可選擇保留最小欄位（如 id、user_id、created_at）做索引，或依合規需求保留/刪除。

---

## 2. 資料範圍與格式

- **表**：優先 `journals`、`card_responses`（依 `created_at` 判斷）。
- **冷資料切點**：`created_at < (today - ARCHIVE_COLD_AFTER_DAYS)`，預設 90。
- **匯出格式**：每行一筆 JSON（JSONL），檔名建議 `{table}_{YYYY-MM-DD}.jsonl` 或依 partition 日；可選壓縮（gzip）。
- **S3 路徑**：例如 `s3://<bucket>/cold-tier/<table>/<year>/<month>/`，便於生命週期與還原。

---

## 3. 應用層行為

- **讀寫**：API 僅查詢主庫；不直接讀 S3。冷資料還原時需先匯回主庫或專用還原流程。
- **封存腳本**：`backend/scripts/archive_cold_tier.py` — 依設定篩選冷資料、匯出 JSONL、上傳 S3；可選在主庫做 soft-delete 或保留僅 id/created_at 之索引列（依合規與還原需求決定）。

---

## 4. 執行與維運

- **排程**：以 cron 或排程系統定期執行 archive 腳本（例如每日一次），避免尖峰。
- **權限**：腳本執行環境需具 S3 寫入權限；建議 IAM role 或 key 僅限目標 bucket。
- **還原**：依 runbook 自 S3 下載 JSONL，經驗證後寫回主庫或還原用 DB；需注意 FK、唯一約束與順序。
- **生命週期**：可搭配 S3 lifecycle 將冷資料轉為 Glacier 等以進一步降成本。

---

## 5. 設定（腳本/環境）

- `COLD_TIER_S3_BUCKET`：目標 S3 bucket。
- `ARCHIVE_COLD_AFTER_DAYS`：超過此天數之資料視為冷（預設 90）。
- 可選：`ARCHIVE_DRY_RUN=1` 僅列出將封存之筆數與範圍，不實際上傳。

詳細參數與使用方式見 `backend/scripts/archive_cold_tier.py`。
