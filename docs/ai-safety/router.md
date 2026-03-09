# AI Router（P1-I 基線）

## 目的
- 建立 provider abstraction，支援 OpenAI + Gemini runtime fallback。
- 在 provider timeout / 5xx / transient failure 時，自動切換下一個 provider，避免中斷核心 journal 分析流程。

## 設計
- 支援 provider：`openai`、`gemini`。
- Request class：`journal_analysis`、`cooldown_rewrite`（同政策、不同成本/品質門檻）。
- 路由策略：
  - `l1_classify_extract`（快速分類/擷取）：預設可指向較低成本 provider。
  - `l2_deep_reasoning`（深度推理）：預設指向高品質 provider。
- Router Policy v1 runtime：
  - free-tier-first 候選排序（quality gate/cooldown aware）。
  - idempotency + inflight reservation + short-lived result cache（重試安全，避免重複扣費）。
  - 429/timeout/5xx 分類重試，`Retry-After` 門檻決定短等重試或立即 failover。
  - schema validation 連續失敗觸發 profile cooldown。
  - Redis degraded mode 進入保守策略（no cache/no poll/no sleep）。
- runtime 會依 `provider_chain` 執行 adapter：
  - primary 成功：直接回傳。
  - primary timeout / 5xx / transient failure：切換 fallback provider。
  - all providers 失敗：回到既有 `fallback response`（不中斷寫入流程）。
- Gemini adapter 使用 REST API (`generateContent`) 並要求 JSON response，再用 `JournalAnalysis` schema 驗證。

## 配置
- `AI_ROUTER_PRIMARY_PROVIDER`（預設：`openai`）
- `AI_ROUTER_L1_PRIMARY_PROVIDER`（預設：空，空值時沿用 `AI_ROUTER_PRIMARY_PROVIDER`）
- `AI_ROUTER_L2_PRIMARY_PROVIDER`（預設：空，空值時沿用 `AI_ROUTER_PRIMARY_PROVIDER`）
- `AI_ROUTER_FALLBACK_PROVIDER`（預設：空）
- `AI_ROUTER_ENABLE_FALLBACK`（預設：`false`）
- `GEMINI_API_KEY`（使用 Gemini provider 時必填）
- `AI_ROUTER_GEMINI_MODEL`（預設：`gemini-2.0-flash-lite`）
- `AI_ROUTER_SHARED_STATE_BACKEND`（預設：`memory`；允許 `memory` / `redis`）
- `AI_ROUTER_REDIS_URL`（優先使用；當 `AI_ROUTER_SHARED_STATE_BACKEND=redis` 且未提供時，runtime 會回退到 `REDIS_URL`，再回退到 `ABUSE_GUARD_REDIS_URL`）

## 降級策略
- provider unavailable / timeout / 5xx：`primary_then_fallback`
- all providers fail：回到既有安全 fallback response（不中斷 journal write）
- 永不阻斷 journal write

## 觀測
- `trace_span` 會帶：
  - `provider`
  - `provider_chain`
  - `router_reason`
  - `router_reason` 可能值：
    - `task_policy_l1`
    - `task_policy_l2`
    - `task_policy_unknown_normalized_to_l2`
    - `configured_primary`
    - `*_normalized_to_default`
- runtime metric counters（in-memory）：
  - `ai_router_fallback_activated_total`
  - `ai_router_fallback_success_total`
  - `ai_router_success_<provider>_<profile>_total`
  - `ai_router_failure_<provider>_<profile>_<reason>_total`
  - `ai_router_cache_hit_total` / `ai_router_cache_fingerprint_mismatch_total`
  - `ai_router_schema_cooldown_activated_total`
  - `ai_router_degraded_mode_total`

## 測試與 Gate
- 單元測試：`backend/tests/test_ai_router.py`
- 任務路由契約測試（L1/L2）：`backend/tests/test_ai_router.py`
- runtime fallback 測試（timeout / 5xx / metric）：`backend/tests/test_ai_router_runtime.py`
- analyze_journal 整合測試（primary fail -> fallback success / exhausted -> safe fallback）：`backend/tests/test_ai_provider_fallback_integration.py`
- Gemini adapter error-contract 測試（invalid JSON / empty content / schema fail / 5xx）：`backend/tests/test_ai_gemini_adapter.py`
- 契約測試：`backend/tests/test_ai_router_policy_contract.py`
- Policy gate：`backend/scripts/check_ai_router_policy_contract.py`
