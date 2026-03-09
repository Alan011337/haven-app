# Abuse Budget Policy (P0 Baseline)

Last updated: 2026-02-17

## Scope

- Backend API write-path rate limits
- Pairing abuse controls (user + IP)
- WebSocket connection/message abuse controls

## Baseline Budgets (Current Defaults)

- Journal write: `JOURNAL_RATE_LIMIT_COUNT=12` / `JOURNAL_RATE_LIMIT_WINDOW_SECONDS=60`
- Journal IP scope: `JOURNAL_RATE_LIMIT_IP_COUNT=36` / `JOURNAL_RATE_LIMIT_WINDOW_SECONDS=60`
- Journal device scope: `JOURNAL_RATE_LIMIT_DEVICE_COUNT=24` / `JOURNAL_RATE_LIMIT_WINDOW_SECONDS=60`
- Journal partner-pair scope: `JOURNAL_RATE_LIMIT_PARTNER_PAIR_COUNT=24` / `JOURNAL_RATE_LIMIT_WINDOW_SECONDS=60`
- Card respond: `CARD_RESPONSE_RATE_LIMIT_COUNT=30` / `CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS=60`
- Card respond IP scope: `CARD_RESPONSE_RATE_LIMIT_IP_COUNT=90` / `CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS=60`
- Card respond device scope: `CARD_RESPONSE_RATE_LIMIT_DEVICE_COUNT=60` / `CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS=60`
- Card respond partner-pair scope: `CARD_RESPONSE_RATE_LIMIT_PARTNER_PAIR_COUNT=60` / `CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS=60`
- Device header: `RATE_LIMIT_DEVICE_HEADER=x-device-id`
- Pairing (user): `PAIRING_ATTEMPT_RATE_LIMIT_COUNT=10` / `PAIRING_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS=300`
- Pairing (user cooldown): threshold `5`, cooldown `600s`
- Pairing (ip): `PAIRING_IP_ATTEMPT_RATE_LIMIT_COUNT=30` / `PAIRING_IP_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS=300`
- Pairing (ip cooldown): threshold `15`, cooldown `900s`
- WebSocket per-user connections: `WS_MAX_CONNECTIONS_PER_USER=1`
- WebSocket global connections: `WS_MAX_CONNECTIONS_GLOBAL=2000`
- WebSocket message budget: `WS_MESSAGE_RATE_LIMIT_COUNT=120` / `WS_MESSAGE_RATE_LIMIT_WINDOW_SECONDS=60`
- WebSocket backoff: `WS_MESSAGE_BACKOFF_SECONDS=30`
- WebSocket max payload: `WS_MAX_PAYLOAD_BYTES=4096`

## Guardrail Invariants (CI Enforced)

- All limit/window/backoff/cooldown values must be positive.
- Pairing IP budgets must not be weaker than pairing user budgets:
  - `PAIRING_IP_ATTEMPT_RATE_LIMIT_COUNT >= PAIRING_ATTEMPT_RATE_LIMIT_COUNT`
  - `PAIRING_IP_FAILURE_COOLDOWN_THRESHOLD >= PAIRING_FAILURE_COOLDOWN_THRESHOLD`
  - `PAIRING_IP_FAILURE_COOLDOWN_SECONDS >= PAIRING_FAILURE_COOLDOWN_SECONDS`
- WebSocket connection envelope:
  - `WS_MAX_CONNECTIONS_GLOBAL >= WS_MAX_CONNECTIONS_PER_USER`
- WebSocket message/payload envelope:
  - `WS_MESSAGE_RATE_LIMIT_COUNT <= 300` per window
  - `WS_MAX_PAYLOAD_BYTES <= 8192`
- Write-path anti-flood envelope:
  - `JOURNAL_RATE_LIMIT_COUNT <= 120`
  - `CARD_RESPONSE_RATE_LIMIT_COUNT <= 180`
- Multi-scope write-path guardrails:
  - `JOURNAL_RATE_LIMIT_IP_COUNT >= JOURNAL_RATE_LIMIT_COUNT`
  - `JOURNAL_RATE_LIMIT_DEVICE_COUNT >= JOURNAL_RATE_LIMIT_COUNT`
  - `JOURNAL_RATE_LIMIT_PARTNER_PAIR_COUNT >= JOURNAL_RATE_LIMIT_COUNT`
  - `CARD_RESPONSE_RATE_LIMIT_IP_COUNT >= CARD_RESPONSE_RATE_LIMIT_COUNT`
  - `CARD_RESPONSE_RATE_LIMIT_DEVICE_COUNT >= CARD_RESPONSE_RATE_LIMIT_COUNT`
  - `CARD_RESPONSE_RATE_LIMIT_PARTNER_PAIR_COUNT >= CARD_RESPONSE_RATE_LIMIT_COUNT`

## Verification

- Local:
  - `cd backend && venv/bin/python -m pytest -q -p no:cacheprovider tests/test_abuse_budget_policy.py`
  - `cd backend && venv/bin/python -m pytest -q -p no:cacheprovider tests/test_abuse_economics_runtime.py`
  - `cd backend && venv/bin/python -m pytest -q -p no:cacheprovider tests/test_rate_limit_runtime_metrics.py`
- Security gate:
  - `cd backend && ./scripts/security-gate.sh`

## Observability Contract

- On `429` write-path throttling, response headers include:
  - `Retry-After`
  - `X-RateLimit-Scope` (`user` | `ip` | `device` | `partner_pair`)
  - `X-RateLimit-Action` (`journal_create` | `card_response_create`)
- Backend emits structured warning log:
  - `rate_limit_block endpoint=... action=... scope=... user_id=... partner_id=... retry_after_seconds=...`
- Runtime counters are exposed via:
  - `GET /health` -> `sli.write_rate_limit`
  - `GET /health/slo` -> `sli.write_rate_limit`
  - `GET /health` / `GET /health/slo` -> `sli.abuse_economics`
    - `sli.abuse_economics.evaluation.status`: `ok | warn | block | insufficient_data`
    - `sli.abuse_economics.vectors[*]`: projected daily events/cost and utilization

## Runtime Gate Contract

- Release gate consumes `/health/slo` and fails closed on:
  - `sli.abuse_economics.evaluation.status == block`
- Optional stricter mode:
  - set `SLO_GATE_FAIL_ON_ABUSE_WARN=true` to also block on `warn`
- Command:
  - `cd backend && venv/bin/python scripts/check_slo_burn_rate_gate.py --url "$SLO_GATE_HEALTH_SLO_URL"`
  - local fallback: `cd backend && venv/bin/python scripts/check_slo_burn_rate_gate.py --payload-file /tmp/health-slo.json`

## Rollback Rule

If this policy causes false positives in emergency response, temporarily relax only the affected bound and keep all changes in git with a postmortem action item to restore strictness.
