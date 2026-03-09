# Backend Perf Baseline

This baseline is a synthetic CUJ-oriented guard for backend regressions.

## Probes

- `auth_verify`: password verification path (`verify_password`)
- `journal_write`: journal write + commit
- `card_write`: card response write + commit
- `timeline_query`: unified memory timeline query (`get_unified_timeline`)

## Run

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_perf_baseline.py \
  --iterations 30 \
  --fail-on-budget-breach \
  --output /tmp/backend-perf-baseline.json
```

## Default P95 Budgets

- `auth_verify`: `120ms`
- `journal_write`: `250ms`
- `card_write`: `250ms`
- `timeline_query`: `300ms`

## Output Contract

`schema_version=v1` with:

- `budgets_p95_ms`
- `results.<probe>.p50_ms/p95_ms/p99_ms`
- `evaluation.<probe>`
- `status` + `failures`

## Rollback

If baseline starts failing after a change:

1. Re-run with same iterations to confirm signal stability.
2. Compare query-path changes first (`memory_archive`, timeline indexes).
3. Revert the suspect change or lower rollout via feature flag.
