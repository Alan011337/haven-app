0) Policy 一句話

在不破壞 safety 與 schema 的前提下：先用免費/低成本供應商；遇到 rate limit/供應商不穩要「可預期地重試 + 迅速切換」；品質或成本超標就自動降級（更便宜/更穩/更短輸出）並留下可追蹤的決策證據。

⸻

1) 你現有 Router 的輸入/輸出契約

1.1 請求類型（Request Classes）

你現在 AI 功能主要分兩類（至少）：
	•	JOURNAL_ANALYSIS：analyze_journal() 產出 JournalAnalysis（結構化、要 schema compliance）
	•	COOLDOWN_REWRITE：rewrite_aggressive_to_i_message()（短輸出、低成本、強 safety）

Router policy 要把「請求類型」納入決策，因為它決定：
	•	可接受的最小品質（schema/一致性）
	•	最大 token / latency
	•	可接受的 provider（免費 provider 可能只允許部分任務）

1.2 強制前置：Moderation / Safety Tier

你已經做了 omni-moderation-latest 的 precheck 與 tier merge。這一步要保持「永遠在 router 之前」：
	•	若 precheck 直接升級到高風險：跳過昂貴模型，直接走你的 circuit-breaker fallback（你現有 _apply_safety_circuit_breaker 即可）
	•	Router policy 只負責「在允許生成的前提下」怎麼選 provider、怎麼重試、怎麼降級

OpenAI 也把「被 rate limit 時要 backoff / retry」列為建議實務（尤其 429）。 ￼

⸻

2) Provider 分層：Free-first 但有底線

2.1 Provider Tier 定義（示例）

你可以在 policy 檔定義 provider 的等級與能力（這是 free-tier 優先的核心）：
	•	Tier F (Free / Sponsor / Trial)：免費額度、或你自己能吃的免費池
	•	Tier C (Cheap)：最便宜可用、品質可接受
	•	Tier P (Premium)：最穩、最準、schema compliance 最好（但貴）

同一個 provider 可能同時有多種「model profile」。Router 決策單位建議用 Profile 而不是 provider 名稱。

2.2 官方 rate limit / quota 是真實約束

例如 Google Gemini 的 Gemini API 有「requests per minute 等 quota / rate limit」概念，超過就會被限流（你需要對 429 / RESOURCE_EXHAUSTED 做好策略）。 ￼

⸻

3) 錯誤分類：讓 retry/fallback 可預期

把 provider adapter 丟回來的錯誤（你已有 ai_errors.py）統一映射成：

3.1 Retryable（可重試）
	•	RATE_LIMITED：HTTP 429 / quota exceeded
	•	TRANSIENT_NETWORK：timeout、TLS、5xx、連線重置
	•	PROVIDER_OVERLOADED：503 / 529 等（視供應商回傳）

重點：尊重 Retry-After
HTTP 的 Retry-After header 用來告訴 client 何時再試（經典用在 503，也常見於限流/維護情境）。 ￼
實務上很多 API 在 429 也會給 Retry-After；你應該「有就用，沒有就 backoff」。

3.2 Non-retryable（不該重試）
	•	AUTH_FAILED / BILLING_DISABLED
	•	INVALID_REQUEST（schema/prompt 太長、參數錯）
	•	SAFETY_BLOCKED（被 moderation 或供應商安全阻擋）
	•	SCHEMA_VALIDATION_FAILED（若同一 provider 同一請求已連續失敗 N 次，改走 fallback 或換 provider，不要無限重試）

⸻

4) Retry Policy：速率限制的 retry / fallback（可直接照做）

這段你可以直接丟給 agent 改 ai_router.py 的核心邏輯。

4.1 重試總原則
	1.	先同 provider profile 小重試（1–2 次）：避免因瞬間尖峰直接切換造成震盪
	2.	若仍失敗：立刻切換到下一個候選 profile（通常是「同 tier」或「更穩 tier」）
	3.	若遇到 Retry-After：尊重它的下限（不要比它更早重試） ￼
	4.	每次重試要加上 exponential backoff + jitter（OpenAI 也建議用退避處理 429）。 ￼

4.2 建議參數（你可寫進 ai-cost-quality-policy.json）
	•	max_attempts_per_profile: 2
	•	max_total_attempts: 4（含切換 profile）
	•	base_backoff_ms: 400
	•	max_backoff_ms: 8000
	•	jitter: full jitter（0~backoff）

4.3 Rate limit 的「快速切換」規則

對於 429（或 Gemini quota exceeded），不要傻等太久：
	•	若 Retry-After <= 2s：等它再試 1 次
	•	若 Retry-After > 2s：立刻 failover 到下一個 profile（因為你是線上互動 app，不值得卡住）
	•	若無 Retry-After：用 backoff 等 0.4s、0.8s，最多等到 1.6s；再不行就切

