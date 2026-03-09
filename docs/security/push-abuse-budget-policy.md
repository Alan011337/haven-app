# Push Abuse Budget Policy (P1-C)

Last updated: 2026-02-23

## Scope

- Web Push subscription registration and cleanup lifecycle.
- Push dry-run sampling path (pre-dispatch health check).
- Push SLI gate inputs for release decisions.

## Baseline Budgets (Current Defaults)

- `PUSH_MAX_SUBSCRIPTIONS_PER_USER=10`
- `PUSH_DEFAULT_TTL_SECONDS=3600`
- `PUSH_DRY_RUN_SAMPLE_SIZE=3`
- `PUSH_INVALID_RETENTION_DAYS=7`
- `PUSH_TOMBSTONE_PURGE_DAYS=30`
- `PUSH_JWT_MAX_EXP_SECONDS=86400`

## Push SLI Targets (Release Gate Inputs)

- `HEALTH_PUSH_DELIVERY_RATE_TARGET=0.98`
- `HEALTH_PUSH_DISPATCH_P95_MS_TARGET=2500`
- `HEALTH_PUSH_DRY_RUN_P95_MS_TARGET=1200`
- `HEALTH_PUSH_SLI_MIN_DISPATCH_ATTEMPTS=5`
- `HEALTH_PUSH_SLI_MIN_DRY_RUN_SAMPLES=3`
- `HEALTH_PUSH_STALE_CLEANUP_BACKLOG_MAX=20`

## Guardrail Invariants (CI Enforced)

- All push budget and retention values must be positive.
- `PUSH_MAX_SUBSCRIPTIONS_PER_USER <= 25`
- `PUSH_DRY_RUN_SAMPLE_SIZE <= 20`
- `PUSH_DEFAULT_TTL_SECONDS <= PUSH_JWT_MAX_EXP_SECONDS`
- `PUSH_TOMBSTONE_PURGE_DAYS >= PUSH_INVALID_RETENTION_DAYS`
- `0.9 <= HEALTH_PUSH_DELIVERY_RATE_TARGET <= 1.0`
- latency targets must be positive
- `HEALTH_PUSH_STALE_CLEANUP_BACKLOG_MAX >= 0`

## Verification

- `cd /Users/alanzeng/Desktop/Projects/Haven/backend && PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider tests/test_push_abuse_budget_policy.py`
- `cd /Users/alanzeng/Desktop/Projects/Haven/backend && PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider tests/test_push_sli_runtime.py`
- `cd /Users/alanzeng/Desktop/Projects/Haven/backend && bash scripts/security-gate.sh`

## Rollback Rule

If push gates produce false positives, temporarily keep release gate in monitor-only mode (`SLO_GATE_REQUIRE_SUFFICIENT_DATA=false`) and adjust one bound at a time with a follow-up postmortem task.
