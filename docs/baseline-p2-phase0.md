# P2 Phase 0 Baseline Record

Run date: 2026-02-25 (execution phase).

## Frontend (npm)

| Step | Command | Exit code | Notes |
|------|---------|-----------|--------|
| install | `cd frontend && npm ci` | 0 | 434 packages; 1 high severity vulnerability (run npm audit) |
| lint | `npm run lint` | 0 | eslint + console-error guard + route-collision guard OK |
| typecheck | `npm run typecheck` | 0 | next typegen + tsc OK |
| build | `npm run build` | 0 | Next.js 16.1.6 webpack build OK |

## Backend (pip / venv)

| Step | Command | Exit code | Notes |
|------|---------|-----------|--------|
| install | `venv/bin/python -m pip install -r requirements.txt` | 0 | (pip not in PATH; used venv) |
| ruff | `ruff check .` | N/A | ruff not in backend requirements; skipped |
| pytest | `venv/bin/python -m pytest -q` | (long run) | Run separately to confirm |
| alembic | `venv/bin/python -m alembic current` / `history` | (async) | Run separately to confirm |

## Summary

- Frontend: lint, typecheck, build all pass. 1 npm audit high severity remains (do not fix in this batch per Hard Rules).
- Backend: install OK; ruff not in repo requirements; pytest/alembic to be verified locally.
