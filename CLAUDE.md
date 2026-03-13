# Haven — Claude Code Project Instructions

## 0) Mission

Ship a stable, secure, high-quality product with premium UX and disciplined engineering execution.

Prioritize, in this order:

1. correctness
2. security
3. reliability
4. rollback safety
5. maintainability
6. UX clarity
7. premium design quality
8. speed

Do not optimize for cleverness.
Do not optimize for uncontrolled speed.
Do not optimize for visual novelty at the expense of product quality.

---

## 1) Authority and document order (non-negotiable)

Read and apply documents in this order:

1. `CLAUDE.md`
   - process law
   - security
   - batching
   - rollback
   - tests
   - observability
   - implementation discipline

2. `docs/design/ART-DIRECTION.md`
   - core Haven art direction
   - token law
   - premium-feel constraints
   - non-negotiable visual language

3. `docs/design/ART-DIRECTION-APPENDIX.md`
   - layout/composition guidance
   - golden screen laws
   - component recipes
   - review heuristics

4. `haven-ui.mdc`
   - frontend execution law
   - App Router rules
   - component layering
   - UI quality gate
   - anti-drift rules

### Conflict rule
- process / release / security / rollback conflicts → `CLAUDE.md` wins
- aesthetic / token / premium-feel conflicts → `ART-DIRECTION.md` wins
- screen-specific UI interpretation → `ART-DIRECTION-APPENDIX.md` clarifies
- frontend execution / architecture / component-layering rules → `haven-ui.mdc` wins

Do not ignore upstream documents.
Do not invent a new design system or process.

---

## 2) Core execution philosophy

### 2.1 Small, reviewable, reversible
Always prefer:
- one logical batch at a time
- explicit file scope
- low blast radius
- reversible changes
- clear test plan
- clear rollback path

Never prefer:
- sweeping refactors
- repo-wide aesthetic rewrites
- “cleanup while I’m here”
- hidden coupling changes
- silent behavior changes

### 2.2 Evidence-based execution only
Every recommendation or implementation must map to at least one of:
- specific file paths
- concrete diffs / edit instructions
- runnable commands
- tests
- docs
- runbooks
- migration steps

No vague advice.
No abstract praise.
No hand-wavy architecture commentary.

### 2.3 Product quality is multi-dimensional
A batch is not good merely because:
- it compiles
- it passes lint
- it looks cleaner

A good batch must also preserve or improve:
- correctness
- security
- user experience
- accessibility
- design consistency
- maintainability
- rollback safety

---

## 3) Non-negotiables (always true)

## 3.1 No destructive bulk changes
Unless explicitly requested, do NOT:
- perform repo-wide refactors
- mass rename/move files
- broad reformat unrelated code
- replace patterns across the entire codebase
- delete files you cannot prove are unused
- “simplify architecture” in a sweeping way

If a larger change is genuinely needed:
- propose a plan first
- split into multiple batches
- define blast radius
- define rollback rehearsal

---

## 3.2 Security and privacy first
Treat the following as sensitive by default:
- auth headers
- API keys
- tokens
- session IDs
- JWTs
- refresh tokens
- emails
- phone numbers
- addresses
- device identifiers
- user-generated private content
- relationship/journal content
- AI outputs containing user-sensitive reflections

Rules:
- never log secrets or PII
- redact sensitive values at source
- do not weaken auth/authz to make tests pass
- do not expose data you do not need

Any new or changed endpoint must include:
- authn verification
- authz verification
- BOLA-focused test thinking
- input validation
- failure-mode handling

---

## 3.3 Gate integrity
Do NOT:
- disable tests just to get green CI
- weaken security rules to reduce friction
- relax type safety without explanation
- silently remove guardrails
- alter acceptance criteria without calling it out

If expectations must change:
- explain the product requirement change
- explain user impact
- update code and tests together
- document risk and rollback

---

## 3.4 Production safety
When uncertain:
- prefer safe defaults
- add explicit failure paths
- add logs/metrics if appropriate
- reduce scope
- surface the unknown clearly

Never hide uncertainty behind confident implementation.

---

## 3.5 Maintainability over short-term hacks
Avoid:
- copy-paste sprawl
- ad-hoc one-off fixes that should become shared patterns
- UI hacks that bypass design tokens
- unnecessary dependencies
- code that future agents cannot reason about

If a shortcut is taken:
- state it explicitly
- contain the scope
- add a follow-up TODO if needed

---

## 3.6 Backward-compatible changes by default
Prefer:
- expand → migrate → contract
- dual-read / dual-write when semantics change
- guarded rollout
- forward-fix plans where rollback is risky

Avoid destructive DB or contract changes without:
- deprecation plan
- migration plan
- rollback or forward-fix plan
- runtime risk acknowledgment

---

## 4) Repo-first workflow (do not skip)

## Step 1 — Inventory first
Before proposing changes, produce a short repo map:
- relevant areas
- entrypoints
- critical paths
- files likely touched

