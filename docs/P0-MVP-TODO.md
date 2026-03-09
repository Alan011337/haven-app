# P0 MVP — 可執行 TODO 列表 (B)

> 每一項對應：repo 檔案、預計新增/修改的檔案、驗收方式（DoD）。  
> 順序依 Critical Path：P0-D → P0-E → P0-G → P0-H → P0-I，P0-A/B 穿插落地。

---

## P0-A/B：上線閘門與 DoD 落地

| ID | 項目 | 既有/相關檔案 | 新增/修改 | 驗收方式 |
|----|------|----------------|-----------|----------|
| META-1 | Launch Readiness checklist 實體 | `docs/p0-execution-protocol.md`, `.github/workflows/release-gate.yml`, `backend/scripts/security-gate.sh` | 新增 `docs/P0-LAUNCH-GATE.md` | LAUNCH-01 每子項可勾選且對應到 CI job / 測試名 / 文件；PR 可引用 |
| META-2 | DoD 範本（每任務必填） | `docs/p0-execution-protocol.md` | 新增或擴充 `docs/P0-DOD-TEMPLATE.md`，並在 `.github/PULL_REQUEST_TEMPLATE.md` 或 CONTRIBUTING 引用 | 範本含：成功定義、失敗/降級行為、觀測點、測試、安全隱私檢查、回滾策略 |

---

## P0-D：8 decks / Library / Email backup / Health

| ID | 項目 | 既有/相關檔案 | 新增/修改 | 驗收方式 |
|----|------|----------------|-----------|----------|
| D-1 | 8 decks 內容/seed 驗證 | `frontend/scripts/seed.ts`（已含 8 類 VALID_CATEGORIES）, `frontend/scripts/data/cards.json` | 確保 seed 驗證/QA 涵蓋 8 類；可選：`npm run seed:cards:validate` 或 CI 檢查 8 類皆有卡片 | `npm run seed:cards:validate` 通過且 8 類皆有；或文件註明「8 類需在 cards 來源中齊全」 |
| D-2 | Library 頁 UI/UX + RWD | `frontend/src/app/decks/page.tsx`, `frontend/src/lib/deck-meta.ts` | 微調 grid、間距、八大入口在手機/平板/桌機顯示 | 手動或 e2e：/decks 在 320px / 768px / 1024px 無破版、8 牌組皆可點 |
| D-3 | Email 營運說明 + health/uptime | `backend/app/main.py`（/health 已有 email 狀態）, `docs/ops/` | 新增根目錄 `RUNBOOK.md`（≤200 行）：含 Health、UptimeRobot、Email 供應商（金鑰、SLA、未配置時行為）、DB/Redis/WS 診斷連結 | RUNBOOK.md 存在且指向 `/health`、UptimeRobot、Resend、incident-response；review 通過 |

---

## P0-E：BOLA / Rate limit / WS abuse / Secrets baseline

| ID | 項目 | 既有/相關檔案 | 新增/修改 | 驗收方式 |
|----|------|----------------|-----------|----------|
| E-1 | Secrets 管理 baseline | `backend/scripts/check_env.py`, `docs/security/` | 新增根目錄 `SECURITY.md`（≤200 行）：含 Key rotation / env separation 原則、漏洞回報、OWASP/evidence 對照 | SECURITY.md 存在；可選：check_env 或 release-gate 檢查敏感 key 不在 log |
| E-2 | BOLA/OWASP 與 CI 對應 | `backend/scripts/security-gate.sh`, `docs/security/owasp-api-top10-mapping.md` | 確認 security-gate 已跑所有 mapping 內列出的 test；必要時補一兩個 test 或 checklist 條目 | `./backend/scripts/security-gate.sh` 通過；owasp mapping 中 evidence 路徑皆有效 |

---

## P0-G：Age gating / Legal stub / Data rights 文件

