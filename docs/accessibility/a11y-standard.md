# P2-K. 無障礙標準（A11y Standard）

**目標**：Screen Reader 支援、Dynamic Type、Color Blindness Mode、WCAG 2.2 AA 清單與自動化檢查。

---

## [A11Y-01] Screen Reader Support

| 項目 | 說明 |
|------|------|
| **實作** | 關鍵互動元件使用 `aria-label`、`aria-describedby`、`role`；按鈕/連結具備可讀文案；表單欄位有 `<label>` 或 `aria-label`。 |
| **位置** | `frontend/src/components/`：Button、Input、Sidebar、Modal、卡片與表單；`e2e/a11y.spec.ts` 以 axe 檢查。 |
| **DoD** | 核心頁面通過 axe WCAG 2.2 AA；焦點順序與鍵盤可操作（focus-visible 已套用）。 |

---

## [A11Y-02] Dynamic Type / Font Scaling

| 項目 | 說明 |
|------|------|
| **實作** | `frontend/src/app/globals.css`：`html { font-size: 100%; }`；`@media (prefers-contrast: more)` 時 `font-size: 106%`，尊重系統字級與對比偏好。 |
| **延伸** | 字級使用 `rem`/`var(--text-body)` 等 token，隨根字級縮放。 |

---

## [A11Y-03] Color Blindness Mode

| 項目 | 說明 |
|------|------|
| **實作** | `frontend/src/app/globals.css`：`.color-blind-safe` 類別；套用於 `body` 時，綠/紅背景與文字輔以 outline 或 underline，避免僅以顏色傳達狀態。 |
| **使用** | 設定頁或全域偏好可提供「色盲友善模式」開關，為 `document.body` 加上 `color-blind-safe`。 |

---

## [A11Y-WCAG-01] WCAG 2.2 AA Checklist + Automated Checks

| 項目 | 說明 |
|------|------|
| **自動化** | `npm run test:a11y`（Playwright + @axe-core/playwright）；核心頁面（Home、Login、Register、Decks、Legal）執行 axe `wcag2a`、`wcag2aa`，無 critical violations 即通過。 |
| **P0/P1** | P0：登入/註冊/首頁/抽卡/日記核心流程可鍵盤操作、焦點可見、對比與文字可讀。P1：其餘頁面與元件逐步納入 axe 與手動檢查。 |
| **清單** | 對照 [WCAG 2.2 AA](https://www.w3.org/WAI/WCAG22/quickref/)：1.1 替代文字、1.3 可適應、1.4 可辨識、2.1 鍵盤可操作、2.4 可導覽、2.5 輸入模式、3.1 可讀、3.2 可預測、3.3 輸入協助、4.1 相容。 |

---

## 驗收

- **自動**：`cd frontend && npm run test:a11y`（需 E2E 環境）。
- **手動**：鍵盤 Tab 導覽、螢幕閱讀器（NVDA/VoiceOver）朗讀核心流程；開啟色盲友善模式檢查狀態辨識。
