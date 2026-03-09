# Haven Observability Minimum (P0-H)

## Scope
- Structured logging context fields: `request_id`, `user_id`, `partner_id`, `session_id`, `mode`, `route`, `status_code`, `latency_ms`
- Runtime SLI snapshots from `/health` and `/health/slo`
- Minimal trace chain logging for API -> DB -> AI provider -> parse -> commit
- PII-safe logging defaults for trace fields

## Structured Logging Contract
- Middleware bootstrap:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/middleware/request_context.py`
  - `x-request-id` normalized and echoed on response
  - `session_id` and `mode` inferred from headers/query/path for CUJ requests
- Context injection:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/core/structured_logger.py`
  - Filter injects `request_id/user_id/partner_id/session_id/mode/route/status_code/latency_ms` on every log record
  - Deterministic log sampling helper available for high-volume streams (`should_sample_event`)
- Logger wiring:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/core/logging_setup.py`
 - Cardinality control:
   - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/middleware/request_context.py`
   - Dynamic path segments normalize to `:uuid/:id/:token` by default (`LOG_ROUTE_NORMALIZE_DYNAMIC_SEGMENTS=true`)

## Runtime Metrics (Health Endpoints)
- Source:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/main.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/http_observability.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/ws_runtime_metrics.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/rate_limit_runtime_metrics.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/notification.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/notification_runtime_metrics.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/dynamic_content_runtime_metrics.py`
- Available at:
  - `GET /health`
  - `GET /health/deep` (explicit deep probe alias of `/health/slo`)
  - `GET /health/slo`
  - `GET /metrics` (OpenMetrics text payload)
  - `GET /metrics` auth policy:
    - if `METRICS_REQUIRE_AUTH=false` and `METRICS_AUTH_TOKEN` unset: public
    - otherwise requires either `X-Metrics-Token: <token>` or `Authorization: Bearer <token>`
- Key payloads:
  - `sli.http_runtime.latency_ms.p50/p95/p99`
  - `sli.http_runtime.error_rate`
  - `sli.write_rate_limit.*`
  - `sli.write_rate_limit.attempt_total`
  - `sli.write_rate_limit.blocked_total`
  - `sli.write_rate_limit.block_rate_overall`
  - `sli.write_rate_limit.block_rate_by_scope.*`
  - `sli.notification_runtime.counters.*`
  - `sli.dynamic_content_runtime.counters.*`
  - `sli.events_runtime.counters.*`
  - `sli.events_runtime.drop_rate_overall`
  - `sli.events_runtime.rate_limited_rate_overall`
  - `sli.events_runtime.ingest_guard.configured_backend`
  - `sli.events_runtime.ingest_guard.active_backend`
  - `sli.events_runtime.ingest_guard.redis_degraded_mode`
  - `sli.dynamic_content_runtime.state.cooldown_active`
  - `sli.dynamic_content_runtime.state.cooldown_remaining_seconds`
  - `sli.dynamic_content_runtime.state.cooldown_store_degraded`
  - `sli.dynamic_content_runtime.state.cooldown_store_retry_remaining_seconds`
  - `sli.timeline_runtime.counters.timeline_query_total`
  - `sli.timeline_runtime.counters.timeline_budget_clamped_total`
  - `sli.timeline_runtime.counters.timeline_page_served_total`
  - `sli.timeline_runtime.counters.timeline_page_item_total`
  - `sli.timeline_runtime.counters.timeline_page_has_more_total`
  - `sli.ws.*`
  - `sli.ws.partner_event_delivery_latency_p95_ms`
  - `sli.ws.partner_event_publish_success_rate`
  - `sli.ws.partner_event_delivery_ack_rate`
  - `sli.abuse_economics.evaluation.status` (`ok|warn|block|insufficient_data`)
  - `sli.abuse_economics.vectors[*].projected_daily_events`
  - `sli.abuse_economics.vectors[*].estimated_daily_cost_usd`
  - `checks.notification_queue_depth`
  - `checks.notification_outbox_depth`
  - `checks.notification_outbox_oldest_pending_age_seconds`
  - `checks.notification_outbox_retry_age_p95_seconds`
  - `checks.notification_outbox_dead_letter_rate`
  - `checks.notification_outbox_dispatch_lock_heartbeat_age_seconds`
  - `notification_outbox_replayed_total`
  - `notification_outbox_auto_replay_triggered_total`
  - `notification_outbox_auto_replay_error_total`
  - `haven_notification_outbox_depth`
  - `haven_notification_outbox_oldest_pending_age_seconds`
  - `haven_notification_outbox_retry_age_p95_seconds`
  - `haven_notification_outbox_dead_letter_rate`
  - `haven_notification_runtime_*`
  - `haven_dynamic_content_runtime_*`
  - `haven_events_runtime_*`
  - `haven_ws_runtime_*`
  - `haven_http_runtime_*`
  - `haven_ai_router_runtime_*`
  - `haven_timeline_runtime_*`
  - `sli.ai_router_runtime.state.shared_state_backend`
  - `sli.ai_router_runtime.state.redis_degraded_mode`
- Runtime metric cardinality guards:
    - `notification_runtime_metric_cardinality_overflow_total`
    - `dynamic_content_runtime_metric_cardinality_overflow_total`
  - Hard deny list for labels:
    - any unbounded identifier (`user_id`, `request_id`, `email`, `raw_model`, journal content fragments)
    - denied values must map to fixed `unknown` bucket and stay out of metrics labels

## Sampling Policy (Default)
- Keep `LOG_SAMPLE_RATE_DEFAULT=1.0` for baseline completeness.
- Use targeted sampling on high-frequency failure streams:
  - `LOG_SAMPLE_RATE_WS_SEND_FAILURE` controls WebSocket send/publish warning logs.
- Sampling is deterministic by event key to preserve reproducibility across replicas.

## AI Router Runtime Notes
- `redis_degraded_mode=true` means router switched to conservative mode:
  - result cache disabled
  - inflight poll disabled
  - cooldown enforcement disabled
  - max attempts forced to 1
- Router labels are enum-bucketed only (`provider/profile/reason`), and unknowns are pinned to fixed constant `unknown` (no dynamic hash labels).

## Trace Baseline
- Source:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/trace_span.py`
- Contract:
  - Every trace start/end log includes `request_id`
  - Trace fields auto-enrich with context: `context_user_id/context_partner_id/context_session_id/context_mode`
  - Sensitive keys are redacted by default (`token/secret/password/api_key/content/email/ip`)
  - Optional OpenTelemetry export can be enabled with `OTEL_TRACING_ENABLED=true`; if OTel SDK is absent, tracing falls back to log-only mode.

