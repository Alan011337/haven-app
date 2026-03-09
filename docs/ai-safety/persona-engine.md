# AI Persona Engine（P1-H 基線）

## 目的
- 將 Haven AI 固定為「第三者觀察者」視角，避免冒充伴侶。
- 在不破壞現行分析流程前提下，先落地可開關的 Dynamic Context Injection。

## Persona 定義
- `persona_id`: `third_party_observer_v1`
- 核心原則：
  - `AI-POL-01` 不冒充伴侶
  - `AI-POL-02` 危機一致化（`safety_tier >= 2` 優先安全）
  - `AI-POL-03` 關係教練邊界（非診斷、非命令）

## Dynamic Context Injection
- 功能旗標：`AI_DYNAMIC_CONTEXT_INJECTION_ENABLED`（預設 `false`）
- 執行位置：`backend/app/services/ai_persona.py`
- 近期情緒氣象 hint 來源：`backend/app/api/journals.py`（最近 48h、最多 6 筆 journal）
- 策略：
  - `relationship_weather_inference`：根據當前內容判斷 `conflict/repair/neutral`
  - `relationship_weather_hint`：當前內容為 `neutral` 時，回退到近期 pair weather（衝突/修復）
  - `conflict_to_deescalation_guidance`：衝突時優先降刺激、降命令語氣
  - `repair_signal_amplification`：正向訊號時放大感謝/見證

## Runtime Output Guardrail（AI-01）
- 功能旗標：`AI_PERSONA_RUNTIME_GUARDRAIL_ENABLED`（預設 `true`）
- 執行位置：
  - 規則：`backend/app/services/ai_persona.py`（`apply_persona_output_guardrails`）
  - 串接：`backend/app/services/ai.py`（`analyze_journal`）
- 規則（v1）：
  - `partner_identity_claim_rewrite`：改寫「我是你的男/女朋友」等冒充語句
  - `direct_love_phrase_rewrite`：改寫直接第一人稱告白語句（句首 `我愛你` / `I love you`）
  - 維持第三者觀察者口吻，不暴露原始日記內容到 log
- 降級行為：
  - 偵測到違規時採「sanitize output」而非中斷分析流程（不阻斷核心 CUJ）。
  - 僅記錄規則命中 `rule_ids/fields/version`（不記錄敏感文本）。

## 安全與降級
- 旗標關閉時，系統 message 與既有行為完全一致（無額外 context）。
- 旗標開啟且推斷為 `neutral` 時，不注入額外 context（最小干預）。
- 任何高風險內容仍由 `ai_safety` 與 `safety circuit breaker` 主導。

## 觀測與測試
- 單元測試：`backend/tests/test_ai_persona.py`
- 近期 hint 測試：`backend/tests/test_journal_dynamic_context_hint.py`
- 契約測試：`backend/tests/test_ai_persona_policy_contract.py`
- Contract gate：`backend/scripts/check_ai_persona_policy_contract.py`
- Env 檢查：`backend/tests/test_backend_env_check.py`（guardrail flag）
