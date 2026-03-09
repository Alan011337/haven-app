# P0 MVP — Repo 現況盤點 (A)

> 對應 P0-D ~ P0-I + P0-A/P0-B gate 落地。僅列與 launch 相關的既有檔案、端點、測試與**缺口**（具體路徑）。  
> 上限約 200 行；每項可對應到 code/test/CI。

---

## 1. 啟動 / 測試 / 遷移 / CI 入口

| 項目 | 指令/入口 | 備註 |
|------|-----------|------|
| **後端本地啟動** | `./backend/scripts/run-dev.sh` | 會先跑 `python3 scripts/check_env.py`，再 `uvicorn app.main:app --reload` |
| **前端本地啟動** | `cd frontend && npm run dev` | predev 會跑 `npm run check:env` |
| **後端單元/整合測試** | `cd backend && python -m pytest -q -p no:cacheprovider` | 或 `./backend/scripts/security-gate.sh`（含 policy 腳本 + 指定 test 列表） |
| **前端檢查** | `cd frontend && npm run check:env`、`TYPECHECK_TIMEOUT_MS=180000 npm run typecheck`、`npm run test` (`test:e2e`) | e2e 需先安裝 Playwright browser (`npx playwright install`) |
| **DB 遷移** | `cd backend && ./scripts/run-alembic.sh upgrade head` | 遷移檔在 `backend/alembic/versions/` |
| **CI Pipeline** | `.github/workflows/release-gate.yml` | 觸發：PR / push to main。含 backend env check、security-gate、pytest、SLO burn-rate gate（main 必過）、frontend check:env + typecheck |
| **本地一鍵 Release Gate** | `./scripts/release-gate.sh` | 依序：backend check_env → security-gate → check_slo_burn_rate_gate → pytest；frontend check:env + typecheck |

---

## 2. P0-D：8 decks / Library / Email backup / Health

### 已存在

- **8 大牌組 enum + 前端 meta**  
  - `backend/app/models/card.py`：`CardCategory` 已含 DAILY_VIBE, SOUL_DIVE, SAFE_ZONE, MEMORY_LANE, GROWTH_QUEST, AFTER_DARK, **CO_PILOT**, **LOVE_BLUEPRINT**  
  - `frontend/src/lib/deck-meta.ts`：`DECK_META_MAP` / `DECK_META_LIST` 已含 8 組（含 CO_PILOT、LOVE_BLUEPRINT 顏色與 Lucide 圖標）  
  - `frontend/src/types/index.ts`：CardCategory 與後端對齊  
- **Health endpoint**  
  - `backend/app/main.py`：`GET /health`、`GET /health/slo`；含 DB/Redis/email 狀態、runtime ws、rate_limit SLI  
  - `backend/tests/test_health_endpoint.py`：health 與 health/slo 測試  
  - `docs/ops/uptimerobot-setup.md`：UptimeRobot 監控 `/health` 設定說明  
- **Email 通知鏈路**  
  - `backend/app/services/notification.py`：`queue_partner_notification` → `send_partner_notification_with_retry` → Resend；`is_email_notification_enabled()` 依 `RESEND_API_KEY`  
  - `backend/app/api/journals.py`：create_journal 內呼叫 `queue_partner_notification`  
  - `backend/app/api/routers/card_decks.py` / `cards.py`：respond 後呼叫 `queue_partner_notification`  
  - `backend/tests/test_notification_service.py`、`test_journal_notification_rules.py`、`test_card_mode_isolation.py`（含 email 觸發次數）  

### 缺口（具體路徑）

- **8 decks「內容」更新**：DB/seed 是否已為 8 大牌組各準備足夠題目（含 CO_PILOT、LOVE_BLUEPRINT）；若仍以 6 大為主，需確認 `frontend/scripts/seed.ts` 或匯入來源是否涵蓋 8 類。  
- **Library UI/UX**：P0-D 要求「優化牌組圖書館頁面 UI/UX」與 RWD；需對應 `frontend/src/app/...` 圖書館頁（含 grid、八大入口）。  
- **Email backup 營運**：無集中「營運層」說明（供應商金鑰、投遞 SLA、清理策略）；建議收斂至 RUNBOOK 或 SECURITY 一節，並可選在 `/health` 或文件註明「未配置時為 warning」。  
- **UptimeRobot 實際綁定**：文件有，需確認 production 是否已對 `GET /health` 設 monitor（非 code 缺口，為 ops 檢查項）。

---

## 3. P0-E：BOLA / Authorization Matrix / Rate limit / WS abuse / Secrets

### 已存在

- **BOLA / Authorization Matrix**  
  - `docs/security/endpoint-authorization-matrix.json` + `backend/scripts/check_endpoint_authorization_matrix.py` + `backend/tests/test_endpoint_authorization_matrix_policy.py`  
  - `docs/security/read-authorization-matrix.json` + `backend/scripts/check_read_authorization_matrix.py` + `backend/tests/test_read_authorization_matrix_policy.py`  
  - 各 resource 的 authz 測試：`test_user_authorization_matrix.py`、`test_journal_authorization_matrix.py`、`test_card_authorization_matrix.py`、`test_card_deck_authorization_matrix.py`、`test_notification_authorization_matrix.py`、`test_billing_authorization_matrix.py` 等，並在 `backend/scripts/security-gate.sh` 中列為必跑。  