## PII Redaction Guardrails
- Core helpers:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/core/log_redaction.py`
- Trace redaction enforcement:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/trace_span.py`
- Regression tests:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_log_redaction.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_trace_span_redaction.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_logging_setup.py`

## Quick Checks
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_request_context_middleware.py \
  tests/test_logging_setup.py \
  tests/test_trace_span_redaction.py \
  tests/test_trace_span_otel.py \
  tests/test_health_endpoint.py
```

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/export_memory_timeline_query_baseline.py \
  --output /tmp/memory-timeline-query-baseline.json \
  --fail-on-missing-index \
  --fail-on-date-function \
  --fail-on-full-scan
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/export_endpoint_authorization_matrix.py \
  --check-current
```

## Local Gate Speed Profiles
- `backend/scripts/security-gate.sh` supports:
  - `SECURITY_GATE_PROFILE=fast` for fast local policy + core authz checks
  - `SECURITY_GATE_PROFILE=full` for full release-grade checks (default)
  - local release gate defaults:
  - `RELEASE_GATE_SECURITY_PROFILE=full`
  - `API_INVENTORY_AUTO_WRITE=1` (auto-sync `docs/security/api-inventory.json` before full checks)
  - `RELEASE_GATE_AUTO_REFRESH_EVIDENCE=0` (local default): avoids long-running evidence refresh in normal dev loops
  - set `RELEASE_GATE_AUTO_REFRESH_EVIDENCE=1` only when you explicitly want CUJ/billing/audit evidence regeneration
  - `RELEASE_GATE_ALLOW_MISSING_SLO_URL=0` (fail-closed default; set `=1` only for local emergency override)
  - evidence cleanup knobs (local):
    - `EVIDENCE_NOISE_PRUNE_TIMESTAMPED=1` (default): prune untracked timestamped evidence noise
    - `EVIDENCE_NOISE_KEEP_UNTRACKED_TIMESTAMPED_COUNT=2` (default): keep newest two untracked timestamped evidence files per extension
  - if `SLO_GATE_HEALTH_SLO_URL` and `SLO_GATE_HEALTH_SLO_FILE` are both absent locally, `release-gate-local` auto-generates `/tmp/cuj-slo-payload-local.json` and still keeps fail-closed semantics
  - timeline runtime gate:
    - summary path: `/tmp/timeline-runtime-alert-summary-local.json`
    - warn clamp ratio threshold: `TIMELINE_RUNTIME_CLAMP_WARN_RATIO` (default `0.15`)
    - critical clamp ratio threshold: `TIMELINE_RUNTIME_CLAMP_CRITICAL_RATIO` (default `0.30`)
    - minimum query sample: `TIMELINE_RUNTIME_MIN_QUERY_TOTAL` (default `20`)
  - outbox snapshot summary:
    - snapshot path: `/tmp/notification-outbox-health-snapshot-local.json`
    - summary path: `/tmp/notification-outbox-health-summary-local.json`
    - override source: `RELEASE_GATE_OUTBOX_HEALTH_FILE` or `RELEASE_GATE_OUTBOX_HEALTH_URL`
  - optional preflight: `RELEASE_GATE_BACKEND_TEST_PROFILE=fast|safety|full`

## Local Test Profiles
- `backend/scripts/run-test-profile.sh`:
  - `smoke`: critical lint + health/ai-router/outbox/security contract smoke
  - `fast`: lint + health/outbox + billing/store contracts
  - `runtime`: lint + health/structured-logging/ai-router/timeline/outbox snapshot contracts
  - `safety`: BOLA/authz + billing security tests
  - `full`: full backend lint + full backend pytest

## Alerting Starter (Minimal)
- Trigger degraded service alert when `/health` returns `503` for 2 consecutive probes.
- Trigger SLI alert when:
  - `sli.http_runtime.error_rate > 0.01` over 15m
  - `sli.ws_burn_rate` evaluation status is `degraded`
  - `sli.abuse_economics.evaluation.status` is `block`
  - `sli.notification_runtime.counters.notification_failure_*` shows sustained growth
  - `sli.dynamic_content_runtime.counters.dynamic_content_weekly_run_fallback_total` increases abnormally
  - `sli.timeline_runtime.counters.timeline_budget_clamped_total / max(1, timeline_query_total)` exceeds:
    - warn: `0.15`
    - critical: `0.30`
    - evaluate only when `timeline_query_total >= 20`
  - `sli.dynamic_content_runtime.counters.dynamic_content_cooldown_store_read_error_total` increases
  - `sli.dynamic_content_runtime.state.cooldown_store_degraded=true` for extended time
  - `sli.dynamic_content_runtime.state.degraded_mode_active=true` 且 `degraded_mode_remaining_seconds` 長期不下降
  - `*_runtime_metric_cardinality_overflow_total` keeps increasing (indicates unbounded metric keys)
  - `checks.notification_queue_depth` exceeds team-defined threshold
  - `checks.notification_outbox_depth` keeps growing while `notification_outbox_sent_total` stalls
  - `checks.notification_outbox_retry_age_p95_seconds >= 2400`
  - `checks.notification_outbox_dispatch_lock_heartbeat_age_seconds >= 180`
  - `sli.write_rate_limit.block_rate_overall` 快速上升（區分惡意流量與誤傷）

## Runtime Alert Runbook
- Detailed alert thresholds + triage sequence:
  - `/Users/alanzeng/Desktop/Projects/Haven/docs/sre/runtime-alerts.md`

## Evidence Refresh Automation
- Daily workflow:
  - `/.github/workflows/security-evidence-refresh.yml`
  - refreshes CUJ synthetic + billing reconciliation + audit-log retention evidence
- Local one-shot refresh:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
bash scripts/refresh-security-evidence-local.sh
```

- Timeline runtime gate (from local health/slo payload):
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/check_timeline_runtime_alert_gate.py \
  --health-slo-file /tmp/cuj-slo-payload-local.json \
  --summary-path /tmp/timeline-runtime-alert-summary-local.json
```

- Notification outbox health snapshot:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_notification_outbox_health_snapshot.py \
  --health-file /tmp/local-health.json \
  --output /tmp/notification-outbox-health-snapshot-local.json
```

## Evidence Artifact Policy (Release Hygiene)
- `docs/security/evidence/*-latest.json` 屬於 snapshot pointer 類產物，主要供 pipeline/local gate 最新狀態覆蓋。
- 可發布提交應以固定時間戳證據（drill/audit/report）為主；`*-latest.json` 非必要時不納入人工提交。
- 本地跑 gate 後若僅有 latest pointer 變更，可於提交前清理：
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
bash scripts/clean-evidence-noise.sh
```
- `backend/scripts/security-gate.sh` 已將 golden set latest pointer 輸出到 `/tmp`，避免污染 repo 追蹤檔。
