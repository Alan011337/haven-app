# WCAG 2.2 Level AA — Haven 對照清單

本文件為 P2-K [A11Y-WCAG-01] 產物：WCAG 2.2 Level AA 條款與 Haven 前端元件/頁面對照，供手動與自動化檢查使用。

**自動化**：CI 已納入 `npm run lint`（含 ESLint 規則）；可選加 axe-core 於 e2e。  
**單一來源**：本清單對應 [WCAG 2.2](https://www.w3.org/TR/WCAG22/) Level AA。

---

## 1. Perceivable

| 準則 | 條款 | Haven 對應 / 備註 |
|------|------|-------------------|
| 1.1 Text Alternatives | 1.1.1 Non-text Content | 圖標按鈕使用 `aria-label`（如 JournalCard 刪除、複製邀請碼、返回連結）；TarotCard 裝飾性圖示可加 `aria-hidden`。 |
| 1.3 Adaptable | 1.3.1 Info and Relationships | 表單：`<label htmlFor>` 與 `id` 對應（PartnerSettings、DeckHistoryFiltersBar、decks 排序）；標題階層 h1/h2 合理。 |
| 1.3 Adaptable | 1.3.2 Meaningful Sequence | 閱讀順序與 DOM 順序一致；Tab 面板使用 `hidden` 與順序可聚焦。 |
| 1.4 Distinguishable | 1.4.3 Contrast (Minimum) | 使用 ART-DIRECTION 色彩（非純黑/純白）；文字與背景對比符合 AA。 |
| 1.4 Distinguishable | 1.4.4 Resize Text | 支援 200% 縮放；`prefers-contrast: more` 時略放大根字級（globals.css）。 |
| 1.4 Distinguishable | 1.4.11 Non-text Contrast | 控制項與邊框對比；focus-visible 環使用 `ring-ring`。 |

---

## 2. Operable

| 準則 | 條款 | Haven 對應 / 備註 |
|------|------|-------------------|
| 2.1 Keyboard Accessible | 2.1.1 Keyboard | 所有功能可鍵盤操作；無僅依賴滑鼠。 |
| 2.1 Keyboard Accessible | 2.1.2 No Keyboard Trap | 焦點可離開 Dialog、Tab、Drawer；使用 Radix Dialog 與 roving tabindex。 |
| 2.4 Navigable | 2.4.1 Bypass Blocks | 主內容區可跳過導覽（可選 skip link）。 |
| 2.4 Navigable | 2.4.3 Focus Order | 焦點順序與視覺/邏輯一致；Tab 使用 roving tabindex。 |
| 2.4 Navigable | 2.4.7 Focus Visible | 鍵盤焦點使用 `focus-visible:` 環（全站已統一）。 |
| 2.5 Input Modalities | 2.5.3 Label in Name | 可視標籤與無障礙名稱一致；圖標按鈕 `aria-label` 與可見 tooltip 對齊。 |

---

## 3. Understandable

| 準則 | 條款 | Haven 對應 / 備註 |
|------|------|-------------------|
| 3.1 Readable | 3.1.1 Language of Page | `<html lang="zh-TW">` 已設定。 |
| 3.2 Predictable | 3.2.1 On Focus | 聚焦不自動提交表單或大幅變更內容。 |
| 3.2 Predictable | 3.2.2 On Input | 變更設定不自動提交；表單需明確送出。 |
| 3.3 Input Assistance | 3.3.1 Error Identification | 表單錯誤以 `aria-invalid`、`aria-describedby` 與內文說明（Input 元件）。 |
| 3.3 Input Assistance | 3.3.2 Labels or Instructions | 必填與格式說明以 label/placeholder 提供。 |

---

## 4. Robust

| 準則 | 條款 | Haven 對應 / 備註 |
|------|------|-------------------|
| 4.1 Compatible | 4.1.2 Name, Role, Value | 自訂控制項具 role、accessible name；Dialog、Tab 使用 Radix 或 ARIA 正確。 |
| 4.1 Compatible | 4.1.3 Status Messages | 非干擾式狀態（如 toaster）以 `role="status"` 或 `aria-live` 宣告（Sonner）。 |

---

## 元件對照速查

| 元件 / 頁面 | 對應準則 | 備註 |
|-------------|----------|------|
| HomeHeader 標籤 | 2.1.1, 2.4.7, 4.1.2 | WAI-ARIA Tabs，roving tabindex，focus-visible。 |
| Sidebar / Drawer | 2.1.2, 2.4.7 | 導航連結與按鈕 focus-visible；drawer 可鍵盤關閉。 |
| JournalCard | 1.1.1, 2.5.3 | 刪除按鈕 `aria-label="刪除日記"`。 |
| PartnerSettings | 1.3.1, 2.5.3 | label + input id；複製按鈕 aria-label。 |
| DeckHistoryFiltersBar | 1.3.1, 2.4.7 | 篩選與排序 select 有 label；focus-visible。 |
| error.tsx / not-found.tsx | 2.4.7, 3.3.1 | CTA 按鈕 focus-visible。 |
| DailyCard / DeckRoomView | 2.4.7, 3.3.2 | 按鈕與 textarea focus-visible、label。 |

---

## CI 與手動驗證

- **Lint**：`cd frontend && npm run lint`（ESLint 含 Next 推薦規則，可擴充 jsx-a11y）。
- **手動**：鍵盤僅操作主要流程（登入 → 首頁 Tab → 日記 → 牌組房 → 設定）；螢幕報讀器抽查焦點與名稱。
- **可選**：e2e 加入 axe-playwright 或類似，對關鍵頁面跑 axe-core。
