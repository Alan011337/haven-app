# P2-B. 擴展基石 (Scalability Foundation) — 完成對照表

目標：為千萬級、億級使用者預先鋪路，避免單點崩潰。本文件對應各項實作狀態與檔案位置。

---

## ✅ 資料庫分片準備 (Sharding / Partitioning Strategy)

- **DoD**：journals、card_responses 依 created_at（或 user_id）進行 Partitioning 設計。
- **實作**：
  - **策略文件**：`docs/backend/partitioning-strategy.md` — journals / card_responses 採 `PARTITION BY RANGE (created_at)`，以月為分區；含 PostgreSQL 建立步驟（CREATE TABLE ... PARTITION BY RANGE、月分區、遷移、替換）。
  - **Alembic**：`backend/alembic/versions/g1p2b0000001_journals_card_responses_partitioning_prep.py` — 於 PostgreSQL 為 `journals`、`card_responses` 加上 table comment，標註分區意圖與文件連結。
  - **實際建立分區**：依文件由維運在維護窗口執行，或未來以 `ENABLE_PARTITIONING=1` 觸發 migration；應用層表名不變。
- **Rollback**：僅 comment 時可 downgrade 移除 comment；已做 partition 替換則需依 runbook 還原。

---

## ✅ 讀寫分離 (Read Replica)

- **DoD**：高頻讀取（歷史紀錄）不影響核心寫入（日記/抽卡）效能。
- **實作**：
  - **設定**：`backend/app/core/config.py` — `DATABASE_READ_REPLICA_URL`（可選）；未設時讀寫皆用主庫。
  - **Session**：`backend/app/db/session.py` — `engine_read` 由 `DATABASE_READ_REPLICA_URL` 建立；`get_read_session()` 使用 `engine_read`。
  - **依賴**：`backend/app/api/deps.py` — `ReadSessionDep = Annotated[Session, Depends(get_read_session)]`。
  - **讀路徑**：
    - 日記列表：`backend/app/api/journals.py` — `read_my_journals`、`read_partner_journals` 使用 `ReadSessionDep`。
    - 牌組歷史：`backend/app/api/routers/card_decks.py` — `get_deck_history`、`get_deck_history_summary` 使用 `ReadSessionDep`。
  - 寫入（日記 create/update/delete、抽卡/揭牌）一律使用 `SessionDep`（主庫）。
- **Rollback**：清空 `DATABASE_READ_REPLICA_URL` 即全部走主庫。

---

## ✅ WebSocket 水平擴展 (Redis Pub/Sub)

- **DoD**：跨伺服器訊息廣播，解決單機記憶體限制。
- **實作**：
  - **Manager**：`backend/app/core/socket_manager.py` — `ConnectionManager`（單機 in-memory）、`RedisBackedConnectionManager`（Redis Pub/Sub）；`create_socket_manager(redis_url)` 當 `REDIS_URL` 有值時回傳 Redis 版。
  - **Channel**：`WS_REDIS_CHANNEL = "haven:ws:send"`；publish 格式 `{"user_id": str, "message": dict}`。
  - **生命週期**：`backend/app/main.py` — `lifespan` 內 `await init_socket_manager(settings.REDIS_URL)`、shutdown 時 `await shutdown_socket_manager()`；Redis 版會啟動 subscriber loop 並在關閉時取消。
  - **行為**：送給使用者的訊息改為 `publish` 到 Redis；任一 instance 的 subscriber 收到後若該 user 連在本 instance 則轉發，否則由持有連線的 instance 轉發。
- **Rollback**：移除或清空 `REDIS_URL` 即退回單機 in-memory。

---

## ✅ [DATA-READ-01] Read model / denormalization (P0)

- **DoD**：journal feed、streak summary 使用 materialized view / precomputed table。
- **實作**：
  - **Streak summary**：
    - 表：`backend/alembic/versions/g1p2b0000002_user_streak_summary_read_model.py` — `user_streak_summary`（user_id, partner_id, streak_*, level_*, love_bar_percent, level_title, updated_at）。
    - 讀路徑：`backend/app/services/gamification.py` — `get_or_compute_streak_summary()` 先查 `user_streak_summary`，在 TTL 內且 partner 一致則直接回傳；否則計算並 upsert。TTL：`settings.STREAK_SUMMARY_CACHE_TTL_SECONDS`（預設 300）。
  - **Journal feed**：
    - 目前：讀取走 **Read Replica**（`read_my_journals`、`read_partner_journals` 使用 `ReadSessionDep`），查詢 Journal + Analysis，無額外 MV。
    - 可選後續：可新增 materialized view 或 precomputed table（如 `journal_feed_cache`）並在寫入/分析時更新，進一步減輕主庫/副本負載；現階段以讀寫分離 + 索引滿足擴展需求。
