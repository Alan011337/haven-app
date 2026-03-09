# Backend Optimization Baseline (2026-03-01)

## Scope
- Branch: `p2-sprint1-polish`
- Baseline policy: work on top of current dirty worktree (no reset/revert of unrelated changes).
- Optimization program: stability + availability first, then API/data consistency, then code quality.

## Snapshot
- Backend gate script: `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/security-gate.sh`
- Last observed status: pass (`769 passed, 1 warning, 32 subtests passed`).
- API inventory entries: `102` (`/Users/alanzeng/Desktop/Projects/Haven/docs/security/api-inventory.json`)
- Alembic revisions in repo: `44` (`/Users/alanzeng/Desktop/Projects/Haven/backend/alembic/versions`)

## Current Known Risks
1. Runtime wrapper/path fragility:
   - Some virtualenv wrappers still reference old absolute paths in local environments.
2. Migration path complexity:
   - Fresh sqlite and legacy schema paths require explicit bootstrap/guard flow.
3. Local gate stall points:
   - Frontend and mobile typecheck can hang in some environments; release gate supports skip toggles for local debugging.
4. Backend lint debt:
   - `ruff` reported ~208 issues before this optimization wave; includes correctness issues (`F821/F841`).

## Baseline Verification Commands
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
bash /Users/alanzeng/Desktop/Projects/Haven/backend/scripts/security-gate.sh

cd /Users/alanzeng/Desktop/Projects/Haven/backend
ruff check . --select F821,F841,E9 --output-format concise
```

## Rollback Convention
- All changes in this optimization wave are rollbackable by commit-level revert.
- For migration-related changes:
  - provide explicit downgrade revision in each batch doc,
  - provide dry-run command before applying upgrade.

## Notes
- This file is the anchor artifact for all backend optimization batches in this wave.
- Each batch must reference this baseline and record:
  - changed files,
  - verification commands,
  - rollback steps.
