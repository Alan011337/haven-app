# Canary + Rollback Policy (P1-A)

## Rollout Strategy
- Progressive rollout: `1% -> 5% -> 25% -> 50% -> 100%`.
- Each stage requires health checks to remain within SLO guardrails.
- New features must be behind feature flags by default.

## Automation Hooks
- Guard runner: `backend/scripts/run_canary_guard.py`
- Wrapper: `scripts/canary-guard.sh`
- Workflow: `.github/workflows/canary-guard.yml`

## Auto Rollback Conditions
- Burn-rate gate degraded in canary observation window.
- WS arrival SLI degradation beyond threshold.
- CUJ runtime SLI degraded (`/health/slo` reason includes `cuj_sli_degraded`).
- Critical error rate spike tied to canary cohort.

## Rollback Actions
1. Disable feature flag (preferred, fastest).
2. Trigger rollback hook (if deployment supports traffic split revert).
3. Announce in incident channel and create postmortem record.

## Verification Checklist
- Confirm rollback signal from metrics.
- Confirm no residual write-side corruption.
- Confirm user-visible fallback path active.

## Production Connection (REL-GATE-02)
To connect canary rollout/rollback in production:
1. **Env**: Set `CANARY_HEALTH_URL` to the production `/health/slo` (or staging) URL used by the guard. Set `CANARY_COHORT_LABEL` if traffic split is cohort-based.
2. **Workflow**: `.github/workflows/canary-guard.yml` runs the guard script; ensure the repo has access to the deployment environment (e.g. GitHub env secrets for prod URL).
3. **Rollout hook**: Integrate `scripts/canary-guard.sh` or `backend/scripts/run_canary_guard.py` with your deploy pipeline (e.g. after 1% traffic) so that each stage (1% → 100%) is gated on guard pass. Use `--dry-run-hooks` in CI when prod URL is not available.
4. **Rollback hook**: On guard failure (burn-rate or SLO breach), trigger your platform’s rollback (e.g. revert traffic split, disable feature flag). Document the exact rollback command or API in RUNBOOK.md.
5. **Allow missing**: For PRs/forks without prod, use `--allow-missing-health-url` so the workflow does not fail; require real health URL only on main/protected branches.
