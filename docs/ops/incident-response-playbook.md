# Incident Response Playbook — 事件應變手冊

> Haven 生產環境常見異常的診斷與處理流程。當 `/health` 或 `/health/slo` 回報異常時，依照本手冊逐步排查。

---

## 1. `database_unhealthy` — 資料庫不健康

### 症狀
- `/health` 回傳 `"database": "unhealthy"`
- API 回傳 500 錯誤，日誌出現 `ConnectionRefusedError` 或 `OperationalError`

### 診斷步驟

```
1. 確認 Supabase 服務狀態
   → https://status.supabase.com/
   → Supabase Dashboard > Project > Database > Health

2. 驗證連線字串
   → 確認 DATABASE_URL 環境變數正確
   → 確認密碼未過期或被重設

3. 檢查連線池
   → Supabase Dashboard > Database > Connection Pooling
   → 確認 active connections 未達上限（免費方案上限約 60）

4. 檢查是否有長時間鎖定的 query
   → Supabase SQL Editor:
     SELECT pid, now() - pg_stat_activity.query_start AS duration, query
     FROM pg_stat_activity
     WHERE state != 'idle'
     ORDER BY duration DESC;
```

### 處理

| 狀況 | 動作 |
|------|------|
| Supabase 全域故障 | 等待恢復，啟用降級模式（唯讀快取） |
| 連線字串錯誤 | 修正 `.env` 並重啟服務 |
| 連線池耗盡 | 重啟應用以釋放 idle connections |
| 長時間 query | `SELECT pg_terminate_backend(<pid>);` 終止異常查詢 |

---

## 2. `redis_unhealthy` — Redis 不健康

### 症狀
- `/health` 回傳 `"redis": "unhealthy"`
- WebSocket rate limiting 或 session 功能異常

### 診斷步驟

```
1. 確認 Redis 連線
   → 檢查 REDIS_URL 環境變數
   → 嘗試手動連線：redis-cli -u $REDIS_URL ping

2. 檢查 Redis 服務狀態
   → 若使用 Upstash：https://console.upstash.com/
   → 確認未超過免費方案 daily command 上限

3. 檢查記憶體用量
   → redis-cli INFO memory
   → 確認 used_memory 未超過 maxmemory
```

### 處理

| 狀況 | 動作 |
|------|------|
| Redis 完全不可用 | **接受 memory fallback**：系統自動降級為 in-memory rate limiting |
| 連線字串錯誤 | 修正 `REDIS_URL` 並重啟 |
| 超過用量上限 | 升級方案或清理過期 keys |

> **重要：** Haven 設計上 Redis 為可選依賴。Redis 不可用時系統仍可運作，僅影響跨 instance 的 rate limiting 一致性。

---

## 3. `ws_sli_below_target` — WebSocket SLI 低於目標

### 症狀
- `/health/slo` 回傳 WebSocket 相關 SLI 低於目標值
- 使用者回報即時通訊延遲或斷線

### 診斷步驟

```
1. 查看 SLO 指標
   → GET /health/slo
   → 關注：ws_connection_success_rate, ws_message_latency_p99

2. 檢查 WS abuse guard 指標
   → 確認是否有異常高頻連線（可能為濫用）
   → 查看 rate limiting 日誌

3. 檢查伺服器資源
   → 確認 CPU / Memory 用量
   → 確認 concurrent WebSocket connections 數量

4. 檢查 upstream 依賴
   → 資料庫回應時間是否正常
   → AI provider 是否有延遲
```

### 處理

| 狀況 | 動作 |
|------|------|
| 單一 IP 異常高頻 | 確認 abuse guard 已自動封鎖，必要時手動 ban |
| 伺服器資源不足 | 水平擴展或垂直升級 |
| 上游延遲 | 參考對應 provider 的處理流程 |
| SLI 短暫波動 | 持續觀察，若 15 分鐘內恢復則無需介入 |

### 3.1 Vicky Disconnect（伴侶/連線中斷演練，OPS-04）

每週五下午與 Chaos Drill 同步進行 tabletop 或乾跑：

- **情境**：一側使用者 WebSocket 斷線或「伴侶離線」，另一側仍在使用。
- **驗證**：重連流程、離線佇列 replay、通知（Email/推播）是否可觸達；降級時不影響讀取已存資料。
- **步驟**：依 `chaos-drill-spec.md` 與本節執行 tabletop，記錄於 chaos-drill 證據或 runbook。

---

## 4. `providers.openai.error` — OpenAI API 異常

## 3.1 `abuse_economics_budget_block` — 濫用成本預算觸發封鎖

### 症狀
- `/health` 回傳 `degraded_reasons` 含 `abuse_economics_budget_block`
- `/health/slo` 的 `sli.abuse_economics.evaluation.status = "block"` 或 `warn`
- release gate (`check_slo_burn_rate_gate.py`) 回報 `abuse_economics_block`

### 診斷步驟