Gemini API 的「有 quota / rate limit」是已知事實，所以你必須把 429/限流當成常態處理，而不是例外。 ￼

4.4 切換順序（free-tier 優先）

對 JOURNAL_ANALYSIS 建議候選順序（示例）：
	1.	gemini_free（Tier F）
	2.	openai_cheap（Tier C）
	3.	openai_premium（Tier P）
	4.	若都失敗 → _get_fallback_response()（你現有安全文案）

對 COOLDOWN_REWRITE：
	1.	gemini_free（Tier F）
	2.	openai_cheap（Tier C）
	3.	若都失敗 → 直接走 deterministic rewrite template（非 AI fallback）

⸻

5) Cost-Quality Gate：新增規則（重點是「可自動降級」）

你現在已有 ai_quality_monitor.py + ai-cost-quality-policy.json。我建議把 gate 從「監控」進化到「可干預 router 決策」。

5.1 你需要追的 4 個指標

每個 request_class × provider_profile 都要有：
	1.	Schema Compliance Rate：valid_json && passes_pydantic 的比例
	2.	Fallback Rate：走 _get_fallback_response() 的比例
	3.	Safety Escalation Rate：moderation/tier 升級觸發 circuit breaker 的比例
	4.	Cost per Successful Output：成功輸出的平均成本（或 token）

5.2 Gate 的新規則（可直接寫入 policy）

下面每條都能在 router 里落地：

Rule A — Schema 失敗就降級輸出形狀（先救可用性）
若某 profile 在最近 N=50 次 JOURNAL_ANALYSIS：
	•	schema_compliance < 0.97
→ 該 profile 對 JOURNAL_ANALYSIS 進入 DEGRADED 15 分鐘
→ 降級策略：
	•	限制輸出 token（更短更不容易跑格式）
	•	提高 temperature 以外的「格式約束」：例如強化 system prompt 的 JSON-only、或改用 function calling/JSON schema（若你已有）

Rule B — 成本超標就切到更便宜 profile（但要符合品質下限）
若 cost_per_success > cost_cap（例如：單次 journal 分析成本 > $0.01）
→ router 對該 user 或全域啟動 BUDGET_MODE
→ 候選順序改為：Tier F → Tier C（並禁用 Tier P）
→ 同時縮短輸出（token cap 下調 30%）

Rule C — 429 熱點就開「冷卻視窗」避免雪崩
對同一 profile，若 60 秒內 RATE_LIMITED >= 3
→ 對該 profile 開 60–120 秒 cooldown（不再嘗試）
→ 直接從下一順位開始

Rule D — 品質守門：免費不夠穩就自動升級
free-tier profile 若在最近 N 次：
	•	fallback_rate > 5% 或 schema_compliance < 0.95
→ 對 JOURNAL_ANALYSIS 永久降為「非首選」
→ 仍保留給 COOLDOWN_REWRITE（因為任務較簡單）

⸻

6) Router 決策流程（貼給 agent 的偽代碼）

def route(request_class, safety_tier, user_plan, budget_mode, context):
    if safety_tier >= TIER_BLOCK:
        return FALLBACK_SAFE_RESPONSE

    candidates = policy.candidates_for(request_class, user_plan)

    # cost-quality gates mutate candidate order / availability
    candidates = apply_global_degraded_profiles(candidates)
    candidates = apply_budget_mode(budget_mode, candidates)
    candidates = apply_profile_cooldowns(candidates)

    attempts = 0
    for profile in candidates:
        per_profile_attempts = 0
        while per_profile_attempts < policy.max_attempts_per_profile:
            try:
                resp = call_provider(profile, request_class, context)
                parsed = parse_schema(resp)  # JournalAnalysis / etc
                record_success(profile)
                return parsed

            except RateLimited as e:
                record_rate_limited(profile)
                ra = e.retry_after_seconds
                if ra and ra > policy.rate_limit_failover_threshold_s:
                    mark_cooldown(profile, ra)
                    break  # failover immediately
                sleep(backoff_with_jitter(ra))
                per_profile_attempts += 1
                attempts += 1

            except TransientNetwork as e:
                record_transient(profile)
                sleep(backoff_with_jitter(None))
                per_profile_attempts += 1
                attempts += 1

            except SchemaError as e:
                record_schema_error(profile)
                # do NOT infinite retry; either 1 retry then failover
                per_profile_attempts += 1
                attempts += 1
                if per_profile_attempts >= 2:
                    break

            except NonRetryable as e:
                record_nonretryable(profile)
                break

            if attempts >= policy.max_total_attempts:
                return FALLBACK_SAFE_RESPONSE

    return FALLBACK_SAFE_RESPONSE

關鍵點：429 要嘛短等，要嘛快速切；而不是一直卡同一個 provider。退避/重試是官方建議作法。 ￼
Retry-After 的語意是「告訴你多久再試」。 ￼

