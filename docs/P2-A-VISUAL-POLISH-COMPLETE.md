# P2-A. 視覺藝術化 (Visual Polish) — 完成對照表

本文件對應「P2-A 視覺藝術化」開發清單，逐項對照實作狀態與檔案位置。所有項目均已實作並符合 DoD；可選擴充（Capacitor、音效資產）已註明。

---

## ✅ 八大牌組專屬視覺

### 卡背設計
- **DoD**：深度交流、性愛親密、日常共感等 8 牌組各有獨立色系/紋理/水印。
- **實作**：
  - **Single source**：`frontend/src/lib/deck-meta.ts` — `DECK_META_MAP` 每 deck 定義 `cardBack`（gradient、borderClass、glowClass、patternKey、watermarkIconKey）、`primaryColor` / `secondaryColor`。
  - **Primitives**：`frontend/src/components/haven/CardBackBase.tsx`（共用圓角/陰影）、`frontend/src/components/haven/CardBackVariant.tsx`（依 deck 渲染色系/紋理/水印）。
  - **紋理**：`globals.css` 內 `.pattern-card-dots` / `.pattern-card-lines` / `.pattern-card-grid`（CSS pattern）。
- **套用處**：牌組列表（decks 頁）、抽卡/揭牌（DeckRoomView、TarotCard）、回答頁、DeckHistorySummaryCard 等。
- **prefers-reduced-motion**：卡背不依賴動畫，靜態顯示無問題。

### 動畫特效（Framer Motion：Flip / Swipe / Glow）
- **DoD**：Flip 鍵盤替代、Swipe 有左右按鈕、Glow 可關閉、prefers-reduced-motion 降級。
- **實作**：
  - **LazyMotion + m**：`frontend/src/components/features/card-ritual/MotionProvider.tsx`；`TarotCard.tsx` 使用 `m`、`useReducedMotion`（翻轉改淡入/縮放）。
  - **Flip**：TarotCard 3D flip，Enter/Space 觸發；**Swipe 替代**：`onPrev` / `onNext` 按鈕（min 24×24px）。
  - **Glow**：解鎖發光由 `useAppearanceStore.cardGlowEnabled` 控制；設定頁可關閉。
  - **Ritual 長時動畫**：TarotCard duration-700、panel enter 等已註明為刻意「儀式感」例外，不納入 micro-motion token。
- **Bundle**：僅 card-ritual 範圍使用 framer-motion，未全站擴散。

---

## ✅ 情緒背景漸變 (Dynamic Background)

- **DoD**：mood_label → 背景色；無 mood → default；一鍵關閉；不影響可讀性（overlay 可選）。
- **實作**：
  - **MOOD_THEME_MAP**：`frontend/src/lib/mood-background.ts` — 平靜/快樂/憂鬱/熱烈等中英文 key → `bgGradient`、`overlayOpacity`。
  - **單一套用點**：`frontend/src/components/system/DynamicBackgroundWrapper.tsx`（layout 內）；`getThemeForMood(latestMoodLabel)`。
  - **Feature flag**：`NEXT_PUBLIC_DYNAMIC_BG_ENABLED` + 後端 `dynamic_background_enabled`；兩者皆開且有 `latestMoodLabel` 才啟用。
  - **Overlay**：`overlayOpacity > 0` 時加透明層保對比。
- **Mood 來源**：首頁「我的」最新一則日記的 `mood_label` 寫入 `useAppearanceStore.setLatestMoodLabel`。

---

## ✅ 質感 UI 全面升級 (Glassmorphism)

- **DoD**：Glass 僅從 primitives 進入；可 flag 切回；留白與慢互動。
- **實作**：
  - **Primitives**：`GlassCard`、`GlassPanel`、`GlassModal`（`frontend/src/components/haven/`）；blur 為 token（`--glass-blur-1/2/3`，`globals.css`）。
  - **全面 rollout（A10+）**：已於全站完成逐頁/逐區塊替換，包含：首頁、decks、decks/history、settings、analysis、notifications、login、register、legal/terms、legal/privacy、loading/error/not-found、DeckRoom、PartnerSettings、PartnerTab、JournalCard 等；無散落 ad-hoc blur class。
  - **切回**：各處可改 `GlassCard variant="solid"` 或還原為一般 Card/div。
- **留白與慢互動**：`ART-DIRECTION.md` 與 `globals.css` 定義 `--space-page`、`--space-section`、`--space-block`；動效使用 `duration-haven` / `ease-haven`，強調神聖感與節奏。