- **Rate limit**  
  - `backend/app/services/rate_limit.py`：journal_create、card_response_create（user/IP/device/partner_pair）；`backend/app/core/config.py` 對應設定  
  - `backend/app/services/rate_limit_runtime_metrics.py` + `/health` 與 `/health/slo` 的 write_rate_limit  
  - 測試：`test_journal_notification_rules.py`、`test_card_mode_isolation.py` 內 rate limit 案例；`test_rate_limit_runtime_metrics.py`、`test_abuse_budget_policy.py`  
- **WebSocket 濫用防護**  
  - `backend/app/services/ws_abuse_guard.py`：message rate limit、backoff、max payload  
  - `backend/app/main.py`：`WsAbuseGuard` 在 `/ws/{user_id}` 使用；`WS_MAX_CONNECTIONS_PER_USER` / `WS_MAX_CONNECTIONS_GLOBAL` 在 config  
  - `backend/tests/test_ws_abuse_guard.py`  
- **OWASP 對照**  
  - `docs/security/owasp-api-top10-mapping.md`：BOLA、Authn、Property、Resource、Function 等對應與 evidence 路徑  

### 缺口（具體路徑）

- **Secrets 管理 baseline**：無集中「Key rotation policy + env separation」文件或 CI 檢查；建議在 `SECURITY.md` 或 `docs/security/` 一節 + 可選 `check_env.py` 或 release-gate 檢查項。  
- **BOLA 等 OWASP 測試與 CI gate 對應**：mapping 已有，需確認 release-gate / security-gate 已涵蓋所有列出的 test 檔（目前 security-gate.sh 已列多數 authz 與 rate limit 測試）。

---

## 4. P0-G：Age gating / Legal docs / Data rights

### 已存在

- **Data rights（Export/Erase）**  
  - `GET /api/users/me/data-export`、`DELETE /api/users/me/data`：`backend/app/api/routers/users.py`  
  - `backend/tests/test_data_rights_api.py`  
  - `docs/security/data-rights-export-package-spec.json`、`data-rights-deletion-graph.json`、`data-deletion-lifecycle-policy.json`  
  - `backend/scripts/check_data_rights_contract.py`、`validate_security_evidence.py --kind data-rights-fire-drill`  
  - `docs/security/data-rights-fire-drill.md`、P0 drill 腳本含 data-rights 演練  

### 缺口（具體路徑）

- **Age gating**：程式與文件中未見年齡門檻（birthday/age/minor）或性內容政策實作；需在後端或前端註冊/敏感功能路徑加年齡確認，並在 `docs/` 或 POLICY 中寫明 policy（P0 最小可行）。  
- **Legal docs stub**：無 repo 內 `Privacy Policy` / `ToS` / Consent 版本化 stub（例如 `docs/legal/PRIVACY_POLICY.md`、`docs/legal/TERMS_OF_SERVICE.md` 加 version 與日期）。  
- **Launch 必要文件**：無根目錄 `SECURITY.md`、`RUNBOOK.md`、`DATA_RIGHTS.md`；現有內容分散在 `docs/ops/`、`docs/security/`，需收斂為 launch 最小集並對應到 code/test/CI。

---

## 5. P0-H：Structured logs / Metrics / Tracing / PII redaction

### 已存在

- **Request ID 基礎**  
  - `backend/app/middleware/request_context.py`：`request_id_var`、`RequestContextMiddleware` 設定 `x-request-id`  
  - **未掛載**：`backend/app/main.py` 僅掛了 `CORSMiddleware` 與 `append_security_headers`，未使用 `RequestContextMiddleware`，故 request_id 未貫穿請求。  
- **部分結構化**  
  - `backend/app/services/rate_limit.py`：`_log_rate_limit_block` 含 endpoint、action、scope、user_id 等  
  - `/health`、`/health/slo`：runtime、sli、write_rate_limit 等 metrics 已存在  

### 缺口（具體路徑）

- **Structured logging 一致化**：未統一採用 request_id / user_id / partner_id / session_id / mode 等欄位；需在 middleware 或 logging filter 中注入並確保 log 格式一致（例如 JSON 或固定 key）。  
- **Metrics 匯出**：無 Prometheus/OpenMetrics 或其它 metrics endpoint；若 P0 僅依賴 `/health`、`/health/slo` 可視為最小可行，但文件中需寫明「觀測最小集」與後續擴充點。  
- **Tracing**：無 API → DB → AI → parse → commit 全鏈路 tracing（可 P0 僅文件標註為後續項，或最小 span 標記）。  
- **PII redaction**：未見 log/trace 中對 email、姓名、日記/卡片內容的 redaction；P0-H 與「敏感資料不得進 log/trace」要求需在 logging 層或 audit 寫入前實作 redaction。

