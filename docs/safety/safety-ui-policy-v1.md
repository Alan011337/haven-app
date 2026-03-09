# Safety UI Policy v1 — 安全分級顯示策略

> Haven 的內容安全分級系統，根據 AI 偵測到的情緒風險等級，決定前端 UI 的呈現方式。

## Tier Behavior Matrix

| Tier | 名稱 | Banner | 內容顯示 | 危機資源 | 樣式 |
|------|------|--------|----------|----------|------|
| 0 | Normal | 無 | 完整顯示 | 無 | 預設 |
| 1 | Nudge | Amber 提示 | 完整顯示 | 無 | amber-500 |
| 2 | Hide + Cooldown | Rose 警示 | 隱藏，需點擊揭露 | 顯示專線 | rose-400 |
| 3 | Force Lock | Rose 鎖定 | 鎖定 + 30 秒倒數 | 醒目顯示專線 | rose-600 |

---

## Tier 0 — Normal

- **觸發條件：** 情緒風險分數低於閾值，無安全疑慮
- **Banner：** 無
- **內容：** 完整顯示，無任何遮罩或延遲
- **危機資源：** 不顯示

```
┌─────────────────────────┐
│  [正常卡片/日記內容]      │
└─────────────────────────┘
```

---

## Tier 1 — Nudge（輕度提醒）

- **觸發條件：** AI 偵測到輕微情緒波動訊號
- **Banner：** Amber 色調，文字：「伴侶可能正在經歷情緒波動」
- **內容：** 完整顯示，不遮蔽
- **危機資源：** 不顯示
- **目的：** 讓閱讀者帶著同理心閱讀，不製造恐慌

```
┌─────────────────────────────────────┐
│ ⚠ 伴侶可能正在經歷情緒波動          │  ← amber-500 bg
├─────────────────────────────────────┤
│  [正常卡片/日記內容]                  │
└─────────────────────────────────────┘
```

### Frontend 實作要點

- Banner 使用 `bg-amber-500/10 text-amber-700` (light) / `bg-amber-500/20 text-amber-300` (dark)
- Banner 不可被使用者關閉（persist during session）

---

## Tier 2 — Hide + Cooldown（隱藏 + 冷靜期）

- **觸發條件：** AI 偵測到中度情緒風險
- **Banner：** Rose 色調警示
- **內容：** 預設隱藏，使用者需主動點擊「點擊查看內容」按鈕才能揭露
- **危機資源：** 顯示危機專線

```
┌─────────────────────────────────────┐
│ 🩷 此內容包含較敏感的情緒表達        │  ← rose-400 bg
├─────────────────────────────────────┤
│                                     │
│   ┌───────────────────────┐         │
│   │    點擊查看內容        │         │  ← tap to reveal button
│   └───────────────────────┘         │
│                                     │
├─────────────────────────────────────┤
│ 📞 1925 安心專線（24hr）             │
│ 📞 113 保護專線                      │
└─────────────────────────────────────┘
```

### 危機專線資訊

| 專線 | 號碼 | 說明 |
|------|------|------|
| 安心專線 | **1925** | 衛福部 24 小時免費心理諮詢 |
| 保護專線 | **113** | 家暴、性侵害通報及諮詢 |

### Frontend 實作要點

- 內容區域使用 `blur-lg` 或替換為佔位區塊
- 點擊揭露後內容淡入（`transition-opacity duration-300`）
- 揭露動作記錄至 analytics（不記錄內容本身）

---

## Tier 3 — Force Lock（強制鎖定）

- **觸發條件：** AI 偵測到高度情緒風險或危機訊號
- **Banner：** Rose-600 鎖定警示
- **內容：** 完全鎖定，30 秒倒數計時器結束後才顯示解鎖按鈕
- **危機資源：** 醒目顯示，置於畫面最上方
- **目的：** 強制冷靜期，確保使用者先看到危機資源

```
┌─────────────────────────────────────┐
│ 🚨 偵測到較強烈的情緒訊號            │  ← rose-600 bg, white text
├─────────────────────────────────────┤
│                                     │
│  如果你或伴侶需要協助：              │
│                                     │
│  ☎ 1925 安心專線（24 小時免費）      │  ← 可點擊撥號
│  ☎ 113 保護專線                     │  ← 可點擊撥號
│                                     │
├─────────────────────────────────────┤
│                                     │
│        🔒 內容已鎖定                 │
│      請等待 [28] 秒後解鎖            │  ← 30s countdown
│                                     │
└─────────────────────────────────────┘
```

倒數結束後：

```
│      ┌──────────────────┐           │
│      │   解鎖查看內容    │           │  ← 解鎖按鈕出現
│      └──────────────────┘           │
```

### Frontend 實作要點

- 倒數使用 `setInterval`，不依賴 server time
- 倒數期間解鎖按鈕不渲染（非 disabled，而是不存在於 DOM）
- 危機專線使用 `tel:` link，行動裝置可直接撥號
- 樣式：`bg-rose-600 text-white` for banner
- 解鎖動作記錄至 analytics，包含等待時間

---

## Backend API 回應格式

Safety tier 由後端 AI 分析後透過 API 回傳：

```json
{
  "content_id": "uuid",
  "safety_tier": 2,
  "display_hint": "hide_with_reveal",
  "crisis_resources": [
    { "name": "安心專線", "number": "1925", "hours": "24hr" },
    { "name": "保護專線", "number": "113", "hours": "24hr" }
  ]
}
```

## Implementation Status

| Component | File | Status |
|-----------|------|--------|
| Policy constants | `frontend/src/lib/safety-policy.ts` | Done |
| SafetyTierGate | `frontend/src/components/features/SafetyTierGate.tsx` | Done |
| ForceLockBanner (30s) | `frontend/src/components/features/ForceLockBanner.tsx` | Done |
| PartnerJournalCard wiring | `frontend/src/components/features/PartnerJournalCard.tsx` | Done |
| PartnerSafetyBanner | `frontend/src/components/features/PartnerSafetyBanner.tsx` | Done |
| Backend moderation | `backend/app/services/ai_safety.py` | Done |
| Backend circuit breaker | `backend/app/services/ai.py` | Done |
| Prompt abuse guard | `backend/app/services/prompt_abuse.py` | Done |

## 變更紀錄

| 日期 | 版本 | 說明 |
|------|------|------|
| 2025-01 | v1.0 | 初始版本，定義四級安全分級 |
| 2026-02-19 | v1.1 | SafetyTierGate/ForceLockBanner 元件實作完成；新增實作狀態表 |
