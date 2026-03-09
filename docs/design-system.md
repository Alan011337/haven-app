# P2-L. Haven Design System

**目標**：Design Tokens 全平台同步、Motion System 標準曲線。

---

## [DS-01] Design Tokens

| 項目 | 說明 |
|------|------|
| **單一來源** | `frontend/src/app/globals.css`（`:root` 與 `@theme inline`）。 |
| **產物** | `npm run tokens:generate` 產生 `frontend/src/design-tokens.json`（顏色、間距、圓角、陰影、字級、動畫曲線與時長），供 RN、文件與跨平台同步。 |
| **結構** | W3C-style + Haven 分組：`color`、`radius`、`spacing`、`shadow`、`typography`、`motion`（ease、duration）、`font`。 |

---

## [DS-02] Motion System

| 項目 | 說明 |
|------|------|
| **曲線** | `globals.css`：`--ease-haven`（Apple-style ease-out）、`--ease-haven-spring`（ritual/reveal 輕微 overshoot）。 |
| **時長** | `--duration-haven-fast`（200ms）、`--duration-haven`（220ms）、`--duration-haven-slow`（320ms）、`--duration-haven-ritual`（500ms，翻牌/揭曉）。 |
| **使用** | Tailwind `duration-haven-fast`、`ease-haven-spring` 等；`design-tokens.json` 的 `motion.ease` / `motion.duration` 供 RN 或腳本使用。 |
| **減少動態** | `@media (prefers-reduced-motion: reduce)` 已將動畫與過渡縮短為 0.01ms，尊重系統偏好。 |
