# Migration Orchestration (Legacy + Fresh Bootstrap)

## Purpose
Provide deterministic migration flows for three environments:
- legacy DB with existing schema/data
- fresh local sqlite DB
- CI verification-only preflight

## Modes
`/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run-alembic.sh` supports:

1. `--mode legacy-upgrade` (default)
- Use for existing databases.
- Guard: blocks `upgrade head` on sqlite when legacy baseline is missing.

2. `--mode fresh-bootstrap`
- Use for brand-new sqlite databases only.
- Flow: run `scripts/bootstrap-sqlite-schema.py` then `alembic upgrade head`.
- Fails if target sqlite DB is non-empty.

3. `--mode verify-only`
- No migration execution.
- Runs preflight guard checks and exits.

## Recommended Commands

### Legacy database
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
./scripts/run-alembic.sh --mode legacy-upgrade upgrade head
```

### Fresh sqlite bootstrap + upgrade
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
DATABASE_URL=sqlite:///./test.db ./scripts/run-alembic.sh --mode fresh-bootstrap
```

### CI/local preflight only
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
./scripts/run-alembic.sh --mode verify-only
```

## Dry-run Checklist
1. Confirm `DATABASE_URL` target.
2. Run `--mode verify-only`.
3. Run `alembic current` (or `upgrade head` in target mode).

## Rollback
1. Code/script rollback:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
git restore /Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run-alembic.sh /Users/alanzeng/Desktop/Projects/Haven/docs/backend/MIGRATION_ORCHESTRATION.md
```
2. Schema rollback:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
./scripts/run-alembic.sh --mode legacy-upgrade downgrade -1
```

> For destructive revisions, use forward-fix instead of blind downgrade.
