# Alert Specification (P1-A)

## Burn-rate (multi-window, multi-burn)

### Fast windows
- Window pair: `5m / 1h`
- Purpose: fast detection for severe regressions.
- Trigger class: `page` when both windows exceed fast threshold.

### Slow windows
- Window pair: `6h / 24h`
- Purpose: sustained degradation detection.
- Trigger class: `ticket/page` depending on severity.

## Threshold Policy
- WS burn-rate thresholds (current gate baseline):
  - fast: `14.4`
  - slow: `6.0`
- Service tier policy:
  - `tier_0` (Bind/Ritual/Journal/Unlock) freeze is enforced for `feature` releases.
  - `tier_1` (Share/Report/Growth/Visual) follows `docs/sre/service-tiering.json`.
- CUJ runtime status (`/health/slo -> sli.evaluation.cuj`):
  - `degraded`: immediate gate failure (`cuj_sli_degraded`)
  - `insufficient_data`: allowed by default, fail when `SLO_GATE_REQUIRE_SUFFICIENT_DATA=true`
- Push runtime status (`/health/slo -> sli.evaluation.push`):
  - `degraded`: immediate gate failure (`push_sli_degraded`)
  - `insufficient_data`: allowed by default, fail when `SLO_GATE_REQUIRE_SUFFICIENT_DATA=true`
- Abuse economics runtime status (`/health/slo -> sli.abuse_economics.evaluation.status`):
  - `block`: immediate gate failure (`abuse_economics_block`)
  - `warn`: observe by default, fail when `SLO_GATE_FAIL_ON_ABUSE_WARN=true`
  - `insufficient_data`: allowed by default, fail when `SLO_GATE_REQUIRE_SUFFICIENT_DATA=true`
- Ritual and Journal SLO thresholds follow error budget objective; breach contributes to release freeze.

## Severity Matrix
| Severity | Condition | Action |
| --- | --- | --- |
| SEV-1 | Fast + slow windows both breached + user impact confirmed | page primary on-call, start incident |
| SEV-2 | Fast breached only | triage within 15m, monitor rollout |
| SEV-3 | Slow breached only | create remediation ticket, monitor 24h |

## Failure Class Routing (Synthetic CUJ)
| failure_class | Meaning | Primary SOP |
| --- | --- | --- |
| `health_endpoint_unavailable` | `/health` probe failed or unhealthy | Check service availability, ingress, DB/Redis probe failures; escalate to incident if >10m |
| `ws_slo_degraded` | WS SLI or WS burn-rate degraded | Apply WS degradation fallback (polling/inbox), inspect reject/block counters, evaluate rollback |
| `cuj_slo_degraded` | CUJ runtime SLI degraded | Inspect `/health/slo -> sli.evaluation.cuj`, check ritual/journal/bind failure reasons, freeze feature rollout if sustained |
| `abuse_economics_block` | Abuse cost budget block threshold exceeded | Inspect `/health/slo -> sli.abuse_economics.vectors`, tighten relevant rate-limit/WS controls, freeze feature rollout until recovered |
| `push_sli_degraded` | Push delivery/latency/cleanup SLI degraded | Check `/health/slo -> sli.push` and `sli.evaluation.push`, run push cleanup dry-run, disable push channel if needed |
| `journal_latency_regression` | Journal latency stage failed | Enable async degradation path, inspect queue/analysis lag, validate retry backlog |
| `synthetic_stage_failure` | Other synthetic stage contract failure | Review synthetic evidence JSON + workflow logs, route to service owner |
| `none` | No hard failure | No incident; keep scheduled monitoring |

## SOP (on alert)
1. Confirm signal quality (data lag/collector status).
2. Check `/health/slo` (`ws`, `ws_burn_rate`, `cuj`, `abuse_economics`) and recent deployment diff.
3. Execute degradation matrix fallback (`docs/sre/degradation.md`).
4. If unresolved, trigger canary rollback per `docs/sre/canary.md`.
5. Update `docs/sre/error-budget-status.json` if freeze criteria met.
