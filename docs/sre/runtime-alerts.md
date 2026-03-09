# Runtime Alerts (Outbox + Dynamic Content)

## Scope
Operational alerts for alpha/prod runtime paths that can silently degrade:
- notification outbox dispatch path
- dynamic content provider/fallback path
- websocket fallback path

## Alert Rules
1. `notification_outbox_depth` high watermark  
- warn: `> 100` for `10m`  
- critical: `> 500` for `5m`

2. `notification_outbox_dead_letter_total` rate jump  
- warn: increase `>= 20` in `15m`  
- critical: increase `>= 100` in `15m`

3. `dynamic_content_runtime.fallback_total / dynamic_content_runtime.attempt_total`  
- warn: `> 0.2` for `30m`  
- critical: `> 0.5` for `15m`

4. `dynamic_content_runtime.timeout_total`  
- warn: increase `>= 30` in `30m`  
- critical: increase `>= 100` in `30m`

5. `ws_disconnected_total` with `realtime_fallback_activated_total`  
- warn: fallback ratio `> 0.1` for `15m`  
- critical: fallback ratio `> 0.3` for `10m`

## Triage Order
1. Confirm health payload fields exist: `sli.notification_runtime`, `sli.dynamic_content_runtime`, `checks.notification_outbox_depth`
2. Distinguish provider incident vs queue buildup:
- provider incident: timeout/fallback spikes, outbox depth flat
- queue incident: outbox depth climbs, dead-letter climbs
3. Apply mitigations:
- disable non-critical notifications (feature flag)
- lower dynamic content generation frequency
- switch to polling fallback for realtime UX

## Rollback
1. Feature-flag rollback first (zero-downtime)
2. Deploy rollback second (previous Fly release)
3. Re-run `make security-gate-fast` and `make release-check` after rollback
