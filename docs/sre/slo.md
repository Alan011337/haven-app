# Haven SLO/SLI Specification (P1-A)

## Scope
This document defines production SLOs, SLIs, and measurement contracts for Haven core CUJs.

## SLO-01 Daily Ritual Draw/Unlock Success
- Objective: `>= 99.9%` success in rolling 30d.
- Success definition (all must be true):
  1. Frontend receives draw payload with valid `card_id`.
  2. Backend persists `card_sessions.id` and response side-effects (creator/partner state consistent).
  3. Partner reconciliation path (`respond -> unlock`) reaches consistent session state.
- Exclusions:
  - synthetic test users (`source=synthetic`).
  - internal canary accounts (`user_tag=internal`).
  - declared maintenance windows (`maintenance=true`).
- Data sources:
  - backend audit/metrics (`CARD_DECK_RESPOND`, `CARD_REVEALED`).
  - frontend CUJ events (`ritual_draw_rendered`, `ritual_unlock_rendered`).
  - **CUJ ingest**: `POST /api/users/events/cuj` receives RITUAL_DRAW, RITUAL_RESPOND, RITUAL_UNLOCK; `cuj_sli_runtime.build_cuj_sli_snapshot` computes `ritual_success_rate` numerator/denominator from these events (see `backend/app/services/cuj_sli_runtime.py`).
- Query contract:
  - PromQL (example):
    - numerator: `sum(rate(haven_ritual_success_total[5m]))`
    - denominator: `sum(rate(haven_ritual_attempt_total[5m]))`
  - SQL fallback:
    - `ritual_success_rate = successful_ritual_sessions / all_ritual_attempts`.
  - Runtime: `GET /health/slo` exposes `sli.cuj.metrics.ritual_success_rate` from CUJ event aggregation.

## SLO-02 Journal Submit + AI Analysis P95
- Objective: `journal_submit_to_analysis_complete_p95 < 4s`.
- Split SLIs (both tracked):
  - `journal_write_p95` (submit -> DB durable write).
  - `analysis_async_lag_p95` (DB write -> analysis materialized/delivered).
- Degradation strategy:
  - write journal first, enqueue analysis async.
  - frontend displays "分析稍後送達" status.
  - retry policy: exponential backoff, capped attempts, dead-letter evidence.
- Query contract:
  - PromQL example:
    - `histogram_quantile(0.95, sum(rate(haven_journal_write_ms_bucket[5m])) by (le))`
    - `histogram_quantile(0.95, sum(rate(haven_analysis_lag_ms_bucket[5m])) by (le))`
  - SQL fallback:
    - percentile on `(analysis_delivered_at - journal_created_at)`.

## SLO-03 WebSocket Sync Arrival
- Objective: `>= 99.5%` event arrival rate.
- Definition: partner-expected realtime event delivered within SLA window.
- Data sources: `ws_runtime_metrics`, notification fallback counters.
- Query contract:
  - `arrival_rate = ws_partner_event_delivered / ws_partner_event_expected`.

## SLO-04 Partner Binding Success
- Objective: `>= 99.9%` successful binding in rolling 30d.
- Definition: invite accepted, reciprocal pairing persisted, authz checks pass.
- Data source: `USER_PAIR` audit events + binding API outcomes.

## SLO-05 AI Hallucination Proxy Rate
- Objective: keep adverse feedback trend below threshold (product policy target).
- Definition: ratio of negative feedback events over analysis deliveries.
- Data source: feedback events (`analysis_feedback_downvote`), analysis delivery events.

## SLI Source Mapping
| SLI | Primary Source | Secondary Source | Owner |
| --- | --- | --- | --- |
| ritual_success_rate | backend metrics/audit | frontend CUJ events | Backend + FE |
| journal_write_p95 | backend latency histogram | request logs | Backend |
| analysis_async_lag_p95 | async lag metric | DB timestamps | Backend |
| ws_arrival_rate | ws runtime counters | inbox fallback counters | Backend |
| partner_binding_success_rate | pairing API metrics | audit events | Backend |
| ai_hallucination_proxy | feedback analytics | support tickets | Product/AI |

## Emission Checklist (where to emit)
- **SLO-02** `journal_write_p95` / `analysis_async_lag_p95`: Emit from `backend/app/api/journals.py` — on journal persist send CUJ `JOURNAL_PERSIST` with metadata `journal_write_ms`; on analysis delivered send `JOURNAL_ANALYSIS_DELIVERED` with metadata `analysis_async_lag_ms`. `cuj_sli_runtime.build_cuj_sli_snapshot` aggregates these; `GET /health/slo` exposes `journal_write_p95_ms`, `analysis_async_lag_p95_ms`.
- **SLO-03** `ws_arrival_rate`: Emit from `backend/app/services/ws_runtime_metrics.py` and `/health/slo` — numerator = partner events delivered, denominator = partner events expected; normalize by same time window. Inbox fallback counters as secondary source.
- **SLO-04** `partner_binding_success_rate`: Emit from pairing API — frontend/backend send CUJ `BIND_START` and `BIND_SUCCESS` to `POST /api/users/events/cuj`; `cuj_sli_runtime` computes `bind_success_total` and ratio; `GET /health/slo` exposes `partner_binding_success_rate`.
- **SLO-05** `ai_hallucination_proxy`: Ingest feedback via CUJ `AI_FEEDBACK_DOWNVOTE` to `POST /api/users/events/cuj`; ratio = downvote count / analysis delivery count (from JOURNAL_ANALYSIS_DELIVERED). Optional: dedicated `POST /api/users/events/feedback` or extend CUJ metadata; SLO computation can use same CUJ event store.

## Journal stage timeline (CUJ-02)
- To correlate queued vs delivered per request: send the same `request_id` (8–128 chars) on JOURNAL_SUBMIT, JOURNAL_PERSIST, JOURNAL_ANALYSIS_QUEUED, and JOURNAL_ANALYSIS_DELIVERED. `CujEventTrackRequest` accepts optional `request_id`; backend persists it on `CujEvent.request_id`. Frontend/backend can then compute per-request journal timeline (submit → persist → queued → delivered) from CUJ events.

## Runtime Health Snapshot Contract
- Endpoint: `GET /health/slo`.
- Expected payload additions:
  - `sli.cuj.counts` for ritual/journal/bind stage counters.
  - `sli.cuj.metrics` for `ritual_success_rate`, `partner_binding_success_rate`, `journal_write_p95_ms`, `analysis_async_lag_p95_ms`.
  - `sli.evaluation.cuj.status` in `ok | degraded | insufficient_data`.
  - `sli.targets.cuj` mirrors runtime thresholds used by health gates.
- Health gate behavior:
  - `/health` returns `503` with `degraded_reasons` containing `cuj_sli_below_target` when CUJ evaluation is degraded.
  - `insufficient_data` does not fail health status by itself.

## Compliance Notes
- All telemetry must redact PII/secrets before logs/traces.
- Metric labels must avoid raw user identifiers.
- New SLI changes require update to `docs/sre/alerts.md` and release checklist.
