# CACHE-01: Cache Strategy (P0)

## 目標

建立 CDN/edge cache 與 server-side cache 策略，降低主庫與 API 負載，支援高頻讀取與橫向擴展。

---

## 1. CDN / Edge Cache

- **適用**：靜態資源（JS/CSS/圖片、前端 build 產物）、可快取的公開 API 回應（若日後有）。
- **建議**：
  - 靜態資源：部署於 CDN（如 Cloudflare、Vercel Edge、AWS CloudFront），設定 `Cache-Control: public, max-age=…`（例如 1 年並以 hash 檔名做 immutable）。
  - API：預設不帶 long cache；若特定 GET 為公開且可接受延遲一致性，可於該 endpoint 回傳 `Cache-Control: private, max-age=…` 或由反向代理設定。
- **失效**：前端資源以檔名 hash 為主，部署即失效；API 依 max-age 或 proxy 設定。

---

## 2. Server-Side Cache (Redis)

- **用途**：讀多寫少、可接受短期不一致的資料；佇列與跨 instance 狀態。
- **現有使用**：
  - **Streak 摘要**：`user_streak_summary` 表 + 應用層 TTL `STREAK_SUMMARY_CACHE_TTL_SECONDS`（秒）；在 TTL 內直接讀表，逾時再計算並 upsert。不需額外 Redis key，讀表即為「server-side cache」。
  - **Abuse guard**：當 `ABUSE_GUARD_STORE_BACKEND=redis` 且 `ABUSE_GUARD_REDIS_URL` 設定時，WS/API 限流狀態存於 Redis，key prefix `haven:abuse`。
  - **Queue**：`REDIS_URL` — journal 分析/通知佇列（`haven:queue:journal_analysis`、`haven:queue:journal_notify`）。
  - **WebSocket**：`REDIS_URL` — 跨 instance 廣播 channel `haven:ws:send`。
- **鍵與 TTL 原則**：
  - 鍵名：`haven:<domain>:<id>` 或 `haven:queue:*`、`haven:ws:*`、`haven:abuse:*`。
  - TTL：依功能設定（例如 abuse 視 window_seconds）；streak 為 DB 表 + 應用 TTL，非 Redis TTL。
- **失效**：佇列消費即刪；abuse 依時間窗口；streak 依 `updated_at` 與設定 TTL 判定是否重算。

---

## 3. 快取 Bypass / 一致性

- **寫入後**：日記/抽卡寫入後，讀徑使用 **Read Replica** 或本機讀；replica 延遲通常為秒級，可接受。
- **Streak**：寫入日記或分數後，`get_or_compute_streak_summary` 會重算並 upsert，下次讀取即為新值；若需即時可將 TTL 調短或寫入後主動 invalidate（目前為 TTL 自然過期）。
- **不快取**：個人化、即時性高、含 PII 的 API 不建議 CDN 或 long cache；僅 server-side 短期 TTL 可考慮。

---

## 4. 設定總覽

| 設定 | 用途 |
|------|------|
| `REDIS_URL` | Queue、WebSocket Pub/Sub |
| `ABUSE_GUARD_REDIS_URL` | Abuse 限流狀態（可與 REDIS_URL 同或分庫） |
| `STREAK_SUMMARY_CACHE_TTL_SECONDS` | Streak 讀表快取 TTL（0 = 每次重算） |

CDN/edge 由前端與維運依本策略於部署與 proxy 設定中實作。
