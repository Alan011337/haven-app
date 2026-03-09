# Haven — 營運 Runbook（精簡版）

> 詳細步驟見 `docs/ops/`。本文件為 launch 最小集，對應 health、uptime、Email、DB/Redis/WS 診斷與回滾。

---

## 健康檢查與 Uptime

- **Endpoint**：`GET /health`、`GET /health/slo`
- **監控**：使用 UptimeRobot（或同類）監控 production `https://<DOMAIN>/health`；Keyword Monitor 可檢查回傳 JSON 含 `"status":"ok"` 或 `"degraded"` 判定。
- **設定細節**：`docs/ops/uptimerobot-setup.md`
- **異常時**：依 `docs/ops/incident-response-playbook.md` 依症狀（database_unhealthy、redis_unhealthy、ws_sli_degraded 等）排查。

---

## Email 通知（Backup / 離線喚回）

- **用途**：日記建立、卡片回答後通知伴侶；作為 push/WS 以外的備援。
- **供應商**：Resend；開關由 `RESEND_API_KEY` 控制，未設定時不送信（`/health` 回傳 `email.status: "warning"`）。
- **營運要點**：
  - 金鑰：`RESEND_API_KEY`、發信人 `RESEND_FROM_EMAIL`（選填）；僅放於 env，不得進程式碼或 log。
  - 投遞：依 Resend SLA；失敗寫入 `notification_events` 並標記 `error_message`。
  - 清理：`notification_events` 保留策略依資料保留政策；無額外信箱清理腳本（由 Resend 端管理）。
- **程式**：`backend/app/services/notification.py`；觸發點：`create_journal`、`respond_card` / deck respond。

---

## 觀測最小集（Observability Minimum）

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Full health check: database, Redis, providers, WS SLI, burn-rate. Returns `200` (ok) or `503` (degraded). |
| `GET /health/slo` | SLI/SLO snapshot: WS connection accept rate, message pass rate, burn-rate windows, HTTP runtime, rate-limit metrics. |

### Key Metrics

- **HTTP latency**: p50 / p95 / p99 (provided by `/health` via `sli.http_runtime`)
- **Error rate**: HTTP 5xx ratio over 15-minute window
- **WS disconnect rate**: `connections_disconnected` / `connections_accepted`
- **WS burn-rate**: Fast (5m + 1h) and slow (6h + 24h) windows; thresholds in config
- **Queue depth**: `notification_queue_depth` in `/health` response
- **Rate-limit blocks**: `sli.write_rate_limit.blocked_total` breakdown by scope/action/endpoint

### Structured Logging Format

All log lines include request context:

```
%(asctime)s %(levelname)s [%(name)s] [request_id=%(request_id)s user_id=%(user_id)s] %(message)s
```

- `request_id`: UUID per HTTP request (from `X-Request-Id` header or auto-generated)
- `user_id`: Set after auth dependency resolves the current user

### PII Redaction Policy

- Journal/card content is **never** logged in full. Use `redact_content(value, max_visible=N)` for truncated previews with length hint.
- Email addresses are masked via `redact_email()` (e.g., `a***@example.com`).
- User names use `redact_name()` (returns `[name]` placeholder).
- Implementation: `backend/app/core/log_redaction.py`; tests: `backend/tests/test_log_redaction.py`.

### Stack traces in production

- **`LOG_INCLUDE_STACKTRACE`** (backend): Default is `false`. In **production** do not set `LOG_INCLUDE_STACKTRACE=true`; it would write full stack traces to logs on 500 errors and can leak internal paths. Use `true` only in development for debugging.

---

## 資料庫與 Redis

- **DB**：Supabase；連線 `DATABASE_URL`。異常時見 incident-response 第 1 節。
- **Redis**：選用；用於 abuse guard / rate limit 多實例時。`ABUSE_GUARD_STORE_BACKEND=redis`、`ABUSE_GUARD_REDIS_URL`。異常時見 incident-response 第 2 節。

---

## WebSocket 與 Rate limit

- **WS**：`/ws/{user_id}`；連線數與 message rate 由 `backend/app/services/ws_abuse_guard.py` 與 config 限制。
- **SLI/burn-rate**：`/health/slo` 暴露；main 分支 CI 跑 `check_slo_burn_rate_gate.py`。告警見 `docs/ops/incident-response-playbook.md` WS 相關章節。

---

## Data Rights 演練與回滾

- **Export**：`GET /api/users/me/data-export`
- **Erase**：`DELETE /api/users/me/data`
- **演練步驟與證據**：`docs/security/data-rights-fire-drill.md`
- **回滾**：Data rights 為不可逆；僅能透過備份/還原 DB（若有）復原，營運上不建議回滾 erase。

