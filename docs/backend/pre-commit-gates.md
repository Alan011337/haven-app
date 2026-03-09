# Pre-commit contract gate

Run this before pushing backend/frontend API changes:

```bash
cd /Users/alanzeng/Desktop/Projects/Haven
bash scripts/pre-commit-api-contract-check.sh
```

It validates:

- backend API contract snapshot
- backend API inventory source-of-truth
- frontend generated contract type freshness
