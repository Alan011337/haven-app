# Haven Art Direction & Token Contract (v1)

This document contains the strict contracts for Haven's UI aesthetic. These are not suggestions; they are exact specifications for `globals.css` and UI components.

## 1. Color Token Contract (Strict OKLCH)
*Use these exact OKLCH values in `globals.css`. Never use arbitrary values (e.g., `bg-[#...]` or `text-[oklch(...)]`) in component files.*

- **Surface Tokens**: 
  - `--background`: Light `0.985 0.005 80` / Dark `0.250 0.010 80`
  - `--card` / `--popover`: (Same as background, rely on shadows/borders for separation)
- **Brand/Accent Tokens**: 
  - `--primary`: Champagne Gold `0.750 0.080 65` (or Sage Green/Dusty Rose)
  - `--destructive`: Muted warm red (Avoid pure bright red `#FF0000`)
- **Text Tokens**: 
  - `--foreground`: Light `0.300 0.010 80` / Dark `0.920 0.010 80`
  - `--muted-foreground`: `0.650 0.010 80`
- **Border/Divider**:
  - `--border`: Alpha must not exceed 15% to avoid harsh lines.

## 2. Elevation & Shadow Contract (Max 3 Styles)
Define these strictly in your Tailwind config or CSS. Do not invent new shadows.
- `--shadow-soft`: For default cards/surfaces. Large, diffused, low opacity.
- `--shadow-lift`: For hover states. Slightly higher Y-offset and blur.
- `--shadow-modal`: For Dialogs/Drawers. Deep ambient shadow with primary color tint.

## 3. Typography Scale Contract
- **Headings (`--font-serif`)**: `Playfair Display` or `Instrument Serif`. 
  - `h1` / `h2` MUST use `tracking-tight`.
- **Body (`--font-sans`)**: `Inter` or `Geist`. Generous line-height (`leading-relaxed`).

## 4. White Space & Rhythm (The "Sacredness" Contract)
- **Space Tokens**: Define and use `--space-page`, `--space-section`, `--space-block` in `globals.css`.
- **Execution**: Provide generous padding around main content. Do not cram elements together. Maintain a clear "神聖感" (sacredness/elegance) through whitespace.

## 5. Component Recipes (Strict Execution)
When building these specific UI elements, use these exact class combinations:
- **Glass Panel (Cards/Sheets/Popovers)**: 
  `bg-background/40 backdrop-blur-2xl border border-foreground/10 shadow-soft`
- **Interactive Button (Primary)**:
  `bg-primary text-primary-foreground rounded-full hover:shadow-lift active:scale-95 transition-all duration-haven ease-haven`
- **Empty State**:
  Must include generous `--space-section` padding, muted text, and a soft CTA.

## 6. Motion Tokens
- `--ease-haven`: `cubic-bezier(0.32, 0.72, 0, 1)` (Apple spring). Never linear.
- `--duration-haven`: `240ms` or `300ms` max.

## 7. Golden Screens (Aesthetic Benchmarks)
When implementing or modifying these core screens, strict adherence to this document is mandatory to maintain the "Quiet Luxury" baseline:
- **Home / Dashboard**: Focus on spatial structuring (`--space-section`) and typography hierarchy.
- **Decks / Journal List**: Must use the `Glass Panel` recipe for all cards.
- **Settings**: Minimalist forms, soft inputs, clear labels (no boxy default shadcn inputs).
- **Dialogs / Sheets**: Must use `--shadow-modal` and backdrop blurs to isolate focus.

## 8. Exceptions (Documented Out-of-Contract Allowances)
The following are the only allowed exceptions to the "no arbitrary colors" and token-only rules. Do not add new exceptions without updating this section.

- **`frontend/src/app/global-error.tsx`**: This component is the Next.js App Router *global* error boundary. When the root layout or CSS pipeline is broken, Tailwind and `globals.css` may not load. To guarantee a minimal, readable fallback UI, this file is allowed to use **minimal inline hex colors** (e.g. background, border, text, button) so the page renders without any external styles. It must not import layout or theme-dependent components. Do not replicate this pattern elsewhere.

- **Focus ring on primary or dark backgrounds**: Interactive elements that sit on primary-colored or dark hero/header backgrounds (e.g. Home header tabs) need a high-contrast focus ring. Using **`focus-visible:ring-white/90`** (or a future `--focus-over-primary` token) for keyboard focus is allowed for those specific elements only. Elsewhere, use the standard `focus-visible:ring-ring` pattern.