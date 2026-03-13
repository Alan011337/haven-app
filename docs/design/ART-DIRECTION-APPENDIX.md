# Haven Art Direction Appendix

This appendix extends `ART-DIRECTION.md` with deeper guidance for composition, component recipes, and screen-specific rules.

If there is any conflict:
- `ART-DIRECTION.md` wins
- this appendix clarifies, extends, and operationalizes the main rules

---

## 1. Layout & Composition Rules

Token compliance alone is not enough.
A page can use correct tokens and still feel generic if composition is weak.

### 1.1 Composition Philosophy
Haven layouts should feel:
- curated, not crowded
- calm, not empty
- structured, not boxed in
- premium, not oversized
- spacious, not vague

### 1.2 Max Width & Density
Every screen should have an intentional content width strategy.
Avoid full-width layouts with random cards everywhere.

Guidelines:
- reflective / emotionally dense content should use narrower reading widths
- operational / dashboard content may use broader widths
- do not let every page default to the same density

### 1.3 One Primary Focus Rule
Each screen must have one clear primary visual anchor.

Avoid:
- three equally loud panels
- too many competing CTA zones
- equal-weight card grids by default
- stacked surfaces with no focal hierarchy

### 1.4 Container Discipline
Not everything needs a card.

Use cards only when they provide:
- grouping
- containment
- material contrast
- focus isolation
- interaction clarity

Avoid:
- card-inside-card-inside-card
- wrapping every section in the same panel
- UI by rectangle

### 1.5 Section Structure
Each page section should contain:
- a clear purpose
- controlled hierarchy
- one dominant action or information goal
- enough breathing room before the next section

---

## 2. Form Composition Rules

Forms must feel elegant and emotionally safe.

Avoid:
- long boxy input stacks with no grouping
- harsh form density
- labels jammed too close to fields
- generic error styling
- destructive actions mixed into neutral controls

Use:
- grouped sections
- calm label rhythm
- soft helper text
- clear validation hierarchy
- enough space for reflection and confidence

### 2.1 Input Feel
Inputs and textareas must not look like default shadcn boxes.
They should feel:
- soft
- readable
- calm
- integrated into the Haven system

### 2.2 Validation Tone
Validation should feel:
- clear
- gentle
- trustworthy

Never:
- shout
- overuse bright red
- visually destabilize the form

---

## 3. List & Card Composition

Lists should feel graceful, not mechanically repetitive.

Avoid:
- overly tall dead space without hierarchy
- identical blocks with no emphasis
- thick borders around every list item
- excessive badges and metadata clutter

Use:
- spacing, typography, and soft separation first
- gentle emphasis for selected/focused states
- calm scanning rhythm

---

## 4. Component Recipes

These are baseline treatments, not excuses for indiscriminate reuse.

### 4.1 Glass Panel
Recommended baseline:

`bg-background/40 backdrop-blur-2xl border border-foreground/10 shadow-soft`

Rules:
- use only when material separation genuinely improves UX
- do not apply everywhere
- never let glass become the whole visual identity

### 4.2 Primary Interactive Button
Recommended baseline:

`bg-primary text-primary-foreground rounded-full hover:shadow-lift active:scale-95 transition-all duration-haven ease-haven`

Rules:
- should feel calm, premium, deliberate
- avoid oversized or overly bold CTA treatment unless truly needed

### 4.3 Input / Textarea
Rules:
- soft surface treatment
- elegant focus state
- comfortable vertical rhythm
- helper and validation text must feel integrated, not bolted on

### 4.4 Empty State
Rules:
- generous `--space-section` padding
- soft, supportive tone
- muted text with clear hierarchy
- CTA must feel inviting, not aggressive
- never look like an afterthought

### 4.5 Dialog / Sheet
Rules:
- use `--shadow-modal`
- backdrop blur should isolate attention, not show off
- spacing must feel luxurious
- hierarchy must be immediate
- destructive actions must be clearly separated

### 4.6 Section Header
Rules:
- should anchor rhythm
- heading, supporting text, and CTA must have hierarchy
- avoid dense title/subtitle/badge/tab/CTA clusters unless absolutely necessary

---

## 5. Golden Screen Laws

These screens are aesthetic benchmarks.

### 5.1 Home / Dashboard
Must feel:
- spacious
- intentional
- premium
- immediately legible
- emotionally inviting

Must prioritize:
- sectional rhythm
- hero hierarchy
- restrained CTA placement
- calm visual entry point

Must avoid:
- admin dashboard density
- equal-weight card grids everywhere
- loud metric-first framing unless truly needed

### 5.2 Decks / Journal List
Must feel:
- intimate
- collectible
- elegant
- calm to scan

Must prioritize:
- graceful list/card rhythm
- soft hierarchy
- meaningful spacing
- premium containment

Must avoid:
- repetitive generic cards
- border-heavy list layouts
- dense metadata clutter

### 5.3 Settings
Must feel:
- minimal
- clear
- soft
- trustworthy
- not technical or intimidating

Must prioritize:
- grouped form sections
- clear labels
- subdued helper text
- gentle separation

Must avoid:
- long raw stacks of inputs
- default shadcn form feel
- visually mixed destructive and neutral controls

### 5.4 Dialogs / Sheets
Must feel:
- focused
- calm
- elegant
- gently isolated

Must prioritize:
- clear hierarchy
- premium modal depth
- enough whitespace around actions
- thoughtful close/destructive affordances

Must avoid:
- cramped content
- too many equal-weight actions
- hard-edged default modal styling

---

## 6. Review Heuristics

Use these questions during UI review:

### 6.1 Premium Feel
- Does this feel crafted or assembled?
- Does this feel restrained or generic?
- Does this feel calm or busy?

### 6.2 Emotional Tone
- Does this feel emotionally safe?
- Does this feel warm without becoming sentimental?
- Does this feel intimate without being cluttered?

### 6.3 Hierarchy
- Is there one primary focus?
- Is the CTA hierarchy obvious?
- Does spacing create rhythm?

### 6.4 System Integrity
- Does this still feel like Haven?
- Are tokens, radii, shadows, spacing, and typography consistent?
- Did this accidentally slide back toward default shadcn or generic SaaS?

---

## 7. Implementation Reminder

Any engineer or AI coding agent modifying Haven UI should:

1. read `ART-DIRECTION.md` first
2. use this appendix only as deeper situational guidance
3. prefer restraint over decoration
4. preserve emotional warmth and premium clarity
5. treat whitespace, typography, and hierarchy as first-class design tools

If something feels technically valid but emotionally wrong for Haven, it is wrong.