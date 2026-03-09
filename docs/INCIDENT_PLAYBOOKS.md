# Haven Incident Playbooks (Runtime)

## Scope
- Canonical playbook: `/Users/alanzeng/Desktop/Projects/Haven/docs/ops/incident-response-playbook.md`
- This file adds runtime triage for:
  - notification multi-channel failures
  - dynamic content weekly pipeline fallback spikes
  - release evidence hygiene for local gate artifacts

## 1) Notification Dispatch Degraded

### Signals
- `GET /health` or `GET /health/slo`:
  - `sli.notification_runtime.counters.notification_failure_*` increasing
  - `checks.notification_queue_depth` growing
  - `checks.notification_outbox_depth` growing
  - `checks.notification_outbox_retry_age_p95_seconds` keeps rising (>= 2400s warning threshold)
  - `checks.notification_outbox_dispatch_lock_heartbeat_age_seconds` stale (>= 180s warning threshold)
  - `checks.notification_outbox_dispatch_lock_heartbeat_age_seconds` large/stuck
  - `sli.ws.partner_event_publish_success_rate` drops while `partner_event_delivery_ack_rate` remains low

### First checks
1. Verify provider readiness:
   - Email: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`
   - Outbox: `NOTIFICATION_OUTBOX_ENABLED=true` (if expected on this environment)
   - Push: `PUSH_NOTIFICATIONS_ENABLED`, VAPID keys
2. Inspect failure taxonomy counters:
   - `provider_unavailable`
   - `no_subscriptions`
   - `channel_disabled`
   - `transport_error`
   - `unexpected_error`
3. Confirm kill-switch / trigger matrix is not accidentally disabling channels.

### Immediate mitigation
1. Keep core CUJ running; do not block journal/card flow.
2. If a single channel is unhealthy, keep others active.
3. Prefer outbox drain + replay over service restart:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_notification_outbox_dispatch.py --limit 200
```
3.1 For sustained backlog, run loop mode with heartbeat:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_notification_outbox_dispatch.py \
  --loop \
  --interval-seconds 10 \
  --heartbeat-every 6
```
4. If dead-letter starts accumulating, replay a bounded batch first:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_notification_outbox_dispatch.py \
  --replay-dead \
  --replay-limit 100 \
  --reset-attempt-count
```
4.1 Probe/execute auto recovery policy (dead-row + dead-rate threshold):
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_notification_outbox_recovery.py --json
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_notification_outbox_recovery.py --apply --replay-limit 150
```
4.2 Capture replay audit artifact (dry-run/apply):
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_notification_outbox_dead_replay_audit.py --output /tmp/outbox-dead-replay-audit.json
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_notification_outbox_dead_replay_audit.py --apply --replay-limit 100 --output /tmp/outbox-dead-replay-audit-apply.json
```
4.3 Capture outbox-focused health snapshot artifact:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_notification_outbox_health_snapshot.py --health-url http://127.0.0.1:8000/health --output /tmp/outbox-health-snapshot.json
```
4.4 For local release verification, generate outbox summary artifact (non-blocking by default on non-protected branches):
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
RELEASE_GATE_OUTBOX_HEALTH_URL=http://127.0.0.1:8000/health \
SKIP_FRONTEND_TYPECHECK=1 SKIP_MOBILE_TYPECHECK=1 bash scripts/release-gate-local.sh
```
4.5 CI dry-run planner (hourly) is available at:
- `/.github/workflows/notification-outbox-self-heal.yml`
- Artifact names: `notification-outbox-self-heal` (`health snapshot` + `self-heal summary`)
5. Remove long-tail terminal rows to keep queue scans healthy:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_notification_outbox_cleanup.py
```
6. Run maintenance snapshot / repair in one command:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_notification_outbox_maintenance.py --dry-run
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_notification_outbox_maintenance.py --output /tmp/outbox-maintenance.json
```
7. Check dispatcher singleton lock heartbeat:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python - <<'PY'
from app.services.worker_lock import WorkerSingletonLock
print(WorkerSingletonLock.read_lock_state("notification-outbox-dispatch"))
PY
```
8. WS delivery diagnosis split:
```bash
curl -sS http://127.0.0.1:8000/health/slo | jq '.sli.ws | {publish:.partner_event_publish_success_rate, ack:.partner_event_delivery_ack_rate, p95:.partner_event_delivery_latency_p95_ms}'
```

### Threshold playbook (SLO-aligned)
1. If `notification_outbox_retry_age_p95_seconds` breaches threshold and `depth` is stable:
   - prioritize retry-drain run (`--replay-dead --replay-limit`) over full restart.
2. If `notification_outbox_dispatch_lock_heartbeat_age_seconds` breaches threshold:
   - inspect singleton lock state first; avoid concurrent dispatcher starts.
3. If both retry-age and lock-heartbeat are high:
   - treat as dispatcher-stall incident and run bounded recovery (`run_notification_outbox_recovery.py --apply`).

### Rollback
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/services/notification.py \
/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/notification_multichannel.py \
/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/notification_runtime_metrics.py \
/Users/alanzeng/Desktop/Projects/Haven/backend/app/core/health_routes.py
```