---

## ✅ Haptic Feedback (觸覺回饋)

- **DoD**：揭牌、提交成功、解鎖時輕微震動；可設定開關；行動端體驗。
- **實作**：
  - **API 層**：`frontend/src/services/hapticsService.ts` — `trigger('draw'|'unlock'|'tap', options)`；Web 使用 `navigator.vibrate`，不支援時 no-op 不拋錯。
  - **整合**：`frontend/src/lib/feedback.ts` 之 `feedback.onDrawSuccess` / `onUnlockSuccess` / `onTap` 呼叫 hapticsService；`useDeckRoom`、`DailyCard` 傳入 `hapticsEnabled`、`hapticStrength`。
  - **設定**：`useAppearanceStore` — `hapticsEnabled`、`hapticStrength`（light/medium）；設定頁可開關。
- **Capacitor（可選）**：目前專案未納入 Capacitor；日後若建置原生 app，可在 `hapticsService` 內改為 `import { Haptics } from '@capacitor/haptics'` 並依平台分支，無需改呼叫端。

---

## ✅ 音效系統 (Audio Branding)

- **DoD**：抽卡輕微紙張聲、解鎖空靈鈴聲；可 mute；連發保護；不影響首屏。
- **實作**：
  - **抽卡**：`frontend/src/lib/feedback.ts` — `playDrawSound()`（Web Audio API 正弦掃頻，模擬紙張感）；`feedback.onDrawSuccess` 內依 `soundEnabled` 與 cooldown 觸發。
  - **解鎖**：`playUnlockSound()`（短促和絃）；`feedback.onUnlockSuccess` 內同樣受 `soundEnabled` 與 cooldown 控制。
  - **Mute**：`useAppearanceStore.soundEnabled`；設定頁「音效（抽卡／解鎖）」開關。
  - **Cooldown**：`COOLDOWN_DRAW_MS` / `COOLDOWN_UNLOCK_MS`，避免連發。
  - **延遲載入**：AudioContext 首次呼叫時建立，不阻塞首屏。
- **可選**：日後可於 `/public/audio/v1/` 放置 draw.mp3、unlock.mp3，在 `playDrawSound` / `playUnlockSound` 內優先載入資產， fallback 現有 procedural 音效。

---

## ✅ 優化所有前端頁面的 UI/UX（精品感、精緻感、高級感）

- **DoD（每頁）**：一致 spacing、一致 typography、空狀態完整、互動回饋、A11y。
- **對照**：見 `docs/P2-UI-UX-DoD.md` 頁面對照表；核心頁（/、/login、/register、/decks、/decks/[category]、/decks/history、/settings、/analysis、/notifications、/legal/*）已套用：
  - **Spacing**：`space-page`、`space-section`、`gap-block` 等 token。
  - **Typography**：`text-title`、`text-body`、`text-caption`、`font-art` 語意。
  - **空狀態**：loading skeleton、empty 文案、error `role="alert"`。
  - **互動**：hover / focus-visible / disabled 視覺；按鈕/連結 focus-visible ring。
  - **A11y**：鍵盤可操作、aria-label/aria-labelledby、tab 手動啟動、目標 24×24px 等（見 P2-K axe gate）。

---

## 總結

| 清單項目 | 狀態 | 主要檔案/備註 |
|----------|------|----------------|
| 八大牌組卡背 | ✅ | deck-meta.ts, CardBackBase, CardBackVariant |
| 八大牌組動畫 (Flip/Swipe/Glow) | ✅ | MotionProvider, TarotCard, useAppearanceStore.cardGlowEnabled |
| 情緒背景漸變 | ✅ | mood-background.ts, DynamicBackgroundWrapper |
| Glassmorphism | ✅ | GlassCard/GlassPanel/GlassModal, 全站 A10+ rollout |
| Haptic Feedback | ✅ | hapticsService, feedback, 設定開關；Capacitor 可選 |
| 音效系統 | ✅ | feedback.ts playDrawSound/playUnlockSound, mute+cooldown |
| 全站 UI/UX 精品化 | ✅ | P2-UI-UX-DoD 對照；tokens + 留白 + 動效一致 |

**Rollback**：各項均為多個 commit 或單一模組，可依功能 revert 對應 commit 或關閉 feature flag（動態背景、Glow、音效、觸覺）。
