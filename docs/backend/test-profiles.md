# Backend Test Profiles

This document defines the baseline pytest execution profiles for Haven backend.

## Markers

- `unit`: fast isolated tests with no external dependency.
- `integration`: database/session/service integration tests.
- `contract`: release/security/policy contract tests.
- `slow`: long-running tests (nightly or pre-release).

## Recommended commands

Fast local loop:

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -m "not slow" -p no:cacheprovider
```

Contract-only:

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -m contract -p no:cacheprovider
```

Nightly/full:

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider
```

Scripted profiles:

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
./scripts/run-test-profile.sh smoke
./scripts/run-test-profile.sh unit
./scripts/run-test-profile.sh contract
./scripts/run-test-profile.sh full
```
