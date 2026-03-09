# PII Observability Guardrails

Haven metrics and logs must avoid unbounded or sensitive labels.

## Hard rules

- Never use `user_id`, `request_id`, `email`, `token`, `session`, `jwt`, `password`, `secret`, or raw content as metric labels.
- Unknown provider/profile/reason values are mapped to the fixed bucket `unknown`.
- Unbounded fields can appear only in redacted logs, never in metrics labels.

## Verification

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_ai_router_metrics.py
```
