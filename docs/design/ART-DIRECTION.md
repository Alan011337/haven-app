# Haven Art Direction & Token Contract

This document defines the core non-negotiable art direction and token rules for Haven.
This is the primary UI aesthetic law for all Haven frontend work.

If a design decision conflicts with this document, this document wins.

---

## 0. What Haven Is

Haven is **not**:
- a generic productivity SaaS
- a fintech dashboard
- a harsh clinical wellness app
- a boxy admin panel
- a trendy but cheap startup UI
- a noisy feature-dump interface

Haven **is**:
- intimate
- emotionally safe
- elegant
- premium
- calm
- refined
- editorial
- warm
- minimal but never sterile
- luxurious but restrained

### Emotional Keywords
Use these as the constant design filter:
- intimate
- gentle
- sacred
- emotionally intelligent
- quiet luxury
- soft confidence
- warmth without sentimentality
- clarity without harshness
- premium restraint
- human depth

### Anti-Feeling Keywords
Haven must never feel:
- loud
- cheap
- overly shiny
- corporate
- generic
- cold
- mechanical
- cluttered
- toy-like
- template-driven
- tacky
- over-decorated
- default shadcn

---

## 1. Core Visual Language

Haven follows:
- premium editorial minimalism
- warm emotional modernism
- soft material depth
- restrained luxury
- calm interaction design

### Visual Priorities
When tradeoffs happen, prioritize in this order:
1. clarity
2. emotional tone
3. hierarchy
4. restraint
5. consistency
6. polish
7. novelty

Do not sacrifice clarity and emotional tone for visual cleverness.

---

## 2. Color Token Contract (Strict OKLCH)

Use these exact OKLCH values in `globals.css`.
Never use arbitrary values in components unless explicitly allowed in Exceptions.

### Surface Tokens
- `--background`
  - Light: `0.985 0.005 80`
  - Dark: `0.250 0.010 80`

- `--card`
  - Same family as background; separation should come mainly from elevation, blur, subtle tint, and spacing.

- `--popover`
  - Same family as card; slightly more isolated via shadow and material treatment.

### Text Tokens
- `--foreground`
  - Light: `0.300 0.010 80`
  - Dark: `0.920 0.010 80`

- `--muted-foreground`
  - `0.650 0.010 80`

### Brand / Accent Tokens
- `--primary`
  - Champagne Gold: `0.750 0.080 65`
  - Alternate families such as Sage Green or Dusty Rose must be documented and systematic.

### Functional Tokens
- `--destructive`
  - Muted warm red only
  - Never bright alarm red like `#FF0000`

### Border / Divider
- `--border`
  - Alpha must not exceed 15%
  - Borders are supporting actors, never primary structure

### Border Rule
If a layout needs many visible borders to work, the layout is probably too weak.

---

## 3. Typography Contract

Typography is a major source of Haven’s premium feel.
It must never feel like default web app typography.

### Font Roles
- **Display / Heading (`--font-serif`)**
  - `Playfair Display` or `Instrument Serif`

- **Body / Interface (`--font-sans`)**
  - `Inter` or `Geist`

### Mandatory Hierarchy
At minimum, define and consistently use:
- `display`
- `h1`
- `h2`
- `h3`
- `section-title`
- `body`
- `body-muted`
- `label`
- `caption`
- `micro`

### Rules
- `h1` and `h2` MUST use `tracking-tight`
- body text must use generous line-height
- labels must be clearly distinguishable from body copy
- helper/caption text must be quiet, but readable
- avoid all-caps unless absolutely necessary
- avoid tiny, low-contrast metadata clusters

---

## 4. Spacing & Rhythm Contract

Whitespace is how Haven creates sacredness, calm, and premium restraint.

### Required Space Tokens
Define and use:
- `--space-page`
- `--space-section`
- `--space-block`
- `--space-stack`
- `--space-inline`

### Rules
- main content must have generous outer padding
- sections must not visually collapse into each other
- related items should cluster; unrelated items should breathe apart
- do not solve hierarchy only with borders or font weight
- prefer fewer, clearer groups over many small stacked containers

### Rhythm Rule
A page should feel like it has cadence, not just padding.

---

## 5. Elevation & Shadow Contract

Do not invent new shadow styles ad hoc.

### Allowed Shadows
- `--shadow-soft`
  - default surfaces
  - large, diffused, low-opacity

- `--shadow-lift`
  - hover/focus lift states
  - slightly stronger than soft, still restrained

- `--shadow-modal`
  - dialogs / drawers / overlays
  - deeper ambient shadow with subtle tint if appropriate

### Shadow Philosophy
Shadows should feel:
- ambient
- soft
- expensive
- quiet

Shadows should never feel:
- harsh
- crunchy
- dramatic
- effect-y

---

## 6. Radius & Geometry Contract

Haven should feel soft and refined, not sharp and boxy.

### Rules
- use generous radii
- keep radius hierarchy consistent
- use `rounded-full` only intentionally
- do not mix many unrelated radii
- cards, inputs, sheets, dialogs, and buttons must feel like one family

---

## 7. Motion Contract

Motion reinforces softness, tactility, clarity, and confidence.

### Motion Tokens
- `--ease-haven`: `cubic-bezier(0.32, 0.72, 0, 1)`
- `--duration-haven`: `240ms` or `300ms` max

### Motion Rules
- prefer opacity / translate / slight scale
- hover = gentle lift
- active = subtle press
- dialogs/sheets should enter with softness and confidence
- avoid motion fatigue
- never use flashy motion to compensate for weak design

---

## 8. Forbidden UI Patterns

Do NOT ship these unless explicitly approved:
- harsh dark 1px borders everywhere
- card inside card inside card
- thick boxed sections across the whole screen
- equal visual weight for all blocks
- excessive badge usage
- overuse of blur/glass everywhere
- over-saturated gradients
- generic startup SaaS hero styling
- dense dashboard tiles with little breathing room
- giant blocky default inputs
- CTA overload
- noisy shadows
- overpacked headers
- low-contrast tiny metadata walls

If a screen feels “clean” but also “generic,” it is still wrong.

---

## 9. Token Integrity Rules

- Never use arbitrary color values in components
- Never use arbitrary shadow values in components
- Never use hardcoded radii in components
- Promote repeated visual decisions into tokens first
- `globals.css` and the theme layer are the source of truth

### Integrity Principle
Consistency creates luxury.
Ad hoc styling destroys it.

---

## 10. Exceptions

### `frontend/src/app/global-error.tsx`
This file may use minimal inline hex colors because it must render even when the root layout or CSS pipeline is broken.
Do not replicate this elsewhere.

### Focus Ring on Primary / Dark Backgrounds
For elements on primary or dark hero/header backgrounds, high-contrast focus rings may use:
- `focus-visible:ring-white/90`

Elsewhere, use the normal semantic ring token.

---

## 11. Appendix Reference

For detailed guidance on:
- layout and composition
- component recipes
- golden screen rules
- screen-specific design laws

Read:
- `docs/design/ART-DIRECTION-APPENDIX.md`

This main file defines the always-on design law.
The appendix provides situational guidance.