```
1. 先看 runtime scorecard
   → GET /health/slo
   → sli.abuse_economics.vectors[*] 的 observed_events_total / projected_daily_events / status

2. 判斷是哪一條向量觸發
   → token_drain_journal_analysis / ws_storm / pairing_bruteforce / push_notification_spam / signup_abuse

3. 對照對應控制面
   → rate_limit defaults（JOURNAL/CARD/LOGIN/PAIRING）
   → WS guard defaults（connection/message/backoff/payload）
```

### 處理

| 狀況 | 動作 |
|------|------|
| `ws_storm` block | 先提高封鎖強度（降低 `WS_MESSAGE_RATE_LIMIT_COUNT` / `WS_MAX_CONNECTIONS_GLOBAL`），必要時暫時封鎖來源 IP |
| `pairing_bruteforce` block | 降低 pairing user/ip limit、拉長 cooldown，檢查 invite code 暴力嘗試來源 |
| `token_drain_journal_analysis` / `signup_abuse` block | 收緊 login/journal/card 寫入限流，必要時啟用更嚴格風險控管 |
| 只有 `warn` | 先觀察 15~30 分鐘；若持續升高，提前套用 block 的收斂動作 |

### 回滾

- 若誤殺過高：僅回調單一限流參數，不要同時放寬全部控制。
- 每次調整需記錄：
  - 變更前後值
  - 觸發向量
  - 預期恢復時間

### 症狀
- AI 功能（安全分析、卡片生成等）回傳錯誤
- 日誌出現 `openai.APIError`、`AuthenticationError`、`RateLimitError`

### 診斷步驟

```
1. 確認 OpenAI 服務狀態
   → https://status.openai.com/

2. 驗證 API Key
   → 確認 OPENAI_API_KEY 環境變數正確
   → 確認 key 未被撤銷

3. 檢查帳單狀態
   → https://platform.openai.com/account/billing
   → 確認餘額充足，未超過 usage limit

4. 檢查 rate limits
   → 確認未超過 TPM / RPM 限制
   → 查看 response headers: x-ratelimit-remaining-*
```

### 處理

| 狀況 | 動作 |
|------|------|
| OpenAI 全域故障 | 等待恢復，啟用降級模式（停用 AI 功能，保留基本日記/卡片） |
| API Key 無效 | 重新產生 key 並更新環境變數 |
| 餘額不足 | 儲值或提高 usage limit |
| Rate limit | 確認 request batching 正常，必要時升級方案 |

---

## 5. `providers.email.warning` — Email 發送異常

### 症狀
- 邀請信、通知信未送達
- 日誌出現 Resend API 錯誤

### 診斷步驟

```
1. 確認 Resend 服務狀態
   → https://resend-status.com/

2. 驗證 API Key
   → 確認 RESEND_API_KEY 環境變數正確
   → Resend Dashboard > API Keys 確認 key 有效

3. 檢查域名驗證
   → Resend Dashboard > Domains
   → 確認 DNS records (SPF, DKIM) 正確設定

4. 檢查發送量
   → 確認未超過免費方案 daily limit (100 emails/day)
```

### 處理

| 狀況 | 動作 |
|------|------|
| API Key 無效 | 重新產生 `RESEND_API_KEY` 並更新環境變數 |
| 域名未驗證 | 補設 DNS records，等待傳播 |
| 超過發送上限 | 升級方案或延後非緊急郵件 |
| Resend 全域故障 | Email 為非關鍵路徑，記錄失敗並排入重試佇列 |

> **注意：** Email 為非阻塞功能（non-blocking）。發送失敗不應影響核心功能運作。

---

## 通用應變原則

1. **確認影響範圍** — 先釐清是全域故障還是局部異常
2. **查看日誌** — `docker logs haven-api` 或雲端 log explorer
3. **不要恐慌重啟** — 先診斷再行動，盲目重啟可能遺失問題線索
4. **記錄事件** — 事後填寫 incident report，包含時間軸、根因、改善措施
5. **通知相關人員** — 若影響使用者體驗，透過 Status Page 或應用內通知告知

## Chaos Drill Cadence

1. 週期：每週五 UTC 自動演練（workflow：`/Users/alanzeng/Desktop/Projects/Haven/.github/workflows/chaos-drill.yml`）。
2. 演練範圍：
   - `ai_provider_outage`
   - `ws_storm`
3. 規格文件：`/Users/alanzeng/Desktop/Projects/Haven/docs/ops/chaos-drill-spec.md`
4. 報告模板：`/Users/alanzeng/Desktop/Projects/Haven/docs/ops/chaos-drill-report-template.md`

## Escalation 聯絡

| 層級 | 負責 | 時機 |
|------|------|------|
| L1 | 值班工程師 | 自動告警觸發後 5 分鐘內回應 |
| L2 | 技術負責人 | L1 無法在 30 分鐘內解決 |
| L3 | 外部支援 (Supabase/OpenAI) | 確認為第三方服務問題 |
