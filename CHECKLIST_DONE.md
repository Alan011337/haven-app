# P0/P1 Checklist — DONE (Evidence)

Generated: 2026-02-23. Source of truth: `docs/plan/P0_P1_AUDIT.md`. This file summarizes **DONE** items with evidence pointers. **All P0/P1 audit items are DONE with evidence.** This file summarizes evidence pointers and verification commands; CHECKLIST_DONE is “all complete” until every audit item is DONE with evidence.

## How to verify

- **Backend tests**: `cd backend && PYTHONPATH=. ./venv/bin/python -m pytest` (or `pytest` if venv active)
- **Security gate**: `cd backend && bash scripts/security-gate.sh`
- **Frontend**: `cd frontend && npm run build && npm run lint && npm run typecheck`

**How to test (quick smoke)**: `cd backend && PYTHONPATH=. ./venv/bin/python -m pytest tests/test_health_endpoint.py tests/test_admin_authorization_matrix.py -q` → expect 15 passed. `./venv/bin/python scripts/check_safety_ui_policy_contract.py` → expect exit 0.

Verified 2026-02-23: safety UI contract ok; health + admin authz tests 15 passed; full security gate + pytest in CI. See `docs/plan/AUDIT_REPORT.md` and `docs/plan/P0_P1_AUDIT.md` (Phase 1 Evidence spot-check).

## P0 DONE — Evidence

| Item | Evidence (file / test) |
|------|------------------------|
| **Launch gate** | `docs/P0-LAUNCH-GATE.md`, `.github/workflows/release-gate.yml`, `scripts/release-gate-local.sh`, `backend/scripts/security-gate.sh` |
| **OWASP API Top 10** | `docs/security/owasp-api-top10-mapping.md`, `backend/scripts/check_owasp_api_top10_mapping_contract.py`, `backend/tests/test_owasp_api_top10_mapping_contract_policy.py` |
| **Endpoint / BOLA matrix** | `docs/security/endpoint-authorization-matrix.json`, `backend/tests/security/test_bola_matrix.py`, `backend/tests/security/test_bola_subject_matrix.py` |
| **Rate limiting** | `backend/app/services/rate_limit.py`, `backend/tests/test_pairing_rate_limit_api.py`, `backend/tests/test_card_mode_isolation.py` |
| **WebSocket abuse** | `backend/app/services/ws_abuse_guard.py`, `backend/tests/test_ws_abuse_guard.py`, `backend/tests/test_websocket_auth_guard.py` |
| **Prompt abuse** | `backend/app/services/prompt_abuse.py`, `backend/tests/test_prompt_abuse_policy.py` |
| **Secrets / key management** | `docs/security/secrets-key-management-policy.json`, `backend/tests/test_secrets_key_management_contract_policy.py`, `scripts/key-rotation-drill.sh` |
| **Encryption posture** | `backend/app/core/field_encryption.py`, `backend/app/models/journal.py` (encrypted fields), `backend/tests/test_field_level_encryption.py` |
| **Data rights (export/erase)** | `backend/app/api/routers/users.py` (GET /me/data-export, DELETE /me/data), `backend/tests/test_data_rights_api.py`, `backend/tests/test_data_restore_drill_audit.py` |
| **Consent receipts** | `backend/app/api/routers/users.py` (consent endpoints), `backend/tests/test_user_consent_receipt_api.py`, migration `b2c3d4e5f6a7_add_consent_receipts_and_user_age_fields.py` |
| **Billing core** | `backend/app/api/routers/billing.py` (idempotency, signature), `backend/tests/test_billing_webhook_security.py`, `backend/tests/test_billing_idempotency_api.py` |
| **AI safety / red-team** | `backend/tests/test_ai_safety_redteam.py`, `backend/tests/test_safety_regression.py`, `POLICY_AI.md`, `docs/safety/safety-ui-policy-v1.md` |
| **Health (UptimeRobot-ready)** | `backend/app/main.py` — `@app.get("/health")` returns JSON `status`/`checks`/`sli`; 503 when degraded |
| **8 decks (content model)** | `backend/app/models/card.py` — `CardCategory` enum: DAILY_VIBE, SOUL_DIVE, SAFE_ZONE, MEMORY_LANE, GROWTH_QUEST, AFTER_DARK, CO_PILOT, LOVE_BLUEPRINT |
| **Email notification wiring** | `backend/app/services/notification.py` — `queue_partner_notification` → `send_partner_notification_with_retry`; called from `journals.py`, `cards.py`, `card_decks.py` |
| **Structured logging / observability** | `backend/app/middleware/request_context.py`, `backend/app/core/structured_logger.py` (or `logging_setup.py`), `backend/app/services/http_observability.py`, `backend/tests/test_request_context_middleware.py`, `backend/tests/test_health_endpoint.py` |
| **PII redaction** | `backend/app/core/log_redaction.py`, `backend/tests/test_log_redaction.py`, `backend/tests/test_trace_span_redaction.py` |

## P1 DONE (subset)

