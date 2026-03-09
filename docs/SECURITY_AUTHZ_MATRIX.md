# Security AuthZ Matrix

Canonical authorization matrix documentation lives at:
- `/Users/alanzeng/Desktop/Projects/Haven/docs/security/authz_matrix.md`

Canonical machine-readable matrices:
- `/Users/alanzeng/Desktop/Projects/Haven/docs/security/endpoint-authorization-matrix.json`
- `/Users/alanzeng/Desktop/Projects/Haven/docs/security/read-authorization-matrix.json`

Required P0 BOLA gates:
- `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_endpoint_authorization_matrix.py`
- `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_read_authorization_matrix.py`
- `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/security/test_bola_matrix.py`
- `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/security/test_bola_subject_matrix.py`

Local verification:

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/check_endpoint_authorization_matrix.py
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/check_read_authorization_matrix.py
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider tests/security/test_bola_matrix.py tests/security/test_bola_subject_matrix.py
```