| ID | 項目 | 既有/相關檔案 | 新增/修改 | 驗收方式 |
|----|------|----------------|-----------|----------|
| G-1 | Age gating 最小實作 | `backend/app/api/routers/users.py`（註冊）, 前端註冊/登入或敏感入口 | 後端：註冊或 ToS 同意時可選欄位/claim「已滿 18」；或前端註冊流程勾選 + 政策連結；政策寫入 `docs/legal/` 或 POLICY | 註冊或首次進入敏感流程有年齡/條款確認；政策文件存在且可連結 |
| G-2 | Legal docs stub（Privacy / ToS + versioning） | — | 新增 `docs/legal/PRIVACY_POLICY.md`, `docs/legal/TERMS_OF_SERVICE.md`（標題 + version + 日期 + 最少條文 stub） | 兩檔案存在；內含 version 或 last_updated；可從前端 footer/設定連結 |
| G-3 | DATA_RIGHTS.md 根目錄 | `docs/security/data-rights-fire-drill.md`, `backend/app/api/routers/users.py`（export/erase） | 新增根目錄 `DATA_RIGHTS.md`（≤200 行）：Access/Export/Erase、API、證據、CI 對應 | 檔案存在；含 export/erase 端點與演練/證據說明 |

---

## P0-H：Structured logs / PII redaction / 觀測最小集

| ID | 項目 | 既有/相關檔案 | 新增/修改 | 驗收方式 |
|----|------|----------------|-----------|----------|
| H-1 | Request ID 貫穿 | `backend/app/middleware/request_context.py`, `backend/app/main.py` | `main.py` 掛上 `RequestContextMiddleware` | 請求有 `x-request-id`；日誌可帶 request_id（若已用 var） |
| H-2 | 結構化 log 欄位 | `backend/app/services/rate_limit.py`, 各 router | 統一關鍵路徑 log 帶 request_id/user_id（從 context/deps）；可先做 middleware 或 logging filter | 至少 rate_limit 與一處 API 日誌含 request_id；文件註明「觀測最小集」 |
| H-3 | PII redaction | 各處 logger.*(..., email=, name=, content=) | 新增 `backend/app/core/log_redaction.py`（redact_email, redact_name 等）；在 logging 或 audit 寫入前呼叫 | 單元測試：redact 後無明文 email/姓名；至少一處 log 改用 redact 後輸出 |
| H-4 | 觀測最小集文件 | `docs/ops/`, `/health`, `/health/slo` | 在 RUNBOOK 或獨立小節：latency/error/queue/ws 觀測點、後續 metrics/tracing 擴充 | RUNBOOK 或 docs 有「觀測最小集」一節且對應 /health |

---

## P0-I：JSON schema / CUJ e2e / Safety regression

| ID | 項目 | 既有/相關檔案 | 新增/修改 | 驗收方式 |
|----|------|----------------|-----------|----------|
| I-1 | JSON schema contract 測試 | `backend/app/schemas/ai.py`, `backend/app/services/ai.py` | 新增 `backend/tests/test_ai_schema_contract.py`：以 JournalAnalysis 驗證樣本或 mock 回傳 | pytest 通過；至少 1 筆合法 + 1 筆非法 schema 案例 |
| I-2 | CUJ e2e 最小集 | — | 新增 e2e（Playwright 或同類）：Bind → Ritual/Journal → Unlock 任一路徑；可放 `frontend/e2e/` 或 `tests/e2e/` | CI 可跑；至少 1 條 CUJ 通過（或標記 optional 待環境就緒） |
| I-3 | Safety regression hook | `backend/app/services/ai_safety.py`, 現有 safety 相關 test | 將 safety 相關 test 列為 release-gate 必跑；或新增 `backend/tests/test_safety_regression.py` 與 CI 標記 | release-gate 或 security-gate 含明確 safety 測試集合；文件對應 |

---

## 對應關係速查

- **CI 入口**：`.github/workflows/release-gate.yml`；本地：`./scripts/release-gate.sh`, `./backend/scripts/security-gate.sh`
- **Health**：`GET /health`, `GET /health/slo`；測試：`backend/tests/test_health_endpoint.py`
- **Data rights**：`GET /api/users/me/data-export`, `DELETE /api/users/me/data`；演練：`docs/security/data-rights-fire-drill.md`
- **Launch 必要文件**：根目錄 `SECURITY.md`, `RUNBOOK.md`, `DATA_RIGHTS.md`；Legal stub：`docs/legal/PRIVACY_POLICY.md`, `docs/legal/TERMS_OF_SERVICE.md`
