# Haven Top-10 Optimization Batch (2026-03-06)

This batch finalizes 10 high-ROI full-stack hardening items with low-risk changes and validation gates.

## 1) Frontend API client single import path
- Why: reduce drift between duplicated API clients.
- How: added `frontend/src/lib/http-client.ts` as canonical compatibility path; `frontend/src/services/api-transport.ts` now imports from it.
- DoD: frontend lint/typecheck pass and transport contract gate remains green.

## 2) AI router contract extraction
- Why: reduce `ai_router.py` coupling and make policy/runtime types reusable.
- How: extracted constants and dataclasses into `backend/app/services/ai_router_contract.py`; `backend/app/services/ai_router.py` imports from contract module.
- DoD: AI router runtime/retry/fallback tests pass unchanged.

## 3) WS typing session cache
- Why: reduce repeated DB lookups for typing indicator events.
- How: added `backend/app/services/ws_typing_session_cache.py`, integrated hit/miss path in `backend/app/core/ws_endpoint.py`, and exposed metrics counters.
- DoD: cache hit/expiry/overflow tests pass; WS runtime tests stay green.

## 4) PostHog runtime hardening
- Why: improve observability and avoid failure amplification.
- How: `backend/app/services/posthog_events.py` now tracks bounded runtime counters and degrades gracefully on send failure.
- DoD: no uncaught submission exceptions on provider errors; runtime snapshot includes counters.

## 5) Push dispatch bounded concurrency
- Why: avoid unbounded fan-out pressure under many subscriptions.
- How: added `PUSH_DISPATCH_MAX_CONCURRENCY` in settings + domain loaders; `backend/app/services/notification_multichannel.py` now dispatches with semaphore.
- DoD: notification push fan-out and runtime tests pass.

## 6) Health provider probe modularization
- Why: isolate DB/Redis/provider probes and simplify health route maintenance.
- How: added `backend/app/core/health_providers.py`; health routes delegate through wrappers and preserve test patchability.
- DoD: health endpoint tests pass (including degraded and patched scenarios).

## 7) Health payload builder patch-safety
- Why: avoid static function reference capture that breaks monkeypatch-based tests.
- How: runtime payload registry switched to builder-name lookup in `backend/app/core/health_routes.py`.
- DoD: patched payload tests pass; degraded reasons stay correct.

## 8) Settings contract validation
- Why: catch invalid runtime combinations early.
- How: added `backend/app/core/settings_contract.py`, `backend/scripts/check_settings_contract.py`, and `backend/tests/test_settings_contract.py`.
- DoD: script returns fail on contract violations and pass on valid combinations.

## 9) Frontend home hook cleanup
- Why: remove duplicated logic and reduce future bug surface.
- How: extracted helpers into `frontend/src/features/home/home-data-utils.ts`; `frontend/src/features/home/useHomeData.ts` now reuses shared sort + invalidation helpers.
- DoD: frontend lint/typecheck pass.

## 10) Release gate enforcement for settings contract
- Why: make settings contract checks non-optional in local release preflight.
- How: wired `check_settings_contract.py` into `scripts/release-gate-local.sh`.
- DoD: release gate runs the new step and remains green.

## Verification commands
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
ruff check .
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_ai_router.py \
  tests/test_ai_router_runtime.py \
  tests/test_ai_router_retry.py \
  tests/test_ai_provider_fallback_integration.py \
  tests/test_notification_service.py \
  tests/test_notification_multichannel_runtime.py \
  tests/test_notification_push_dispatch_fanout.py \
  tests/test_health_endpoint.py \
  tests/test_ws_runtime_metrics.py \
  tests/test_ws_typing_session_cache.py \
  tests/test_settings_contract.py

cd /Users/alanzeng/Desktop/Projects/Haven/frontend
npm run lint
npm run typecheck

cd /Users/alanzeng/Desktop/Projects/Haven
SECURITY_GATE_PROFILE=fast bash backend/scripts/security-gate.sh
SKIP_FRONTEND_TYPECHECK=1 SKIP_MOBILE_TYPECHECK=1 bash scripts/release-gate-local.sh
```

## Rollback
- Code rollback: `git revert <commit_sha>`
- Runtime stopgap toggles:
  - `WEBSOCKET_ENABLED=false` (disable realtime path)
  - `PUSH_NOTIFICATIONS_ENABLED=false` (disable push dispatch)
  - `POSTHOG_ENABLED=false` (disable analytics submission)
- Gate rollback (if urgently needed): temporarily remove `check_settings_contract_local` from release gate script and revert in follow-up.
