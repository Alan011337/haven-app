# Local Dev Runtime

## Goal

Keep localhost stable and reproducible on one explicit database mode:
local Postgres. Normal development must not point at the constrained remote
Supabase session-mode pooler, and sqlite is no longer the canonical localhost
runtime.

## Source of truth

- Tracked localhost runtime defaults:
  - `/Users/alanzeng/projects/Haven-local/config/local-dev-runtime.env`
- Backend secrets and production-like defaults:
  - `/Users/alanzeng/projects/Haven-local/backend/.env`
- Frontend secrets and remote storage keys:
  - `/Users/alanzeng/projects/Haven-local/frontend/.env.local`

The local runtime scripts intentionally override only the localhost-sensitive
values:

- `DATABASE_URL` → local Postgres on `127.0.0.1:55432`
- `NEXT_PUBLIC_API_URL` → `http://127.0.0.1:8000/api`
- `NEXT_PUBLIC_WS_URL` → `ws://127.0.0.1:8000`

Remote Supabase storage keys stay remote in localhost development so journal
attachment contracts remain aligned with staging / production.

## Requirements

- Docker Compose is required for the canonical localhost database runtime.
- The checked-in compose file is:
  `/Users/alanzeng/projects/Haven-local/config/local-dev-postgres.compose.yml`

## Canonical localhost flow

### Clean stop

```bash
bash scripts/local-runtime-stop.sh
```

### Prepare local dev DB

```bash
bash scripts/local-dev-db.sh start
```

### Apply migrations

```bash
bash scripts/local-dev-db.sh migrate
```

For a brand-new empty local Postgres DB, this canonical path bootstraps the
current schema from metadata, stamps Alembic head, and then verifies with
`upgrade head`. For an existing local Postgres DB, it continues through the
normal Alembic upgrade path.

### Start backend

```bash
bash scripts/local-runtime-backend.sh
```

### Start frontend

```bash
bash scripts/local-runtime-frontend.sh
```

### Verify runtime

```bash
bash scripts/local-runtime-verify.sh
```

### Reset local dev DB

```bash
bash scripts/local-dev-db.sh reset
```

## Why local Postgres for localhost

- Postgres is materially closer to staging / production Supabase than sqlite:
  dialect behavior, transaction semantics, constraint/index behavior, and
  Alembic migration parity all line up better.
- Remote Supabase from localhost is intentionally not canonical because it adds
  remote network/pooler instability and shared-state ambiguity to normal dev.
- Canonical localhost now uses checked-in Docker Compose with an explicit local
  Postgres connection contract.

## Architecture reality check

- **Canonical localhost DB mode**: local Postgres only.
- **Staging / preview / production DB mode**: remote Supabase / Postgres.
- **Remote Supabase from localhost**: intentionally not canonical because it
  depends on the pooler, network, and shared remote state.
- **Sqlite**: retained only for tests, migration rehearsal, and auxiliary
  scripts. It is no longer the official localhost runtime.

## Migration alignment across environments

- Localhost continues to run the same Alembic revision chain as staging /
  production.
- PostgreSQL-only migrations already use dialect guards where needed, but the
  canonical developer runtime is now the Postgres path instead of sqlite.
- `bash scripts/local-dev-db.sh migrate` is the expected localhost migration
  entrypoint.
- Empty localhost Postgres bootstrap is explicit and local-only; staging /
  production still use normal upgrade flow against existing databases.
- What stays intentionally remote in localhost:
  - Supabase storage / attachment bucket credentials
  - any other non-DB secrets sourced from `backend/.env` / `frontend/.env.local`

## Scope boundaries

- Localhost DB is local Postgres only.
- Staging / preview / production continue using remote Postgres / Supabase.
- Sqlite remains available only for tests / auxiliary scripts / migration drills.
- This batch does not change API contracts, auth behavior, or product UX.