---

## P2 排程任務 (Cron)

以下腳本建議以 cron 或排程系統每日執行（需 DB 與通知矩陣就緒）：

| 腳本 | 建議時間 | 說明 |
|------|----------|------|
| `backend/scripts/run_time_capsule_dispatch.py` | 每日 08:00 | P2-C 時光膠囊：對有伴侶用戶檢查「一年前的今天」是否有回憶，若有則發送 time_capsule 通知給雙方。本腳本僅讀 DB 與發送通知（無需 S3）。 |
| `backend/scripts/run_active_care_dispatch.py` | 每日 09:00 | P2-D 主動關懷：找出「連續 3 天無互動」（無日記、無卡片回答）的伴侶對，對雙方各發一則 active_care 破冰／抽卡邀請。 |
| `backend/scripts/run_dynamic_content_weekly.py` | 每週一 04:00 | P2-E 動態內容：生成 5 張「時事卡片」並寫入「時事」牌組；需 `OPENAI_API_KEY`（可選，失敗時用 fallback）。 |

- **執行方式**：`cd backend && PYTHONPATH=. python scripts/run_<name>.py`
- **關閉**：停用 cron 即可；或於 `docs/security/notification-trigger-matrix.json` 將對應 trigger 設為 `enabled: false`。

---

## Mobile App（Expo）

- **專案**：`apps/haven-mobile`（React Native / Expo），與 web 共用後端與 `packages/haven-shared`。
- **執行**：`cd apps/haven-mobile && npm install && npx expo start`；可設 `EXPO_PUBLIC_API_URL` 指向後端 API base URL。
- **Core Flow**：登入、日記、今日抽卡、牌組房均已接上；詳見 `apps/haven-mobile/README.md`。

---

## P2-I 審核後台與 BI

- **內容審核（ADMIN-02）**：使用者檢舉 `POST /api/reports`；管理員審核介面 `/admin/moderation`（前端），需 `CS_ADMIN_ENABLED`、`CS_ADMIN_ALLOWED_EMAILS`、`CS_ADMIN_WRITE_EMAILS`。佇列 API：`GET /api/admin/moderation/queue`、`POST /api/admin/moderation/{report_id}/resolve`。資料表：`content_reports`（遷移 `g1p2i0000001`）。
- **BI 整合（ADMIN-03）**：唯讀 DB 連線與 Retention Cohort 查詢範例見 `docs/ops/bi-metabase-tableau.md`；Metabase/Tableau 建議使用唯讀角色連線。

---

## 回滾與發布

- **應用回滾**：Render/Vercel 等從前一版重新 deploy。
- **DB 遷移回滾**：`alembic downgrade -1`（僅在遷移腳本支援且經評估後執行）。
- **Release gate**：`./scripts/release-gate.sh`；CI：`.github/workflows/release-gate.yml`。Launch checklist：`docs/P0-LAUNCH-GATE.md`。
- **本地全棧 gate**：`bash scripts/release-gate-local.sh`（順序：override 合約 → backend security-gate → 可選 quick backend 合約測試 → frontend check:env / typecheck / seed:cards:review → mobile typecheck（若存在 `apps/haven-mobile`）→ 可選 E2E（需 `RUN_E2E=1` 與 `E2E_BASE_URL`）。CUJ 證據過期時先執行 `bash scripts/generate-cuj-synthetic-evidence-local.sh`。

### 本地程序清理（Process Hygiene）

- **預覽清理名單（dry-run）**：`bash scripts/cleanup-dev-processes.sh`
- **實際清理（SIGTERM）**：`bash scripts/cleanup-dev-processes.sh --apply`
- **強制清理（SIGKILL）**：`bash scripts/cleanup-dev-processes.sh --apply --force`
- **Makefile 快捷**：
  - `make dev-cleanup-procs`
  - `make dev-cleanup-procs-apply`

---

## CI Gate 故障對照（快速定位）

