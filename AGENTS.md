# Haven — Codex Project Instructions (Optimized)

## 0) Goal
Ship a stable, compliant MVP.
Prioritize correctness, security, reliability, and clear rollback over speed or clever refactors.

## 1) Non-negotiables (Always true)

### 1.1 No vague advice (evidence-based only)
Every suggestion MUST map to at least one of the following:
- specific file paths
- concrete diffs/patches (or explicit edit instructions)
- runnable artifacts (tests / scripts / config / docs / runbook)

### 1.2 Small-step batches (reviewable diffs)
- ONE logical change per batch (keep diffs reviewable)
- Each batch response MUST include:
  - Summary
  - Risk assessment
  - Test plan (exact commands + expected outcomes)
  - Rollback plan (exact steps)
  - Observability notes (what logs/metrics changed, and how to verify)

### 1.3 No destructive bulk changes
Unless explicitly requested, DO NOT:
- do repo-wide refactors (mass renames/moves, sweeping “cleanup”, broad reformatting)
- delete files/dirs you can’t prove are unused
- “simplify architecture” or change patterns across the codebase
If a large change is needed:
- propose a plan first
- split into multiple batches
- include a rollback rehearsal plan

### 1.4 Security & privacy (default: least privilege, least data)
- Never log/trace secrets or PII. Always redact at source.
- Treat as sensitive by default:
  - auth headers, tokens, API keys, session IDs, JWTs, refresh tokens
  - emails, phone numbers, addresses, device identifiers
  - user-generated content unless explicitly designated non-sensitive
- Any new/changed endpoint MUST include:
  - authentication (authn) + authorization (authz) checks
  - authz tests with BOLA focus (object-level authorization)
- Do not weaken security posture to “make tests pass.”

### 1.5 Gate integrity (do not cheat)
- Do NOT disable/relax security gates, remove tests, or “adjust” tests purely to make CI green.
- If a test expectation MUST change:
  - explain the requirement change and user impact
  - update tests + code together
  - call out risk and rollback

### 1.6 Production safety
- Prefer guardrails + graceful degradation.
- If uncertain:
  - add safe defaults
  - add explicit failure modes
  - add observability (logs/metrics)
  - stop and surface the unknown (see §4 Output format)

### 1.7 Database migration safety (backward compatible by default)
- Prefer backward-compatible schema changes (expand → migrate → contract / parallel change).
- Avoid destructive changes (drop/rename columns, change semantics) without:
  - deprecation plan
  - backfill plan
  - dual-write / dual-read strategy where needed
  - observability to confirm rollout
  - explicit rollback steps
- Any migration must document:
  - whether it is reversible
  - what to do if it fails mid-way
  - expected runtime/locks and mitigation if relevant

## 2) Standard workflow (Do not skip)

### Step 1 — Inventory first
Produce a short repo map:
- areas touched
- key files to inspect
- entrypoints/critical paths involved

### Step 2 — Propose prioritized TODOs (top ROI only)
- Maximum 3 TODOs
- Each TODO MUST include a Definition of Done (DoD) using this exact checklist:

**DoD checklist (copy/paste)**
- ✅ Success criteria (user-visible / API-level):  
  - How to verify manually (exact steps, curl, UI steps)
- ✅ Failure / fallback behavior:  
  - What happens on error (status codes, error messages, retries, timeouts)
- ✅ Security & privacy:  
  - Authn/authz enforcement
  - BOLA test cases (at least 2: read + write)
  - Input validation and sensitive data handling
- ✅ Observability:  
  - New/changed log events (names/keys)
  - New/changed metrics (names/tags)
  - How to verify (grep query / local dashboard / log sample shape)
- ✅ Tests:  
  - Unit tests (what + exact commands)
  - Integration/e2e (what + exact commands) if applicable
- ✅ Rollback:  
  - Code rollback steps
  - DB rollback or forward-fix steps (explicit)
  - Feature flag strategy if used

### Step 3 — Implement batch-by-batch
- Implement ONE batch at a time.
- After each batch:
  - run the relevant checks (exact commands)
  - if any gate fails: STOP, fix, re-run, then continue

## 3) Commands (use exact commands unless repo changes)

### Backend
- Setup: `cd backend && export PYTHONUTF8=1 PYTHONPATH=.`
- Lint: `ruff check .` (or repo-configured linter)
- Tests: `pytest`
- DB migrate: `./scripts/run-alembic.sh upgrade head`
- Release gate: `bash scripts/security-gate.sh`

### Frontend
- `cd frontend`
- Lint: `npm run lint`
- Tests: `npm run test` (if present)
- Build: `npm run build`

### Local release gate (repo root)
- `bash scripts/release-gate-local.sh`

## 4) Output format (EVERY response, no exceptions)

### Inventory (paths)
- Repo map (paths + 1-line purpose)
- Files you will touch (explicit list)

### Top 3 ROI TODO list (each with DoD)
- TODO 1: (include DoD checklist)
- TODO 2: (include DoD checklist)
- TODO 3: (include DoD checklist)

### Batch N (ONE logical change)
- Diff summary (paths changed)
- Risk assessment
  - Blast radius
  - Data risk
  - Security risk
- Test plan
  - Commands (exact)
  - Expected outcome (exact)
- Rollback plan
  - Code rollback steps (exact)
  - DB rollback or mitigation (exact)
- Observability notes
  - Logs added/changed (event name, key fields)
  - Metrics added/changed (metric name, tags)
  - How to verify locally
- Assumptions (max 3)
- Open questions (max 3)
  - For each: what file(s)/command(s) would answer it

## 5) Where to look (keep this file short; details elsewhere)
- Release gate: `scripts/release-gate-local.sh`, `.github/workflows/release-gate.yml`
- Backend gate: `backend/scripts/security-gate.sh`
- Launch docs: `docs/P0-LAUNCH-GATE.md`, `docs/FINAL_P0_SIGNOFF.md`

**Single source of truth rule**
- If docs conflict with CI/release gates: CI/release gates win.
- Call out any discrepancy in “Batch N → Notes for follow-up”.