# Backend audit baseline (Phase 0)

Recorded after plan approval. No code changes; results only.

## Environment

- Backend root: `backend/`
- Python: `backend/venv/bin/python` (python3.13)
- Commands run with `PYTHONUTF8=1 PYTHONPATH=.` in backend directory.

## Baseline results

| Check | Command | Exit code | Notes |
|-------|--------|-----------|--------|
| Lint | `cd backend && export PYTHONUTF8=1 PYTHONPATH=. && ruff check .` | N/A | `ruff` not installed in venv (use `python -m ruff` if installed elsewhere). |
| Typecheck | mypy/pyright | N/A | None configured in backend. |
| Tests | `cd backend && PYTHONUTF8=1 PYTHONPATH=. ./venv/bin/python -m pytest -q -p no:cacheprovider --tb=no -x 2>&1 \| head -80` | 1 | ERROR: NameError in tests/test_api_inventory_contract.py — `CreateCheckoutSessionResult` is not defined (billing router import). |
| Build/Start | `cd backend && PYTHONUTF8=1 PYTHONPATH=. ./venv/bin/python -c "from app.main import app; print('import ok')"` | 1 | NameError: name 'CreateCheckoutSessionResult' is not defined (app.api.routers.billing). |
| Security gate | Optional | — | Not run for baseline (time-consuming). |

## Summary

- App import and pytest fail due to missing billing symbols (`stripe`, `_STRIPE_PROVIDER`, `CreateCheckoutSessionRequest`, `CreateCheckoutSessionResult`, `CreatePortalSessionResult`). Batch 1 addresses this.

---

## Post–Phase 3 (after Batches 1–3)

- **Batch 1**: Billing schema + lazy `import stripe`, `_STRIPE_PROVIDER` added. App import succeeds; billing-related pytest (e.g. `-k "billing or checkout or portal"`) passes aside from pre-existing failures (e.g. `test_audit_log_billing_notification_controls`, health endpoint mocks).
- **Batch 2**: `LOG_INCLUDE_STACKTRACE` already default `False`; RUNBOOK section "Stack traces in production" added.
- **Batch 3**: Registration rate limit (IP-based) added: `REGISTRATION_RATE_LIMIT_IP_COUNT`, `REGISTRATION_RATE_LIMIT_IP_WINDOW_SECONDS`, `enforce_registration_rate_limit`, and test `test_registration_rate_limit_returns_429_when_exceeded` added.
