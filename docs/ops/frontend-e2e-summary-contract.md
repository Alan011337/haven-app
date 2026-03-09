# Frontend E2E Summary Contract

This document defines the machine-readable payload emitted by:

- `/Users/alanzeng/Desktop/Projects/Haven/frontend/scripts/summarize-e2e-result.mjs`
- `/Users/alanzeng/Desktop/Projects/Haven/frontend/scripts/check-e2e-summary-schema.mjs`
- `/Users/alanzeng/Desktop/Projects/Haven/.github/workflows/release-gate.yml`
- `/Users/alanzeng/Desktop/Projects/Haven/scripts/release-gate-local.sh`
- `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_quick_backend_contract_summary.py`

## JSON Schema (v1)

`schema_version` must be `v1`.

```json
{
  "schema_version": "v1",
  "result": "pass | fail | unavailable",
  "exit_code": 0,
  "classification": "none | pre_e2e_step_failure | missing_browser | browser_download_network | app_unreachable | cuj_assertion_timeout | test_or_runtime_failure",
  "log_available": true,
  "next_action": "human-readable remediation hint"
}
```

Notes:

- `exit_code` is `null` only when `result` is `unavailable`.
- `classification` is `none` only when `result` is `pass`.

## Compatibility Policy

- Any change to existing fields or allowed values requires a new `schema_version`.
- Consumers must reject unknown `schema_version` values by default.

## Validation

- Contract tests:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_frontend_e2e_summary_contract.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_frontend_e2e_summary_script.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_frontend_e2e_summary_schema_gate_script.py`

- Local verification command:
  - `cd /Users/alanzeng/Desktop/Projects/Haven/backend && PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m unittest tests/test_frontend_e2e_summary_contract.py tests/test_frontend_e2e_summary_script.py tests/test_frontend_e2e_summary_schema_gate_script.py`
  - `cd /Users/alanzeng/Desktop/Projects/Haven/frontend && node scripts/check-e2e-summary-schema.mjs --summary-path /tmp/frontend-e2e-summary.json --required-schema-version v1`

## release-gate-local Default

- `release-gate-local.sh` default mode (`RUN_FULL_BACKEND_PYTEST=0`) runs quick contract tests (`test_release_gate_workflow_contract.py`, `test_security_gate_contract.py`) and all e2e summary contract checks.
- Set `RUN_QUICK_BACKEND_CONTRACT_TESTS=0` only when intentionally bypassing quick backend tests for local troubleshooting.
- quick mode also emits `/tmp/release-gate-local-quick-backend-tests-summary.json` and validates it via `check_quick_backend_contract_summary.py`.

## Quick Backend Summary Schema (v1)

Quick backend contract summary payload must contain:

```json
{
  "schema_version": "v1",
  "result": "pass | fail",
  "exit_code": 0,
  "test_count": 35,
  "duration_seconds": 2,
  "log_path": "/tmp/release-gate-local-quick-backend-tests.log"
}
```

### Manual validation

- `cd /Users/alanzeng/Desktop/Projects/Haven/backend && PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/check_quick_backend_contract_summary.py --summary-file /tmp/release-gate-local-quick-backend-tests-summary.json --required-schema-version v1`

### Troubleshooting

- `schema_version mismatch`: local scripts/tests drifted; sync `release-gate-local.sh` and summary gate script.
- `result/exit_code mismatch`: quick backend tests failed but summary payload marked pass (or inverse); inspect `log_path`.