- **Entitlement evaluation API (MON-02)**: `backend/app/api/routers/billing.py` (`GET /api/billing/entitlements/me`), `backend/app/services/entitlement_runtime.py`, `backend/tests/test_entitlement_enforcement_api.py`
- **AI eval golden-set gate (EVAL-01)**: `backend/scripts/run_ai_eval_golden_set_snapshot.py`, `backend/scripts/security-gate.sh`, `.github/workflows/release-gate.yml`, `backend/tests/test_ai_eval_golden_set_contract_policy.py`
- **Visual skeleton standardization (VIS-SKELETON-01 baseline)**: `frontend/src/components/ui/Skeleton.tsx`, `frontend/src/app/decks/page.tsx`, `frontend/src/features/deck-room/DeckRoomView.tsx`
- **Billing state machine / reconciliation**: `backend/app/api/routers/billing.py`, `backend/scripts/run_billing_reconciliation_audit.py`, `.github/workflows/billing-reconciliation.yml`
- **Push lifecycle / VAPID / SLI**: `docs/push/vapid.md`, `backend/app/services/push_sli_runtime.py`, `backend/tests/test_push_sli_runtime.py`
- **Growth (NSM, activation, referral, re-engagement, onboarding, sync nudge, first delight)**: `backend/app/services/growth_*.py`, `backend/tests/test_growth_*.py`, `backend/tests/test_referral_funnel_api.py`, etc.
- **Gamification streak**: `backend/app/services/gamification*.py`, gamification summary API + tests
- **Admin panel (authz)** : `backend/app/api/routers/admin.py`, `backend/tests/test_admin_authorization_matrix.py`
- **AI router / persona**: `backend/app/services/ai_router.py`, `backend/app/services/ai_persona.py`, `backend/tests/test_ai_router*.py`, `backend/tests/test_ai_persona*.py`
- **Backup / restore drill**: `docs/ops/backup-policy.json`, `.github/workflows/backup-restore-drill.yml`, `docs/security/evidence/backup-restore-drill-*.json`
- **Chaos drill**: `docs/ops/incident-response-playbook.md`, `docs/ops/chaos-drill-spec.md`, `.github/workflows/chaos-drill.yml`
- **Solo mode lifecycle (LIFECYCLE-01)**: `backend/app/services/lifecycle_solo_mode.py`, AI solo prompt injection, `backend/tests/test_lifecycle_solo_mode.py`, `backend/tests/test_journal_notification_rules.py` (solo notification behavior tests)
- **Unit economics monitor (FIN-01)**: `backend/scripts/run_unit_economics_report.py` (`--fail-on-warning`), `.github/workflows/unit-economics-report.yml` (GitHub issue alert on health=warning), `backend/tests/test_unit_economics_report.py`
- **Degradation UX (DEG-01/DEG-02)**: `GET /health/degradation`, `frontend/src/lib/degradation.ts`, `frontend/src/components/system/DegradationBanner.tsx`, layout banner
- **GAME-TITLES**: level/title in gamification API + UI (Lv.X · level_title)
- **SRE-TIER-01**: `docs/sre/service-tier-policy.json`, `backend/scripts/check_sre_tier_policy_contract.py`, security-gate
- **CUJ-01**: POST /api/users/events/cuj + `backend/tests/test_cuj_ingest_schema_contract.py`
- **BILL-04/BILL-09**: refund/chargeback tests in test_billing_webhook_security.py + `backend/tests/test_billing_correctness_suite.py`
- **BILL-03**: entitlement gating + `test_journal_create_403_when_quota_exceeded_free_plan`
- **BILL-08**: store compliance doc + `check_store_compliance_doc_contract.py` in security-gate
- **P1-C-MULTI-CHANNEL**: partner_bound trigger on pair success (notification.py, notification_multichannel.py, users.py)
- **MON-01**: quota ledger + server-side checks for journal/card (DAILY_RITUAL + library draw)
- **UX-SPEED-01**: applyOptimisticPatch in JournalInput (optimistic clear, rollback on failure)
- **SLO-01**: ritual_success_rate in GET /health/slo cuj.metrics; `test_health_slo_cuj_metrics_include_ritual_success_rate_slo01`, `test_health_slo_endpoint_returns_targets` (cuj.metrics.ritual_success_rate when status=ok)
- **SLO-02–05**: journal_write_p95/analysis_async_lag_p95, ws SLI, partner_binding_success_rate, ai_feedback_downvote_rate in cuj_sli_runtime + GET /health/slo; emission checklist in `docs/sre/slo.md`
- **REL-GATE-02**: `run_canary_guard.py` (1%->100%, rollback hook), `test_canary_guard.py` (test_main_accepts_dry_run_hooks_and_allow_missing_health_url_rel_gate_02, test_run_canary_guard_triggers_rollback_hook_on_failure)
- **CUJ-02**: request_id end-to-end (JournalInput + trackJournalSubmit + createJournal X-Request-Id; journals.py journal_request_id = request_id_var.get() or uuid)
- **MON-03**: Stub routes `POST /api/billing/webhooks/appstore`, `/googleplay` return 501; `test_mon03_store_webhook_stubs.py`; `docs/security/store-provider-adapters.md`
- **P1-C-WEB-PUSH**: implementation + E2E checklist in `docs/push/vapid.md` + `backend/scripts/check_push_vapid_readiness.py`

Full DONE list and evidence: see `docs/plan/P0_P1_AUDIT.md` (Audit Matrix, status: DONE).
