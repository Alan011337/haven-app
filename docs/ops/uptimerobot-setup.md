# UptimeRobot Setup Guide — 服務監控設定

> Haven 生產環境的外部健康檢查設定，使用 UptimeRobot 監控 API 可用性。

## Monitor 設定

### HTTP Monitor（主要）

| 欄位 | 值 |
|------|-----|
| Monitor Type | HTTP(s) |
| Friendly Name | `Haven API - Production` |
| URL | `https://<PRODUCTION_DOMAIN>/health` |
| HTTP Method | GET |
| Monitoring Interval | 5 minutes |
| Timeout | 30 seconds |

### Keyword Monitor（進階驗證）

除了 HTTP status code 之外，額外驗證回應內容：

| 欄位 | 值 |
|------|-----|
| Monitor Type | Keyword |
| Keyword | `"status":"ok"` |
| Keyword Type | Keyword Exists |
| URL | `https://<PRODUCTION_DOMAIN>/health` |
| Monitoring Interval | 5 minutes |

> 說明：Keyword Monitor 確保不只是 HTTP 200，而是 `/health` endpoint 真的回傳了正確的健康狀態 JSON。

---

## Alert 條件

監控會在以下任一條件觸發告警：

1. **HTTP status != 200** — 伺服器回傳非 200 狀態碼
2. **Response body 不包含 `"status":"ok"`** — 應用層級異常（例如資料庫連線失敗、Redis 不可用）

### `/health` 預期回應格式

```json
{
  "status": "ok",
  "version": "2.x.x",
  "database": "healthy",
  "redis": "healthy",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

當任一依賴不健康時，status 會變為 `"degraded"` 或 `"unhealthy"`，此時 Keyword Monitor 會觸發告警。

---

## Alert Channels 設定

### Email（必設）

| 欄位 | 值 |
|------|-----|
| Alert Contact Type | E-mail |
| E-mail Address | `ops@<your-domain>` 或團隊信箱 |
| Threshold | Alert after 1 failed check |
| Reminder | Every 30 minutes while down |

### Slack Webhook（選配）

| 欄位 | 值 |
|------|-----|
| Alert Contact Type | Webhook |
| URL | Slack Incoming Webhook URL |
| POST Value (JSON) | 見下方 |

```json
{
  "text": "🚨 Haven API Alert: *monitorFriendlyName* is *alertType*\nURL: *monitorURL*\nDetails: *alertDetails*"
}
```

> 在 Slack 建立 Incoming Webhook：Slack App > Incoming Webhooks > Add New Webhook to Workspace

---

## 設定步驟

1. 登入 [UptimeRobot](https://uptimerobot.com)
2. 點擊 **+ Add New Monitor**
3. 依照上方表格填入 HTTP Monitor 設定
4. 再建立一個 Keyword Monitor（同一個 URL）
5. 在 **My Settings > Alert Contacts** 新增 Email 和/或 Slack Webhook
6. 將 Alert Contacts 綁定到兩個 Monitor
7. 儲存後等待首次檢查確認綠燈

## 驗證

建立完成後進行手動驗證：

```bash
# 確認 health endpoint 正常回應
curl -s https://<PRODUCTION_DOMAIN>/health | jq .

# 預期輸出包含 "status": "ok"
```

## Status Page（選配）

UptimeRobot 提供免費 Status Page，可公開給使用者：

- 在 Dashboard > Status Pages > Create Status Page
- 加入 Haven API Monitor
- 自訂域名（選配）：`status.<your-domain>`

---

## 注意事項

- 免費方案支援最多 50 個 monitors，5 分鐘間隔
- 若需要 1 分鐘間隔，需升級 Pro 方案
- 建議同時監控前端 (`https://<FRONTEND_DOMAIN>`) 的可用性
- Keyword Monitor 比單純 HTTP Monitor 更能捕捉應用層異常
