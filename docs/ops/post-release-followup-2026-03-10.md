# Post-Release Follow-up 2026-03-10

## Release note
- Release branch: `main`
- Green GitHub workflow: `Release Gate`
- Successful run: `Align frontend e2e CI API base URL #15`
- Green release commit: `f0d7e25`
- Release proof record: [release-proof-2026-03-10.md](/Users/alanzeng/projects/Haven-local/docs/ops/release-proof-2026-03-10.md)

## Production monitoring window
- Window (UTC): `2026-03-10T01:36:02Z` to `2026-03-10T02:08:11Z`
- Window (Asia/Taipei): `2026-03-10 09:36:02` to `2026-03-10 10:08:11`
- Scope:
  - `https://haven-api-prod.fly.dev/health`
  - `https://haven-api-prod.fly.dev/health/slo`
  - `HOME=/tmp /tmp/flybin/flyctl checks list --app haven-api-prod`

| Sample | Timestamp (UTC) | `/health` | `/health/slo` | Fly service check |
| --- | --- | --- | --- | --- |
| 1 | `2026-03-10T01:36:02Z` | `200` | `200` | `servicecheck-00-http-8080 passing` |
| 2 | `2026-03-10T01:46:57Z` | `200` | `200` | `servicecheck-00-http-8080 passing` |
| 3 | `2026-03-10T01:57:32Z` | `200` | `200` | `servicecheck-00-http-8080 passing` |
| 4 | `2026-03-10T02:08:11Z` | `200` | `200` | `servicecheck-00-http-8080 passing` |

## Conclusion
- Release remains healthy across the full post-release observation window.
- No rollback or forward-fix was required during the window.
- GitHub `Release Gate` and live production checks are aligned.

## Next-round follow-ups
1. Automate freshness-sensitive release evidence generation before `Release Gate`.
   Evidence churn occurred across `cuj-synthetic`, `billing-console-drift`, `data-soft-delete-purge`, `chaos-drill`, and `p0-readiness`; the relevant generators live under `/Users/alanzeng/projects/Haven-local/scripts` and `/Users/alanzeng/projects/Haven-local/backend/scripts`.
2. Reduce CI and formal release-shell drift by centralizing shared defaults.
   The recent fixes touched `/Users/alanzeng/projects/Haven-local/scripts/release-gate.sh` and `/Users/alanzeng/projects/Haven-local/.github/workflows/release-gate.yml`; those two paths should share one source of truth for API URL, SLO URL, evidence source, and backend Python bootstrap.
3. Confirm whether production should remain on `shared_state_backend=memory`.
   Current live `/health/slo` reports `ai_router_runtime.state.shared_state_backend="memory"`; compare that with `/Users/alanzeng/projects/Haven-local/backend/fly.toml` and deploy intent before the next release.
