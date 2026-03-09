# P2-A6 / P2-A7 Verification

## A6: Target Size (WCAG 2.5.8)

Key interactive targets verified ≥ 24×24 CSS px:

- **TarotCard**: Flip area = full card (h-32); prev/next buttons = 40×40 (min-w-[24px] min-h-[24px] + w-10 h-10).
- **DeckRoom**: Back / History = p-2 + icon w-6 h-6 → 40×40.
- **Settings**: Back button = padding + icon; toggles = h-5 w-5 checkbox with label (combined target).
- **Card ritual**: Submit / Next card buttons use Button component (min height from size prop).

## A7: Glow (可關閉)

- **Setting**: `useAppearanceStore.cardGlowEnabled`; toggle in Settings → 外觀.
- **Implementation**: TarotCard applies `glowClass` (shadow) only when `cardGlowEnabled`; no animated glow/breathing.
- **reduced-motion**: Glow is static shadow; no flash. When `useReducedMotion()` is true, flip uses crossfade (no 3D).
