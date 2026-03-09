# P2-B: 資料庫分片準備 (Sharding / Partitioning Strategy)

## 目標

為 `journals` 與 `card_responses` 依 `created_at`（或 `user_id`）進行 Partitioning 設計，支援千萬級資料量與冷熱分離。

## 策略

- **journals**：`PARTITION BY RANGE (created_at)`，以「月」為分區（可依資料量改為週或季）。
- **card_responses**：同上，`PARTITION BY RANGE (created_at)`。

PostgreSQL 無法直接 `ALTER TABLE ... PARTITION BY`；需建立新 partitioned table，遷移資料後替換。

## 實作步驟（PostgreSQL）

### 1. journals

```sql
-- 1) 建立 partitioned 表（與 journals 同結構，含 PK/FK/index）
CREATE TABLE journals_new (
    LIKE journals INCLUDING DEFAULTS INCLUDING CONSTRAINTS
) PARTITION BY RANGE (created_at);

-- 2) 建立分區（依實際時間範圍調整）
CREATE TABLE journals_2025_01 PARTITION OF journals_new
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE journals_2025_02 PARTITION OF journals_new
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
-- ... 每月一分區
CREATE TABLE journals_default PARTITION OF journals_new DEFAULT;

-- 3) 建立 FK、index（若 LIKE 未帶入）
ALTER TABLE journals_new ADD CONSTRAINT journals_new_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id);
-- ... 其他 FK 與 ix_journals_*

-- 4) 遷移資料
INSERT INTO journals_new SELECT * FROM journals;

-- 5) 替換（需停寫或雙寫窗口）
DROP TABLE journals;
ALTER TABLE journals_new RENAME TO journals;
```

### 2. card_responses

同邏輯：`CREATE TABLE card_responses_new (LIKE card_responses ...) PARTITION BY RANGE (created_at)`，建立月分區與 default，遷移後替換。

## 注意事項

- 遷移期間鎖表或使用邏輯複製以減少停機。
- 應用程式無需改動（表名仍為 `journals` / `card_responses`）。
- 新環境可在 init 時直接建立 partitioned 表，跳過非 partitioned 表。

## Alembic

可選：設 `ENABLE_PARTITIONING=1` 時執行上述步驟的 migration，或由維運依本文件手動執行。
