# P2 開發清單 — 前端已完成項目 (2026-02-23)

本文件對應「請把 P2 開發清單中還未完成的項目都通通完成」中，**可由前端實作且已完成**的項目。需後端、基礎設施或產品決策的項目列於文末「未在本輪實作」一節。

---

## P2-A. 視覺藝術化 (Visual Polish)

| 項目 | 狀態 | 說明 |
|------|------|------|
| 八大牌組專屬視覺：卡背 | ✅ | `deck-meta.ts` 已為 8 個牌組定義 `cardBack`（gradient、border、glow）；`TarotCard` 依 `category` 顯示對應卡背。 |
| 八大牌組：動畫特效 (Flip / Glow) | ✅ | 引入 **Framer Motion**；`TarotCard` 使用 spring 翻轉、揭牌後套用牌組 `glowClass` 陰影。 |
| 情緒背景漸變 (Dynamic Background) | ✅ | `DynamicBackgroundWrapper` + `mood-background.ts` + feature flag `dynamic_background_enabled`；依 `mood_label` 切換背景漸層。 |
| 質感 UI 全面升級 (Glassmorphism) | ✅ | `globals.css` 新增 `.glass`、`.glass-card`；套用於 Sidebar（桌面/手機）、DeckRoomView 主卡、JournalCard（一般狀態）。 |
| Haptic Feedback | ✅ | `lib/feedback.ts`：`navigator.vibrate` 於抽卡成功、解鎖成功、可選 onTap；DailyCard / useDeckRoom 已掛接。 |
| 音效系統 (Audio Branding) | ✅ | `lib/feedback.ts`：Web Audio API 產生「抽卡」輕掃聲與「解鎖」短鈴聲；與 haptic 同時觸發。 |
| 優化所有前端頁面 UI/UX | 🚧 | 已做：motion 統一、glass、tokens、a11y 基礎；其餘為持續精修（留白、微互動等）。 |

---

## P2-L. 設計系統 (Haven Design System)

| 項目 | 狀態 | 說明 |
|------|------|------|
| [DS-01] Design Tokens | ✅ | `globals.css` 為單一來源；`design-tokens.json` 匯出 motion、radius、glass 等供文件/跨平台對照。 |
| [DS-02] Motion System | ✅ | 已有 `--ease-haven`、`--ease-haven-spring`、`--duration-haven-fast`、`--duration-haven`；Framer Motion 翻轉使用 spring。 |

---

## P2-K. 無障礙標準

| 項目 | 狀態 | 說明 |
|------|------|------|
| [A11y] Dynamic Type / Font scaling | ✅ | `globals.css` 在 `prefers-contrast: more` 時略為放大根字級。 |
| [A11y] Color Blindness Mode | ✅ | 提供 `.color-blind-safe` 工具類（outline/underline 輔助），可加在 `body` 或特定區塊。 |
| Screen Reader / WCAG 2.2 AA | 🚧 | 既有 focus-visible、aria-label、tab 結構；完整 WCAG 2.2 AA 清單與自動化檢查為後續項目。 |

---

## P2-M. 前端 i18n 框架

| 項目 | 狀態 | 說明 |
|------|------|------|
| 前端 i18n 框架架構 | ✅ | `messages/zh-TW.json`、`src/lib/i18n.ts`（`t(key)`、`getLocale()`）；`docs/frontend/i18n-setup.md` 說明日後接 next-intl 的步驟。 |

---

## P2-B / P2-C 已在本輪實作（後端 + 前端）

- **P2-B 擴展基石**：✅ 已完成。分片準備、讀寫分離、WebSocket Redis Pub/Sub、DATA-READ-01、CACHE-01、QUEUE-01、ARCH-01；對照見 `docs/P2-B-SCALABILITY-COMPLETE.md`。
- **P2-C 回憶長廊**：✅ 已完成。多媒體日曆、雙視圖（Feed / Calendar）、時光膠囊派送與推播、AI 關係週報/月報；對照見 `docs/P2-C-MEMORY-LANE-COMPLETE.md`。

## P2-D 已在本輪實作（後端 + 法務文件）

- **P2-D 智慧引導基礎**：✅ 已完成。主動關懷 Cron（run_active_care_dispatch.py）、衝突緩解與調解模式（關鍵字偵測、MediationSession、GET/POST /api/mediation）、LEGAL-01/02、PRD-RISK-01 Graceful Exit；對照見 `docs/P2-D-LIFECOACH-COMPLETE.md`。

## 未在本輪實作（需後端 / 基礎設施 / 產品決策）

- **P2-E 進階內容**：Dynamic Content Pipeline — 後端。
- **P2-F 離線優先**：PWA / Local queue / CRDT — 前後端與架構決策。
- **P2-G 原生轉型**：React Native / Expo 評估、Monorepo — 架構與評估。
- **P2-H 進階加密**：E2EE、零知識 — 後端與安全設計。
- **P2-I BI 與營運**：審核後台、BI 整合 — 後端與工具。
- **P2-J 進階 Ops**：Chaos、Multi-region、Code Yellow — DevOps。

---

## 驗收指令

```bash
cd frontend
npm run lint    # 0
npm run typecheck  # 0
npm run build   # 0
```

手動建議：抽卡 / 解鎖時確認有震動與音效（需允許瀏覽器音效）；開啟 `dynamic_background_enabled` 後首頁依 mood 變換背景；Sidebar / 牌組房卡片為玻璃擬態。
