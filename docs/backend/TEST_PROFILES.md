# Backend Test Profiles

`/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run-test-profile.sh` provides three repeatable profiles:

- `fast`: quick runtime/contracts (`health`, `outbox`, billing/store policy contracts)
- `safety`: authz/security-heavy matrix tests (BOLA + billing + endpoint policy)
- `full`: full backend lint + full backend pytest

## Usage

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
./scripts/run-test-profile.sh fast
./scripts/run-test-profile.sh safety
./scripts/run-test-profile.sh full
```

or with env:

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
TEST_PROFILE=safety ./scripts/run-test-profile.sh
```

## Release Gate Preflight

`/Users/alanzeng/Desktop/Projects/Haven/scripts/release-gate-local.sh` supports an optional backend preflight profile before running full security/release gates:

```bash
cd /Users/alanzeng/Desktop/Projects/Haven
RELEASE_GATE_BACKEND_TEST_PROFILE=fast bash scripts/release-gate-local.sh
```

## Rollback

If profile script behavior regresses:

```bash
cd /Users/alanzeng/Desktop/Projects/Haven
git restore /Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run-test-profile.sh \
  /Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_test_profile_script_contract.py \
  /Users/alanzeng/Desktop/Projects/Haven/docs/backend/TEST_PROFILES.md
```
