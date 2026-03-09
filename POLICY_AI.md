# AI 功能告知與使用邊界（P0）

> 對應 P0-F / P0-G。具體 UI 行為見 `docs/safety/safety-ui-policy-v1.md`，後端邏輯見 `backend/app/services/ai_safety.py`、`backend/app/services/ai.py`。

---

## 1. 功能告知

- Haven 使用 AI（如 OpenAI）對日記內容進行情緒分析與建議，並用於推薦卡牌互動。
- 分析結果僅供參考，不構成醫療、心理或法律建議；高風險內容會觸發安全分級與介面引導。

## 2. 安全分級（Safety Tier）

| Tier | 說明 | 前端行為 |
|------|------|----------|
| 0 | 一般 | 正常顯示 |
| 1 | 輕度提醒 | Amber 提示，內容仍顯示 |
| 2 | 隱藏＋冷靜 | 內容預設隱藏，可點擊揭露；顯示危機資源 |
| 3 | 強制鎖定 | 鎖定＋倒數；醒目顯示專線 |

實作：`docs/safety/safety-ui-policy-v1.md`、前端 `SafetyTierGate` / `ForceLockBanner`、後端 moderation + circuit breaker。

## 3. 使用邊界與政策（Immutable Policies）

以下政策已嵌入系統 Prompt（`backend/app/core/prompts.py`），不可由模型覆寫：

- **[AI-POL-01] 不冒充伴侶**：AI 永遠不能假裝成使用者的伴侶，或以伴侶的口吻說話。所有建議必須以第三人稱的「建議角度」呈現。
- **[AI-POL-02] 危機一致化**：當 `safety_tier >= 2` 時，所有建議必須優先導向專線求助與自我照顧。不得產生可能強化風險的互動建議（如「試著跟對方溝通」）。
- **[AI-POL-03] 關係教練邊界**：AI 不是心理治療師或醫師。避免診斷式語氣（如「你有憂鬱症」）、指令式語氣（如「你必須這樣做」）。以支持、建議、觀察為主。

## 4. 提示詞安全與供應鏈

- **Prompt 版本控制**：`CURRENT_PROMPT_VERSION` 追蹤版本，`PROMPT_POLICY_HASH` 以 SHA-256 驗證完整性。
- **Prompt injection 防護**：`backend/app/services/prompt_abuse.py` 對使用者輸入進行正則比對，攔截已知注入模式（ignore system prompt、jailbreak roleplay 等）。
- **Moderation 前置過濾**：使用 OpenAI Moderation API（`omni-moderation-latest`）在分析前篩檢；分析使用 structured output（`JournalAnalysis` schema）。
- **Canary rollout**：Prompt 變更依 `docs/security/prompt-rollout-policy.json` 分批上線，先 10% canary，通過 SLO + safety regression gate 後才全面推送。

## 4.1 AI Router 基線（P1-I）

- 目前支援 provider 策略宣告：`openai`、`gemini`（`docs/security/ai-router-policy.json`）。
- 現階段 runtime 僅實作 OpenAI client；若配置到未實作 provider，系統會安全降級回 OpenAI，不中斷核心流程。
- Router 相關配置：
  - `AI_ROUTER_PRIMARY_PROVIDER`
  - `AI_ROUTER_FALLBACK_PROVIDER`
  - `AI_ROUTER_ENABLE_FALLBACK`

## 4.2 AI 成本與品質監控基線（P1-I）

- 政策檔：`docs/security/ai-cost-quality-policy.json`
- 監控腳本：`backend/scripts/run_ai_quality_snapshot.py`
- 品質/成本阈值（可透過 env 覆寫）：
  - `AI_SCHEMA_COMPLIANCE_MIN`
  - `AI_HALLUCINATION_PROXY_MAX`
  - `AI_DRIFT_SCORE_MAX`
  - `AI_COST_MAX_USD_PER_ACTIVE_COUPLE`
  - `AI_TOKEN_BUDGET_DAILY`
- 若超標：標記 degraded 並觸發降級建議；核心 journal write 不得被阻塞。

## 5. 測試與回歸

| 測試類型 | 檔案 | 含義 |
|---------|------|------|
| Schema 合約 | `test_ai_schema_contract.py` | JSON 結構驗證 |
| Schema fuzz | `test_ai_schema_fuzz.py` | 隨機輸入模糊測試 |
| Safety 邏輯 | `test_ai_safety_logic.py` | Tier 推導閾值 |
| Safety 回歸 | `test_safety_regression.py` | 政策常數 + prompt 版本 |
| Red-team | `test_ai_safety_redteam.py` | 對抗性輸入測試 |
| Prompt 供應鏈 | `test_prompt_supply_chain.py` | Hash 完整性驗證 |
| Prompt abuse | `test_prompt_abuse_policy.py` | 注入模式偵測 |

上述全部納入 `backend/scripts/security-gate.sh`，作為 Safety regression 閘門。

## 6. 評測框架

詳見 `docs/ai-safety/evaluation-framework.md`：
- **自動化**：Schema compliance >= 99.9%、safety regression 0 regressions
- **人工評測**：每月抽樣 50 筆分析，按同理心/準確性/安全性/可行性/語氣五維度評分（合格 >= 4.0/5.0）

---

*正式上線前應由法務/合規審閱並依營運地法規補充告知與同意流程。*