If frontend/UI work:
- explicitly acknowledge which design docs were read

Required acknowledgement format:
- `Read: CLAUDE.md`
- `Read: docs/design/ART-DIRECTION.md`
- `Read: docs/design/ART-DIRECTION-APPENDIX.md` (if applicable)
- `Read: haven-ui.mdc` (if applicable)

Do not proceed without inventory.

---

## Step 2 — Top ROI TODOs only
Propose a maximum of 3 TODOs.

Each TODO must include:
- purpose
- user-visible outcome
- technical scope
- design/system impact if relevant
- Definition of Done

Do not dump a giant backlog.
Do not propose low-leverage tasks first.

---

## Step 3 — Implement one batch at a time
Implement ONE logical batch only.

After each batch:
- run relevant checks
- if a gate fails: stop, fix, re-run, then continue
- do not silently continue with failing checks

---

## Step 4 — Re-evaluate after each batch
After a batch:
- summarize what changed
- describe risk
- confirm checks run
- define next best batch
- avoid automatically chaining into unrelated edits

---

## 5) Required output format (every response)

Every response must follow this structure.

## 5.1 Inventory
- repo map (paths + one-line purpose)
- files to inspect
- files to touch
- document acknowledgements

## 5.2 Top 3 ROI TODO list
For each TODO include the DoD checklist below.

### Definition of Done (copy/paste and fill)
- ✅ Success criteria (user-visible / API-level)
  - exact manual verification steps
- ✅ Failure / fallback behavior
  - exact error behavior, retries, or graceful degradation
- ✅ Security & privacy
  - authn/authz implications
  - BOLA considerations where relevant
  - input validation / sensitive-data handling
- ✅ Observability
  - logs added/changed
  - metrics added/changed
  - how to verify locally
- ✅ Tests
  - unit tests
  - integration/e2e if applicable
  - exact commands
- ✅ Rollback
  - code rollback steps
  - DB rollback or forward-fix steps
  - feature-flag plan if relevant

## 5.3 Batch N
- summary
- exact paths changed
- risk assessment
  - blast radius
  - data risk
  - security risk
  - UX/design risk
- test plan
  - exact commands
  - expected outcomes
- rollback plan
  - exact code rollback steps
  - DB rollback / mitigation
- observability notes
  - logs
  - metrics
  - local verification method
- assumptions (max 3)
- open questions (max 3)
  - for each: what file/command would answer it

---

## 6) Frontend / UI batch addendum (mandatory for UI work)

If the batch touches any UI, frontend, design tokens, styles, layouts, components, forms, screens, loading states, or user-facing interaction surfaces, you MUST additionally apply this section.

## 6.1 UI-specific mission
Do not merely make the UI “cleaner.”
Move Haven toward:
- premium editorial minimalism
- warm emotional modernism
- restrained luxury
- calm, intimate usability
- non-generic product quality

The result must not drift toward:
- generic SaaS
- default shadcn
- over-boxed layouts
- decoration-heavy redesigns
- trendy but cheap visuals

---

## 6.2 Required UI document reads
For any UI-related batch, you must read:
- `docs/design/ART-DIRECTION.md`
- `haven-ui.mdc`

Also read `docs/design/ART-DIRECTION-APPENDIX.md` if touching:
- Home / Dashboard
- Decks
- Journal surfaces
- Settings
- Dialogs / Sheets
- forms
- layout shell
- shared component recipes
- spacing or composition changes

Acknowledge these reads explicitly.

---

## 6.3 UI Definition of Done (mandatory)
Every UI batch must include all of the following:

- ✅ Token compliance check
- ✅ No arbitrary colors/shadows/radii introduced
- ✅ Typography hierarchy verified
- ✅ Spacing rhythm reviewed
- ✅ Focus-visible path verified
- ✅ Labels / aria coverage verified
- ✅ Loading / empty / error states handled or preserved
- ✅ Responsive behavior checked
- ✅ Premium-feel blockers reduced
- ✅ Result still matches Haven art direction
- ✅ No regression toward default shadcn or generic SaaS

If any of these are weak or unknown, the batch is not done.

---

## 6.4 UI review rubric (must be evaluated)
Every UI batch must explicitly evaluate:

### Hierarchy
- Is there a clear primary focus?
- Is CTA hierarchy obvious?
- Is the page/surface easier to scan?

### Spacing rhythm
- Does spacing create calm and cadence?
- Are groups clear without over-fragmenting?
- Is anything cramped or visually box-stacked?

### Typography
- Are heading/body/label/caption/helper roles clearer?
- Does the screen feel more editorial and premium?
- Is metadata readable and not too tiny?

### Component consistency
- Do affected components still feel like one Haven family?
- Any drift in radius, border softness, shadow style, or state treatment?

### Emotional tone
- Does the result feel calmer, warmer, more premium, more intimate?
- Did the batch accidentally make things colder, louder, or more mechanical?

### Responsive quality
- Does it remain elegant across desktop/tablet/mobile?
- Any density or spacing breakdowns?

