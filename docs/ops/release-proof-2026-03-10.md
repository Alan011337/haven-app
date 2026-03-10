# Release Proof 2026-03-10

## Scope
- Release workflow: `Release Gate`
- Green run: `Align frontend e2e CI API base URL #15`
- Commit: `f0d7e25`
- Branch: `main`
- Result: `Success`

## CI signoff
- `backend-gate`: pass
- `frontend-gate`: pass
- `frontend-e2e`: pass

## Production smoke
- Target app: `haven-api-prod`
- Monitoring window (UTC): `2026-03-10T00:34:31Z` to `2026-03-10T00:51:17Z`
- Monitoring window (Asia/Taipei): `2026-03-10 08:34:31` to `2026-03-10 08:51:17`

| Sample | Timestamp (UTC) | `/health` | `/health/slo` | Fly checks |
| --- | --- | --- | --- | --- |
| 1 | `2026-03-10T00:34:31Z` | `200` | `200` | `servicecheck-00-http-8080 passing` |
| 2 | `2026-03-10T00:40:14Z` | `200` | `200` | `servicecheck-00-http-8080 passing` |
| 3 | `2026-03-10T00:45:48Z` | `200` | `200` | `servicecheck-00-http-8080 passing` |
| 4 | `2026-03-10T00:51:17Z` | `200` | `200` | `servicecheck-00-http-8080 passing` |

## Commands used
```bash
curl -i --max-time 20 https://haven-api-prod.fly.dev/health
curl -i --max-time 20 https://haven-api-prod.fly.dev/health/slo
HOME=/tmp /tmp/flybin/flyctl checks list --app haven-api-prod
```

## Outcome
- Release gate proof: complete
- Production smoke: healthy for the full observation window
- Fly health checks: stable and passing

## Notes
- No deploy rollback was required during the observation window.
- This file is the release evidence for the successful `main` release proof on `2026-03-10`.
