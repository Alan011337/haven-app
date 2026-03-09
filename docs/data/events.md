# Event Taxonomy & Governance (P1)

## Why
- 統一 Growth/Activation 事件語彙，避免跨端事件名漂移。
- 降低分析資料中的 PII 外洩風險，讓儀表板可長期維運。

## How
- 命名規則：`domain.object.action.v1`
- 必填欄位：
  - `event_name`
  - `occurred_at` (UTC ISO-8601)
  - `user_id`（若為匿名流量可為 `null`，但需有 `anonymous_id`）
  - `dedupe_key`
- 去重規則：
  - 同 `(user_id, event_name, dedupe_key)` 視為同一事件。
- PII policy：
  - 禁止直接上報 email、token、IP、原始裝置識別資訊。
  - 若需關聯，使用 hash/tokenized surrogate key。

## Canonical Growth Events
- `growth.referral.view.v1`
- `growth.referral.signup.v1`
- `growth.referral.couple_invite.v1`
- `growth.referral.bind.v1`
- `growth.activation.signup_completed.v1`
- `growth.activation.partner_bound.v1`
- `growth.activation.first_journal_created.v1`
- `growth.activation.first_deck_response.v1`
- `growth.pricing.experiment.assigned.v1`
- `growth.pricing.experiment.checkout_started.v1`
- `growth.pricing.experiment.checkout_completed.v1`
- `growth.pricing.experiment.guardrail_triggered.v1`
- `growth.reengagement.share_card_prompted.v1`
- `growth.reengagement.time_capsule_prompted.v1`
- `growth.sync_nudge.partner_journal_reply_prompted.v1`
- `growth.sync_nudge.ritual_resync_prompted.v1`
- `growth.sync_nudge.streak_recovery_prompted.v1`
- `growth.sync_nudge.delivered.v1`
- `growth.first_delight.delivered.v1`

## Canonical CUJ Events
- `cuj.ritual.load.v1`
- `cuj.ritual.draw.v1`
- `cuj.ritual.respond.v1`
- `cuj.ritual.unlock.v1`
- `cuj.journal.submit.v1`
- `cuj.journal.persist.v1`
- `cuj.journal.analysis_queued.v1`
- `cuj.journal.analysis_delivered.v1`
- `cuj.bind.start.v1`
- `cuj.bind.success.v1`

## Ingestion Contracts (Referral)
- `POST /api/users/referrals/landing-view` -> `growth.referral.view.v1`
- `POST /api/users/referrals/signup` -> `growth.referral.signup.v1`
- `POST /api/users/referrals/couple-invite` -> `growth.referral.couple_invite.v1`
- `POST /api/users/pair`（成功配對時）-> `growth.referral.bind.v1`
- `GET /api/users/sync-nudges` -> `growth.sync_nudge.*_prompted.v1`（runtime eligibility）
- `POST /api/users/sync-nudges/{nudge_type}/deliver` -> `growth.sync_nudge.delivered.v1`
- `GET /api/users/first-delight` -> `growth.first_delight.deliverable.v1`（runtime eligibility）
- `POST /api/users/first-delight/ack` -> `growth.first_delight.delivered.v1`

## Ingestion Contracts (CUJ)
- `POST /api/users/events/cuj`
  - payload uses enum-based `event_name` + `event_id`
  - server dedupe: `(user_id, event_name, event_id)` via `dedupe_key`
  - kill-switch aware: `disable_growth_events_ingest=true` returns accepted=false

## Ingestion Contracts (Core Loop v1)
- `POST /api/users/events/core-loop`
  - payload uses snake_case `event_name` + `event_id`
  - PRD v0 minimum event set:
    - `daily_sync_submitted`
    - `daily_card_revealed`
    - `card_answer_submitted`
    - `appreciation_sent`
    - `daily_loop_completed`
  - server dedupe: `(user_id, event_name, event_id)` via `dedupe_key`
  - payload governance:
    - key whitelist only (`props/context/privacy` each has allow-list)
    - blocked key fragments (`email/token/password/content/...`) are dropped
    - oversized JSON payload is dropped safely (non-blocking ingest)
    - server auto-injects `context.event_schema_version=v1`
  - response includes `loop_completed_today` (true when today's four required steps are complete)
  - kill-switch aware: `disable_growth_events_ingest=true` returns accepted=false

### Core Loop payload example
```json
{
  "event_name": "daily_loop_completed",
  "event_id": "loop:2026-03-01",
  "source": "web",
  "session_id": "daily-sync-2026-03-01",
  "props": {
    "loop_version": "v1",
    "time_spent_sec": 320,
    "answered_by": "both"
  },
  "context": {
    "app_version": "web",
    "env": "prod"
  },
  "privacy": {
    "pii_redacted": true
  }
}
```

## DoD
- 事件名稱需符合命名規則並版本化。
- 任何新事件都需說明 owner、用途、保留期與 redaction 規則。
- 事件 ingestion 若缺少 `dedupe_key` 應拒絕或轉降級（不可默默吞錯）。

## Debug Checklist
1. Dashboard 數字異常放大：
   - 先查 dedupe key 是否缺失/不穩定。
2. 新版客戶端資料消失：
   - 檢查 event version 是否 mismatch（例如 `v2` 尚未入倉）。
3. 隱私稽核警示：
   - 檢查 payload 是否含 email/token/IP 原文。
4. 事件 ingestion 成功但資料欄位缺失：
   - 檢查 `/health` `sli.events_runtime.drop_rate_overall`
   - 檢查 `events_sanitize_*` counters（allow-list 過濾或 payload 過大）

## Lifecycle Governance (Rollup -> Retention)
- 週期治理順序固定為 `rollup_then_retention`，避免直接 purge 破壞聚合資料連續性。
- 標準入口：
  - `backend/scripts/run_events_log_lifecycle.py`（dry-run / apply 皆可）
  - `/.github/workflows/events-log-retention-drill.yml`（weekly + monthly drill）
- apply 需雙重保護：
  - `--confirm-apply events-log-lifecycle-apply`
  - `--max-apply-rollup-selected` 與 `--max-apply-retention-matched` safety caps