## 2) Dynamic Content Pipeline Fallback Spike

### Signals
- `sli.dynamic_content_runtime.counters.dynamic_content_weekly_run_fallback_total` increases
- `dynamic_content_generation_timeout_total` or `dynamic_content_parse_error_total` jumps
- `sli.dynamic_content_runtime.state.cooldown_active=true` for long periods

### First checks
1. Validate OpenAI connectivity and credentials.
2. Validate timeout/retry env values:
   - `DYNAMIC_CONTENT_AI_TIMEOUT_SECONDS`
   - `DYNAMIC_CONTENT_AI_MAX_RETRIES`
   - `DYNAMIC_CONTENT_AI_BACKOFF_BASE_SECONDS`
   - `DYNAMIC_CONTENT_AI_FAILURE_COOLDOWN_SECONDS`
   - `DYNAMIC_CONTENT_COOLDOWN_STORE_RETRY_SECONDS`
3. Check cooldown store health in `/health`:
   - `sli.dynamic_content_runtime.state.cooldown_store_degraded`
   - `sli.dynamic_content_runtime.state.cooldown_store_retry_remaining_seconds`
3. Run weekly script manually and inspect summary counters:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_dynamic_content_weekly.py
```

### Immediate mitigation
1. If provider unstable, allow fallback cards to continue serving.
2. Avoid repeated pressure during outage; keep cooldown enabled.
3. Track insert counts and ensure weekly deck still receives cards.
4. If store degraded persists, keep fallback path active and avoid rapid restarts; wait for retry window.

### Rollback
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/services/dynamic_content_pipeline.py \
/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/dynamic_content_runtime_metrics.py \
/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_dynamic_content_weekly.py \
/Users/alanzeng/Desktop/Projects/Haven/backend/app/core/health_routes.py
```

## 3) AI Router Degraded / Failover Storm

## 4) Release Evidence Hygiene (Local Gate Noise)

### Signals
- `/health` / `/health/slo`:
  - `sli.ai_router_runtime.state.redis_degraded_mode=true`
  - `sli.ai_router_runtime.counters.ai_router_provider_exhausted_total` spikes
  - `sli.ai_router_runtime.counters.ai_router_cache_fingerprint_mismatch_total` spikes
  - `sli.ai_router_runtime.counters.ai_router_schema_cooldown_activated_total` spikes

### First checks
1. Confirm router backend state:
   - `sli.ai_router_runtime.state.shared_state_backend`
   - `sli.ai_router_runtime.state.redis_degraded_mode`
2. Confirm failure reason distribution (enum buckets only):
   - `ai_router_failure_*_status_429_total`
   - `ai_router_failure_*_status_5xx_total`
   - `ai_router_failure_*_schema_validation_failed_total`
3. Confirm idempotency/cooldown policy knobs:
   - `AI_ROUTER_MAX_TOTAL_ATTEMPTS`
   - `AI_ROUTER_RATE_LIMIT_FAILOVER_THRESHOLD_SECONDS`
   - `AI_ROUTER_SCHEMA_FAIL_COOLDOWN_THRESHOLD`

### Immediate mitigation
1. Keep journal write path non-blocking (fallback response remains enabled).
2. If 429 dominates, reduce retry pressure:
   - `AI_ROUTER_MAX_TOTAL_ATTEMPTS=1`
   - `AI_ROUTER_RATE_LIMIT_FAILOVER_THRESHOLD_SECONDS=0`
3. If schema failures dominate, keep cooldown active and verify prompt/schema rollout consistency.
4. If Redis unstable, keep degraded mode conservative (no cache/no poll/no sleep) until Redis recovers.
5. Capture one incident snapshot artifact for ticket/debug handoff:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_oncall_runtime_snapshot.py --output /tmp/oncall-runtime-snapshot.json
```

### Rollback
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/services/ai_router.py \
/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/ai.py \
/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/ai_quality_monitor.py \
/Users/alanzeng/Desktop/Projects/Haven/docs/ai/router-policy-v1.md \
/Users/alanzeng/Desktop/Projects/Haven/docs/security/ai-router-policy.json
```

### Signals
- `git status` 只剩 `docs/security/evidence/*-latest.json` 變更，無實際程式邏輯變更。

### First checks
1. 確認必須提交的證據（drill/audit/report）是否已存在且未遺漏。
2. 確認 latest pointer 變更是否僅由本地 gate 觸發，沒有對應功能差異。

