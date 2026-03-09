# Synthetic CUJ Monitoring (P1-A)

## Goals
- Run production-safe synthetic checks for:
  - CUJ-01 Ritual: load -> draw -> respond -> unlock
  - CUJ-02 Journal: submit -> persist -> analysis queued -> delivered

## Initial Skeleton
- Script: `scripts/synthetics/run_cuj_synthetics.py`
- Local helper: `scripts/generate-cuj-synthetic-evidence-local.sh`
- Schedule: `.github/workflows/cuj-synthetics.yml` (daily + manual)
- Evidence output: `docs/sre/evidence/cuj-synthetic-*.json`
- CI summary output: `/tmp/cuj-synthetics-summary.json` (`result`, `failure_class`, `failed_stages`, `warn_stages`)

## Contract
- Script supports `--allow-missing-url` for non-prod PR contexts.
- Script also supports offline payload mode for sandbox/local dry-run:
  - `--health-payload-file <path>` + `--slo-payload-file <path>`
- Production run must set `SYNTHETIC_BASE_URL` and auth secrets.
- Failures should classify by stage (`health`, `slo`, `ritual`, `journal`).
- SLO checks consume `/health/slo` statuses: `ws`, `ws_burn_rate`, `cuj`.
- Release gate evidence validator: `backend/scripts/check_cuj_synthetic_evidence_gate.py`.
  - validates latest `cuj-synthetic-*.json` schema + freshness (default max age 36h).
  - `main` should run fail-closed; PR/local can run with `--allow-missing-evidence`.

## Local evidence refresh

```bash
bash scripts/generate-cuj-synthetic-evidence-local.sh
```

- Generates fresh CUJ evidence under `docs/sre/evidence/`.
- Immediately validates freshness + contract with `check_cuj_synthetic_evidence_gate.py --require-pass`.

## Alerting
- Any hard failure on required stages should page SRE owner.
- Repeated failures (>=3 consecutive runs) auto-open issue.
- Alert issue body should include `failure_class` + `failed_stages` to speed triage.
- `failure_class` handling must follow `docs/sre/alerts.md` Failure Class Routing table.
