# P2-A-7: 全站 UI/UX 可驗收清單

每頁最少要過：

- **一致 spacing**：使用 tokens（`--space-page`、`--space-section`、`--space-block`）或 Tailwind `space-page` / `gap-block`。
- **一致 typography**：標題用 `text-display`/`text-title`，內文 `text-body`，輔助 `text-caption`。
- **空狀態**：loading / empty / error 皆有對應 UI（skeleton、空狀態文案、error 區塊）。
- **互動回饋**：hover / focus-visible / pressed / disabled 皆有視覺區分。
- **A11y**：focus 可見、可鍵盤操作、aria 合理（至少核心流程）。

## 頁面對照

| 路徑 | spacing | typography | 空狀態 | 互動 | A11y |
|------|---------|------------|--------|------|------|
| /login | ✓ | ✓ | error ✓ | button disabled/loading | focus-visible, aria |
| /register | 同左 | 同左 | 同左 | 同左 | 同左 |
| / | tokens | ✓ | loading/empty | ✓ | ✓ |
| /decks | ✓ | ✓ | ✓ | ✓ | ✓ |
| /decks/[category] | ✓ | ✓ | ✓ | ✓ | ✓ |
| /settings | ✓ | ✓ | - | ✓ | ✓ |
| /analysis | ✓ | ✓ | - | ✓ | ✓ |
| /notifications | ✓ | ✓ | empty/error | ✓ | ✓ |
| /legal/terms | ✓ | ✓ | - | ✓ | ✓ |
| /legal/privacy | ✓ | ✓ | - | ✓ | ✓ |

逐頁 batch 時依此表補齊並打勾。P2-A 全站 UI/UX 優化已對齊本表；完成對照見 `docs/P2-A-VISUAL-POLISH-COMPLETE.md`。

**本批 (Settings / Analysis / Notifications)**：已套用 `space-page`、typography tokens（`text-title` / `text-body` / `text-caption`）、semantic 顏色（notifications 改為 bg-card / border-border / text-primary / text-destructive / accent）、loading/empty 之 `role="status"`、錯誤區塊 `role="alert"`、按鈕/連結 `focus-visible` 與 `aria-label`／`aria-hidden`。