### Immediate mitigation
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
bash scripts/refresh-security-evidence-local.sh
bash scripts/clean-evidence-noise.sh
```

### Rollback
- 這是工作樹清理操作，無 runtime 影響，無 DB 回滾需求。

## 4.1) Frontend E2E Process Timeout

### Signals
- `release-gate-local.sh` / `release-gate.sh` e2e summary:
  - `classification=e2e_process_timeout`
- e2e log contains:
  - `[e2e-timeout] frontend e2e exceeded ...`

### First checks
1. Confirm timeout guardrails used during run:
   - `E2E_TIMEOUT_SECONDS`
   - `E2E_TIMEOUT_GRACE_SECONDS`
2. Confirm runtime Node major version:
   - `node -v`
   - release gates require Node 20/22 for `RUN_E2E=1` and fail fast on Node >22.
3. Identify the hanging step from `/tmp/frontend-e2e-local.log` (route wait, assertion, browser startup, or app server reachability).
4. Confirm base URL probe succeeded before e2e execution.

### Immediate mitigation
1. Keep release gate fail-closed for non-hotfix releases.
2. Reduce scope to targeted smoke first (single spec / grep) and reproduce deterministically.
3. Only increase timeout after root-cause note is recorded in release notes.

### Rollback
- Revert timeout wrapper integration if it causes false positives:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
git restore /Users/alanzeng/Desktop/Projects/Haven/scripts/release-gate-local.sh \
/Users/alanzeng/Desktop/Projects/Haven/scripts/release-gate.sh \
/Users/alanzeng/Desktop/Projects/Haven/frontend/scripts/run-e2e-with-timeout.mjs \
/Users/alanzeng/Desktop/Projects/Haven/frontend/scripts/summarize-e2e-result.mjs \
/Users/alanzeng/Desktop/Projects/Haven/frontend/scripts/check-e2e-summary-schema.mjs
```

## 5) Billing Webhook Async Backlog / Retry Degraded

### Signals
- `billing_webhook_receipts.status` 中 `FAILED` / `DEAD` 異常增加
- webhook replay 未收斂，或 entitlement 更新延遲
- `next_attempt_at` 已到期但未被消化

### First checks
1. 驗證 webhook secret 與 async mode 設定：
   - `BILLING_STRIPE_WEBHOOK_SECRET`
   - `BILLING_STRIPE_WEBHOOK_ASYNC_MODE`
2. 驗證重試策略設定：
   - `BILLING_WEBHOOK_RETRY_MAX_ATTEMPTS`
   - `BILLING_WEBHOOK_RETRY_BASE_SECONDS`
3. 快速抽查 receipt 欄位：
   - `attempt_count`
   - `next_attempt_at`
   - `last_error_reason`
4. 確認 retry worker 排程在執行（Render cron `haven-billing-webhook-retry`）。

### Immediate mitigation
1. 先手動消化到期重試批次：
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_billing_webhook_retry_dispatch.py --limit 200
```
2. 如果 provider 故障持續，調大 retry backoff，避免放大重送風暴。
3. 針對 `DEAD` receipt 做人工對帳與補償處理，避免 entitlement 漏同步。

### Rollback
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/billing.py \
/Users/alanzeng/Desktop/Projects/Haven/backend/app/models/billing.py \
/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_billing_webhook_retry_dispatch.py
```
如需 schema 回滾：
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. ./scripts/run-alembic.sh downgrade h1core0000012
```

## 6) Cron Runtime Contracts (Render)

Expected scheduled jobs in `render.yaml`:
1. `haven-billing-webhook-retry` every 5 minutes
2. `haven-notification-outbox-dispatch` every 2 minutes
3. `haven-notification-outbox-cleanup` daily at 04:00

If one job is paused or repeatedly failing:
1. run corresponding script manually from backend root
2. inspect script exit code and logs
3. only then decide restart/rollback

## 7) Events Log Lifecycle Drill (Weekly + Monthly)

### Signals
- growth/event ingestion volume grows but `events_log` 永久保留未清理
- monthly drill artifact missing (`events-log-retention-drill`)

### First checks
1. 確認 workflow `/.github/workflows/events-log-retention-drill.yml` 最近一次執行成功（weekly + monthly）。
2. 檢查 artifact `events-log-retention-drill` 是否有最新證據 JSON。
3. 本地 dry-run 驗證：
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_events_log_lifecycle.py \
  --rollup-retention-days 30 \
  --rollup-batch-size 5000 \
  --retention-days 120 \
  --retention-batch-size 2000
```

### Immediate mitigation
1. 先維持 dry-run，確認 `matched` 規模與 cutoff 是否符合預期。
2. 若需 apply purge，先以小批次執行並保留操作記錄：
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_events_log_lifecycle.py \
  --rollup-retention-days 30 \
  --rollup-batch-size 500 \
  --retention-days 120 \
  --retention-batch-size 500 \
  --apply \
  --confirm-apply events-log-lifecycle-apply \
  --max-apply-rollup-selected 100000 \
  --max-apply-retention-matched 50000
```
3. 觀察 `/health` 與事件寫入流程，確保核心 API 無回歸。

### Rollback
- `events_log` 清理屬資料刪除動作，無 schema rollback；請以備份/快照復原策略處理。
- 程式面可回滾：
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/services/events_log_retention.py \
/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_events_log_lifecycle.py \
/Users/alanzeng/Desktop/Projects/Haven/.github/workflows/events-log-retention-drill.yml
```
