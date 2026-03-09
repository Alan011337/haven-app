# Web Push Observability & Cleanup (P1)

## Why
- 需要可觀測性來確認「送達率、延遲、無效訂閱清理」是否健康。
- 需要可回滾 dry-run 路徑，避免一上線就造成推播風暴。

## How
- Subscription lifecycle：
  - `ACTIVE` -> `INVALID` -> `TOMBSTONED` -> `PURGED`
- API：
  - `GET /api/users/push-subscriptions`
  - `POST /api/users/push-subscriptions`
  - `DELETE /api/users/push-subscriptions/{subscription_id}`
  - `POST /api/users/push-subscriptions/dry-run`
- Cleanup job：
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_push_subscription_cleanup.py`
  - 預設 dry-run；`--execute` 才會真正更新狀態。

## What
- 資料模型：
  - `endpoint`, `endpoint_hash`, `keys`, `created_at`, `last_success_at`, `fail_reason`, `state`
- 主要設定：
  - `PUSH_MAX_SUBSCRIPTIONS_PER_USER`
  - `PUSH_DEFAULT_TTL_SECONDS`
  - `PUSH_INVALID_RETENTION_DAYS`
  - `PUSH_TOMBSTONE_PURGE_DAYS`
  - `HEALTH_PUSH_*`（push SLI target 與 sample 門檻）
- 觀測資料源：
  - API runtime counters：`app/services/push_sli_runtime.py`
  - DB state：`push_subscriptions`
  - health payload：`GET /health`、`GET /health/slo`

## Push SLI 定義

- `push_delivery_rate`：
  - 計算：`dispatch_success_total / dispatch_attempts_total`
  - sample 下限：`HEALTH_PUSH_SLI_MIN_DISPATCH_ATTEMPTS`
  - target：`HEALTH_PUSH_DELIVERY_RATE_TARGET`
- `push_dispatch_latency_p95_ms`：
  - 來源：runtime dispatch latency samples
  - sample 下限：`HEALTH_PUSH_SLI_MIN_DISPATCH_ATTEMPTS`
  - target：`HEALTH_PUSH_DISPATCH_P95_MS_TARGET`
- `push_dry_run_latency_p95_ms`：
  - 來源：`POST /api/users/push-subscriptions/dry-run` latency
  - sample 下限：`HEALTH_PUSH_SLI_MIN_DRY_RUN_SAMPLES`
  - target：`HEALTH_PUSH_DRY_RUN_P95_MS_TARGET`
- `push_cleanup_stale_backlog_count`：
  - 計算：`stale_invalid_subscriptions + stale_tombstoned_subscriptions`
  - target：`HEALTH_PUSH_STALE_CLEANUP_BACKLOG_MAX`
  - stale 判斷依 retention：
    - invalid stale：`updated_at < now - PUSH_INVALID_RETENTION_DAYS`
    - tombstoned stale：`updated_at < now - PUSH_TOMBSTONE_PURGE_DAYS`

## Health / Gate 整合

- `GET /health`:
  - `sli.push`
  - `sli.evaluation.push`
  - `sli.targets.push_*`
- `GET /health/slo`:
  - 同步輸出 `push` SLI + evaluation + targets
- `scripts/check_slo_burn_rate_gate.py`:
  - `push.status == degraded` -> gate fail（`push_sli_degraded`）
  - `push.status == insufficient_data`：
    - 預設允許
    - `SLO_GATE_REQUIRE_SUFFICIENT_DATA=true` 時 fail（`push_sli_insufficient_data`）

## DoD
- 同一 endpoint 不可被不同使用者重複註冊（防 hijack）。
- 每個使用者 subscription 數量受上限保護（abuse budget）。
- dry-run 可以抽樣 subscription 並更新 `dry_run_sampled_at`，不做實際發送。
- cleanup script 在 dry-run 與 execute 兩種模式都可重複執行（idempotent）。

## Failure Taxonomy
- `provider_unavailable`
- `invalid_subscription`
- `permission_denied`
- `payload_rejected`
- `rate_limited`
- `unknown_error`

## Standards References

- VAPID: RFC 8292
- Web Push protocol: RFC 8030
- Message Encryption for Web Push: RFC 8291

## Debug Checklist
1. 無法註冊 subscription：
   - 檢查 `PUSH_NOTIFICATIONS_ENABLED`、HTTPS、瀏覽器 Push API 支援。
   - 檢查是否超過 `PUSH_MAX_SUBSCRIPTIONS_PER_USER`。
2. 刪除後仍收到推播：
   - 確認狀態是否變為 `TOMBSTONED`。
   - 執行 cleanup script 確認是否已進入 `PURGED`。
3. cleanup 沒有動作：
   - 檢查 `updated_at` 是否已超過 retention/purge 門檻。
   - 確認是否忘記加 `--execute`。