| 症狀 | 先看哪裡 | 常見原因 | 第一個動作 |
|------|----------|----------|------------|
| `backend-gate` 失敗（security-gate） | `backend/scripts/security-gate.sh` | authorization matrix 漏更新、evidence freshness 過期、safety/schema 測試失敗 | 先本地跑 `cd backend && ./scripts/security-gate.sh`，按失敗測試檔修正 |
| `test_ai_schema_contract.py` / `test_ai_schema_fuzz.py` 失敗 | `backend/tests/test_ai_schema_contract.py`, `backend/tests/test_ai_schema_fuzz.py` | AI schema 欄位變更、enum 值不一致、safety tier 越界 | 對齊 `backend/app/schemas/ai.py`，必要時同步更新測試樣本 |
| `test_ai_safety_logic.py` 失敗 | `backend/tests/test_ai_safety_logic.py` | moderation 正規化或 tier 規則修改未同步 | 對照 `backend/app/services/ai_safety.py` 規則與測試期望 |
| `check_threat_model_contract.py` 或 `test_threat_model_contract_policy.py` 失敗 | `docs/security/threat-model-stride.json` | STRIDE 欄位缺漏、control 參照檔不存在 | 補齊 threat model 欄位與 control reference 路徑 |
| `check_abuse_economics_contract.py` 或 `test_abuse_economics_contract_policy.py` 失敗 | `docs/security/abuse-economics-policy.json` | 成本/上限欄位不合法、mapped control 檔不存在 | 修正 unit_cost/cap/threshold 與 control 路徑 |
| `check_prompt_abuse_policy_contract.py` 或 `test_prompt_abuse_policy*.py` 失敗 | `docs/security/prompt-abuse-policy.json`, `backend/app/services/prompt_abuse.py` | policy pattern 與 runtime pattern 不一致 | 同步更新 policy id 與 runtime regex / 測試 |
| `check_encryption_posture_contract.py` 或 `test_encryption_posture_contract_policy.py` 失敗 | `docs/security/encryption-posture-policy.json` | TLS/HSTS baseline 設定不合法或 reference 缺失 | 修正 posture policy 與 reference 路徑 |
| `check_consent_receipt_contract.py` 或 `test_consent_receipt_contract_policy.py` 失敗 | `docs/security/consent-receipt-policy.json` | consent 欄位/版本格式錯誤，或 evidence path 失效 | 修正 consent policy required_fields、版本與證據路徑 |
| `check_prompt_rollout_policy_contract.py` 或 `test_prompt_rollout_policy_contract.py` 失敗 | `docs/security/prompt-rollout-policy.json` | canary/guardrail 設定非法或 reference 缺失 | 修正 rollout policy 參數（canary_percent、promotion gate） |
| `check_ai_eval_framework_contract.py` 或 `test_ai_eval_framework_contract_policy.py` 失敗 | `docs/security/ai-eval-framework.json` | auto/human suite 不足或 entry path 失效 | 補齊 required suites 與對應 entry 檔案 |
| `frontend-e2e` 在 PR fail | `.github/workflows/release-gate.yml` `frontend-e2e` | 本機/CI 暫時性 flake、頁面文案變更 | 先重跑 job；若為預期文案改動，更新 `frontend/e2e/smoke.spec.ts` |
| `frontend-e2e` 在 main fail（會擋版） | `frontend/e2e/smoke.spec.ts` + workflow log | 破壞核心頁面可用性、server 啟動失敗 | 優先修 smoke 用例或頁面回歸，main 合併前需綠燈 |
| `slo-burn-rate gate` 失敗 | `backend/scripts/check_slo_burn_rate_gate.py` | `/health/slo` 指標降級、`sli.abuse_economics` 觸發 `block`、或 URL/token 設定錯誤 | 先驗證 health URL/token，再查 incident playbook 的 WS/SLI 與 abuse economics 章節 |

### 故障時最低動作順序

1. 先重跑同一個 CI job，排除瞬時 flake。  
2. 在本地重現同一指令（security-gate / test:e2e / release-gate）。  
3. 若是 schema/safety 失敗，先以「回到 contract」為準，避免直接放寬 gate。  
4. 若是 main 阻擋，優先 hotfix 修復 gate，不帶新功能。  

---

## Top 10 全端優化收斂（2026-03）

以下檢查已接到 `scripts/release-gate-local.sh`，可在本地/CI 重複驗證：

1. `backend/scripts/check_api_contract_sot.py`
2. `backend/scripts/check_write_idempotency_coverage.py`
3. `backend/scripts/check_outbox_slo_gate.py`
4. `backend/scripts/check_ai_runtime_gate.py`
5. `backend/scripts/check_observability_payload_contract.py`
6. `backend/scripts/check_bola_coverage_from_inventory.py`
7. `backend/scripts/check_rate_limit_policy_contract.py`
8. `backend/scripts/run_data_rights_fire_drill_snapshot.py`
9. `backend/scripts/run_growth_cost_snapshot.py`
10. `frontend/src/lib/optimistic-sync.ts` + `frontend/src/hooks/queries/useJournalMutations.ts`（失敗時前端降級入本地 queue）
11. `frontend/scripts/generate-api-contract-types.mjs` + `frontend/src/types/api-contract.ts`（由 API inventory 自動生成前端契約型別，release gate 會檢查是否過期）

補充：`scripts/check-worktree-materialization.py` 已接到 `release-gate-local`，用於 iCloud dataless 檔案風險預檢（local 可降級、CI/main fail-closed）。
