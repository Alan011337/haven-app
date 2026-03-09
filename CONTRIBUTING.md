# Contributing

This repository prioritizes **P0 launch readiness**. Before opening a PR, ensure DoD, safety/privacy, and rollback details are explicit.

## Workflow

1. Run local gate: `./scripts/release-gate.sh`
2. If frontend flow changes, also run: `RUN_E2E=1 ./scripts/release-gate.sh`
3. Open PR with `.github/PULL_REQUEST_TEMPLATE.md`

## Required References

- DoD template: `docs/P0-DOD-TEMPLATE.md`
- Launch checklist: `docs/P0-LAUNCH-GATE.md`
- Security baseline: `SECURITY.md`
- Data rights: `DATA_RIGHTS.md`
- AI policy: `POLICY_AI.md`

## P0 Contribution Rules

- Keep each change set focused on one concern.
- Include `change summary`, `risk`, `how to test`, and `rollback`.
- Any new endpoint must include authorization/BOLA tests.
- Sensitive data must not appear in logs/traces; apply redaction.
- Docs should remain minimal and map to code/tests/CI gates.