⸻

7) Policy 檔案格式（你可以新增一份 router-policy.json）

（給你一個「可直接 PR」的結構；agent 可照這個落地）

{
  "version": "2026-03-03",
  "max_attempts_per_profile": 2,
  "max_total_attempts": 4,
  "rate_limit_failover_threshold_s": 2,
  "backoff": { "base_ms": 400, "max_ms": 8000, "jitter": "full" },

  "request_classes": {
    "JOURNAL_ANALYSIS": {
      "token_cap": 900,
      "min_schema_compliance": 0.97,
      "candidate_profiles": ["gemini_free", "openai_cheap", "openai_premium"]
    },
    "COOLDOWN_REWRITE": {
      "token_cap": 220,
      "candidate_profiles": ["gemini_free", "openai_cheap"]
    }
  },

  "profiles": {
    "gemini_free": { "tier": "F", "cooldown_on_rate_limit_hits_60s": 3 },
    "openai_cheap": { "tier": "C" },
    "openai_premium": { "tier": "P" }
  },

  "gates": {
    "degrade_window_minutes": 15,
    "schema_compliance_degrade_below": 0.97,
    "fallback_rate_deprioritize_above": 0.05,
    "budget_mode_cost_cap_usd_per_success": 0.01
  }
}


⸻

8) Observability：你 PR 要一起做的 metrics

在 ai_router.py 每次決策都打點（你已提到 runtime metrics）：
	•	router.decisions_total{request_class, chosen_profile, reason}
	•	router.failover_total{from_profile, to_profile, error_class}
	•	router.retry_total{profile, error_class}
	•	router.cooldown_active{profile}
	•	ai.schema_error_total{profile, request_class}
	•	ai.fallback_total{request_class, reason}

⸻

9) 測試清單（你可以直接丟進 PR 描述）
	1.	test_router_respects_retry_after()：429 帶 Retry-After=5 → 直接 failover（因為 >2s）
	2.	test_router_short_retry_after_retries_once()：429 帶 Retry-After=1 → sleep 後重試一次
	3.	test_router_schema_error_failover()：schema error 連兩次 → failover
	4.	test_budget_mode_disables_premium()：budget mode → candidates 不含 premium
	5.	test_degraded_profile_removed_temporarily()：profile 被標 degraded → 15 分鐘內不被選
	6.	test_safety_tier_blocks_generation()：tier >= block → 直接 fallback（不呼叫 provider）

⸻

10) 對 Coding Agent 的「PR 任務拆分」(最小可交付)

PR-1（Router policy + retry/fallback）
	•	新增 router-policy.json（或併入你現有 ai-cost-quality-policy.json）
	•	ai_router.py：實作 candidates、cooldown、Retry-After、exponential backoff+jitter
	•	ai_errors.py：統一錯誤分類（至少把 429 映射為 RATE_LIMITED）

PR-2（Cost-quality gates 接到 router）
	•	ai_quality_monitor.py 產出 degraded_profiles 狀態（本地 cache / redis / db 皆可）
	•	router 在選 candidates 前套用 gate

⸻

11) 文件級硬邊界（v1 最終收斂）

11.1 Canonicalization 覆蓋範圍（JCS）
	•	input_fingerprint 的 canonicalization 僅作用於「已 parse 成 JSON value」的結構化資料，不對原始文字做 trim/正規化。
	•	原始 text（例如日記內容）一律先轉成 normalized_content_hash，再放入 canonical JSON。
	•	key sorting 需符合 RFC 8785（JCS）deterministic property sorting 規則；實作需維持 deterministic canonical bytes。
	•	canonical input 僅允許可 deterministic JSON 型別（例如 string/int/bool/null/array/object）；禁止 NaN/Infinity 或語言特有非 JSON 數值表示（遵循 JCS 可序列化子集）。

11.2 Idempotency 狀態碼決策順序（避免誤讀）
	•	先判斷同 key 是否 in-flight：若是，語意為 409 Conflict。
	•	僅在非 in-flight 時，才判斷同 key 與不同 fingerprint：strict mode 語意為 422 Unprocessable Content。
	•	決策順序不可交換：`inflight -> mismatch -> ok`，避免同時成立時回錯誤類型。
	•	`bypass_and_continue` 仍為預設策略；`reject` 僅在策略明確開啟時生效。

11.3 Metrics 高基數底線
	•	任何 unbounded 欄位（例如 user_id、request_id、email、raw model/provider 回傳字串）禁止進入 metrics labels。
	•	即使值符合 regex/長度限制，若不在 allowlist enum 內，一律映射固定常數 `unknown`，不得使用 hash/截斷字串作為替代 label。
	•	原始值僅可進 redacted debug log，不可進 metrics series。
	•	`unknown` 必須是固定常數，不可使用動態 hash/截斷字串以避免隱性高基數。
