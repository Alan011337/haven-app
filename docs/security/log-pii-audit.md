# Log/Trace PII Audit (Batch 1)

One-time audit for logger/trace output that could leak PII or secrets. Redaction helpers: `backend/app/core/log_redaction.py`, `backend/app/services/trace_span.py` (`_sanitize_trace_fields`).

## Fixes applied

| File:Line | Risk | Change |
|-----------|------|--------|
| `backend/app/main.py` (unhandled_exception_handler) | Exception message may contain request/user data | Log only `type(exc).__name__` instead of `exc`. |
| `backend/app/core/socket_manager.py` (Redis WS message parse) | Exception `e` could contain message payload | Log only `type(e).__name__`. |
| `backend/app/api/routers/billing.py` (Stripe checkout/portal) | Full exception `e` in log | Log only `type(e).__name__`. |
| `backend/app/services/growth_first_delight_runtime.py` (ack log) | Client `payload["source"]` in log | Allowlist known values or truncate to 50 chars. |

## Already safe

- `backend/app/api/journals.py`: journal content logged via `redact_content(..., max_visible=10)`.
- `backend/app/services/notification.py`: email logged via `redact_email(receiver_email)`.
- `backend/app/services/trace_span.py`: trace fields passed through `_sanitize_trace_fields`.
- CUJ metadata: `_sanitize_cuj_metadata` in `backend/app/api/routers/users/routes.py`.
- Other log sites audited: only IDs (UUID), type names, counts, or redacted values.

## Verification

- `cd backend && bash scripts/security-gate.sh` (requires env: DATABASE_URL, SECRET_KEY, OPENAI_API_KEY).
- Grep for high-risk patterns: `logger.*(.*email|token|content|password` (no new matches).