- **Rollback**：streak 可改回僅計算不寫入 `user_streak_summary`（或 drop table）；journal feed 維持現狀即可。

---

## ✅ [CACHE-01] Cache strategy (P0)

- **DoD**：建立 CDN/edge cache 與 server-side cache 策略。
- **實作**：
  - **策略文件**：`docs/backend/cache-strategy.md` — 定義 CDN/edge 適用範圍（靜態資源、可快取之公開 API）、server-side 使用 Redis（streak 摘要 TTL、abuse guard、queue）、快取鍵與 TTL、失效與 bypass 原則。
  - **現有 server-side**：`STREAK_SUMMARY_CACHE_TTL_SECONDS`（應用層讀 `user_streak_summary` 的 TTL）、abuse guard 使用 Redis 時為 `ABUSE_GUARD_REDIS_URL`、queue 使用 `REDIS_URL`。
  - **CDN/edge**：由前端/維運依文件對靜態資源與可快取回應設定；API 預設不帶 long cache，需時由回應頭或 proxy 設定。
- **Rollback**：文件與設定還原；關閉 Redis 時 abuse/queue 已有 memory 或同步 fallback。

---

## ✅ [QUEUE-01] Async pipeline (P0)

- **DoD**：分析、推播、週報/月報全部走 queue，避免卡住寫入。
- **實作**：
  - **佇列**：`backend/app/queue/journal_tasks.py` — Redis list `haven:queue:journal_analysis`、`haven:queue:journal_notify`；當 `REDIS_URL` 且 `ASYNC_JOURNAL_ANALYSIS=True` 時，日記建立後只寫 DB 並 enqueue，分析與伴侶通知於 background worker 執行。
  - **設定**：`backend/app/core/config.py` — `ASYNC_JOURNAL_ANALYSIS`（預設 True）。
  - **生命週期**：`backend/app/main.py` — `start_journal_queue_workers()` / `stop_journal_queue_workers()` 於 lifespan 啟停。
  - **週報/月報**：目前產品端無使用者週報/月報排程；同佇列模式已預留，未來可新增 `haven:queue:weekly_digest` / `haven:queue:monthly_digest` 與對應 worker，不影響現有寫入路徑。
- **Rollback**：設 `ASYNC_JOURNAL_ANALYSIS=False` 或移除 `REDIS_URL` 即改回同步分析/通知。

---

## ✅ [ARCH-01] Tiered Storage Strategy (分層儲存)

- **DoD**：冷熱分離，3 個月前數據封存至 S3 (Cold Tier)。
- **實作**：
  - **策略文件**：`docs/backend/tiered-storage-strategy.md` — 熱資料：近 3 個月 journals / card_responses 於主庫查詢；冷資料：超過 3 個月封存至 S3（路徑、格式、生命週期、還原流程）。
  - **腳本**：`backend/scripts/archive_cold_tier.py` — 可執行之 stub：依 `ARCHIVE_COLD_AFTER_DAYS`（預設 90）篩選舊資料、匯出為 JSONL 上傳 S3、並可選標記或保留主庫紀錄；需設定 `COLD_TIER_S3_BUCKET`、AWS 權限等（見腳本與文件）。
  - 應用層讀取仍以主庫（熱）為準；冷資料僅供合規/還原/離線分析。
- **Rollback**：停跑 archive 腳本；已封存資料可依 runbook 自 S3 還原。

---

## 總結

| 項目 | 狀態 | 主要檔案/備註 |
|------|------|----------------|
| 資料庫分片準備 | ✅ | partitioning-strategy.md, g1p2b0000001 |
| 讀寫分離 | ✅ | config DATABASE_READ_REPLICA_URL, session.py, deps ReadSessionDep, journals + card_decks 讀徑 |
| WebSocket Redis Pub/Sub | ✅ | socket_manager.py RedisBackedConnectionManager, main.py lifespan |
| DATA-READ-01 | ✅ | user_streak_summary + get_or_compute；journal feed 用 read replica，可選 MV 後續 |
| CACHE-01 | ✅ | cache-strategy.md, STREAK_SUMMARY_CACHE_TTL_SECONDS, abuse/queue Redis |
| QUEUE-01 | ✅ | journal_tasks.py 分析+通知 queue；週報/月報可擴同一模式 |
| ARCH-01 | ✅ | tiered-storage-strategy.md, archive_cold_tier.py |

**Test**：  
- 單元/整合測試沿用現有；讀徑可透過設定 `DATABASE_READ_REPLICA_URL` 做手動驗證。  
- Partitioning、archive 腳本需於目標環境依文件與腳本註解執行。  
**Rollback**：各項見上；必要時關閉對應 env（READ_REPLICA、REDIS_URL、ASYNC_JOURNAL_ANALYSIS）或停用 archive 腳本。