### Accessibility
- Keyboard path verified?
- Focus states verified?
- Labels and icon accessibility verified?

---

## 6.5 UI-specific verification output
If the batch is UI-related, include:

- screens/components touched
- premium-feel blockers addressed
- composition/layout changes made
- token/system changes made
- why the result is more aligned with Haven
- what visual anti-patterns were removed

If relevant, also include:
- before/after screenshot checklist
- affected states checklist (default/hover/active/focus/disabled/loading/error/empty)

---

## 6.6 Frontend architecture protections
For UI/frontend work, do not break:
- App Router structure
- server/client component boundaries
- TanStack Query vs Zustand responsibilities
- existing route segment loading/error handling
- type safety
- maintainability of shared UI primitives

UI polish must not damage architectural correctness.

---

## 7) Commands (use exact commands unless repo changes)

## 7.1 Backend
- Setup:
  - `cd backend && export PYTHONUTF8=1 PYTHONPATH=.`
- Lint:
  - `ruff check .`
- Tests:
  - `pytest`
- DB migrate:
  - `./scripts/run-alembic.sh upgrade head`
- Backend security gate:
  - `bash scripts/security-gate.sh`

## 7.2 Frontend
- `cd frontend`
- Lint:
  - `npm run lint`
- Tests:
  - `npm run test` (if present)
- Build:
  - `npm run build`

## 7.3 Local release gate
From repo root:
- `bash scripts/release-gate-local.sh`

Use repo-specific commands if they differ, but call out the difference explicitly.

---

## 8) How to think about risk

Every batch must consider these risk dimensions:

### 8.1 Blast radius
- How many files?
- Shared primitives or local feature only?
- Wide UI surface or narrow fix?

### 8.2 Data risk
- Data shape changes?
- Query behavior changes?
- Mutation behavior changes?
- State consistency risks?

### 8.3 Security risk
- auth/authz changes?
- sensitive-data exposure risk?
- input handling changes?

### 8.4 UX risk
- interaction regressions?
- accessibility regressions?
- visual hierarchy regressions?
- premium-feel drift?

### 8.5 Rollback difficulty
- trivial revert?
- partial rollback needed?
- migration coupling?
- component dependency chain?

---

## 9) Observability rules

Add observability when it materially reduces uncertainty.

Do not add noisy useless logs.

When changing important behavior, specify:
- log event names
- key fields
- redaction expectations
- metrics if relevant
- local verification method

Never log:
- secrets
- tokens
- raw private user content
- unnecessary sensitive payloads

---

## 10) UI system anti-drift rules

If touching design/system/frontend:
- do not bypass tokens for convenience
- do not introduce one-off visual hacks
- do not add arbitrary colors/shadows/radii
- do not add repeated patterns without systematizing them
- do not fall back to default shadcn styling
- do not use borders everywhere to create structure
- do not fake premium quality with blur, gradients, or heavy shadows alone

### Drift law
If a visual pattern appears more than once, it should probably become a shared Haven pattern.

---

## 11) When to stop and surface uncertainty

Stop and call out uncertainty when:
- you cannot determine ownership of a shared component
- a change may cross server/client boundaries unexpectedly
- you suspect a migration or contract change is needed
- a UI change may conflict with art direction or component family consistency
- a gate fails and cause is unclear
- required docs conflict

Do not guess silently.

---

## 12) Done means actually done

A batch is done only if all are true:

1. functionality works
2. relevant lint/build/tests pass
3. rollback path is explicit
4. security posture is preserved or improved
5. type safety is preserved or improved
6. UX/accessibility is preserved or improved
7. UI changes still match Haven art direction
8. the result does not regress toward generic SaaS or default shadcn
9. the batch is reviewable and scoped
10. the next step is clearly identified

Functional correctness alone is not enough.
Visual prettiness alone is not enough.
“Haven quality” requires both.

---

## 13) Where to look first

- Release gate:
  - `scripts/release-gate-local.sh`
  - `.github/workflows/release-gate.yml`
- Backend gate:
  - `backend/scripts/security-gate.sh`
- Launch docs:
  - `docs/P0-LAUNCH-GATE.md`
  - `docs/FINAL_P0_SIGNOFF.md`

### Single source of truth rule
If documentation conflicts with CI or release gates:
- CI / release gates win

Call out discrepancies explicitly in follow-up notes.

---

## 14) Final operating reminder

You are working on Haven, not a generic app.

That means:
- product decisions must feel intentional
- UI decisions must respect emotional tone
- engineering decisions must preserve safety and maintainability
- every batch must be small enough to trust
- every visible change must move the product forward, not just sideways

Prefer:
- clarity over cleverness
- restraint over decoration
- systems over hacks
- reversibility over speed
- calm premium quality over generic polish

If something is technically valid but emotionally wrong for Haven, it is wrong.
If something is visually appealing but systemically messy, it is wrong.
If something is fast to ship but hard to trust, it is wrong.