---

## 6. P0-I：JSON schema contract / Fuzz / CUJ e2e / Safety regression

### 已存在

- **AI 分析 JSON 結構**  
  - `backend/app/schemas/ai.py`：`JournalAnalysis`（Pydantic）+ `CardRecommendation`  
  - `backend/app/services/ai.py`：`client.beta.chat.completions.parse(..., response_format=JournalAnalysis)`，寫入前有 safety circuit breaker  
- **Safety**  
  - Moderation 前置 + safety_tier 合併 + 斷路器；`backend/app/services/ai_safety.py`、`backend/app/services/ai.py`  
  - 前端：`SafetyTierGate`、`ForceLockBanner`、`frontend/src/lib/safety-policy.ts` 等  

### 缺口（具體路徑）

- **JSON schema contract 測試**：無獨立的「API 回傳或 AI 輸出符合 JournalAnalysis schema」的 contract/fuzz 測試（例如 pytest 用 schema 驗證樣本或 fuzz 生成）。  
- **CUJ e2e**：無 Playwright/Cypress 等 e2e；僅後端 pytest。需新增最小 CUJ e2e（Bind → Ritual → Journal → Unlock 等）並在 CI 可跑。  
- **Safety regression hook**：無專用「safety regression」CI job 或 script；可將現有 safety 相關 test 標記並在 release-gate 中列為必跑，或新增一組 red-team 風格用例。

---

## 7. P0-A / P0-B：Gate 落地為 checklist + CI gate

### 已存在

- **DoD / 協議文件**  
  - `docs/p0-execution-protocol.md`：含優先級、DoD 要素、依賴、release gate 基線、CUJ、Security/Privacy/Legal、Billing、證據 freshness 等  
- **CI 已涵蓋**  
  - `.github/workflows/release-gate.yml`：backend 測試 + security-gate + SLO burn-rate；frontend check:env + typecheck  
  - `backend/scripts/security-gate.sh`：多項 policy 腳本 + 指定 authz/rate limit/evidence 測試  
  - P0 drill、data-rights、billing、audit-log、data-soft-delete evidence 皆有 `validate_security_evidence.py` 與 freshness 參數  

### 缺口（具體路徑）

- **Launch Readiness checklist 實體**：無單一「Launch Readiness Gate」清單檔案（例如 `docs/LAUNCH-CHECKLIST.md` 或 `docs/P0-LAUNCH-GATE.md`），逐項對應到 CI job / 測試名稱 / 文件；P0-B 的 LAUNCH-01 各子項需可勾選且對應到上述 artifact。  
- **P0-A DoD template**：可從 p0-execution-protocol 擷取為「每任務 DoD 範本」一節，並在 issue/PR 模板或 CONTRIBUTING 中引用，使「成功定義、失敗行為、觀測、測試、安全、回滾」成為必填。

---

## 8. Launch 必要文件狀態（≤200 行/份，對應 code/test/CI）

| 文件 | 狀態 | 說明 |
|------|------|------|
| **SECURITY.md** | 缺 | 需新增；可收斂 `docs/security/owasp-api-top10-mapping.md`、abuse、evidence、CI gate 路徑，並註明漏洞回報方式。 |
| **RUNBOOK.md** | 部分 | 已有 `docs/ops/incident-response-playbook.md`、`docs/ops/uptimerobot-setup.md`；可新增根目錄 RUNBOOK.md 精簡版，對應 health、DB、Redis、WS、billing、data-rights 演練與回滾。 |
| **DATA_RIGHTS.md** | 部分 | 已有 data-rights-fire-drill、export/erase spec；可新增根目錄 DATA_RIGHTS.md，說明 Access/Export/Erase 與證據/CI。 |
| **POLICY_AI.md** | 可選 | 若需明示 AI 功能告知、邊界、安全分級，可新增並對應 safety-policy、prompt 版本、moderation。 |

---

## 9. 小結：缺口優先對應

- **P0-D**：8 decks 內容/seed 確認、Library 頁 UI/UX/RWD、Email 營運說明、UptimeRobot 實際綁定。  
- **P0-E**：Secrets baseline 文件/可選 CI、確認 BOLA/OWASP 測試全在 security-gate。  
- **P0-G**：Age gating 最小實作 + 文件、Legal stub（Privacy/ToS + versioning）、SECURITY/RUNBOOK/DATA_RIGHTS 根目錄最小集。  
- **P0-H**：掛上 RequestContextMiddleware、結構化 log 欄位、PII redaction、觀測最小集文件。  
- **P0-I**：JSON schema contract/fuzz 測試、CUJ e2e、Safety regression CI hook。  
- **P0-A/B**：Launch checklist 檔案、DoD 範本對應到 PR/issue。

以上路徑均為 repo 內既有或建議新增的具體位置，可作為 B) 可執行 TODO 與 C) 小步提交的依據。
