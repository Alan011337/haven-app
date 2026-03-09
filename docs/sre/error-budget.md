# Error Budget Policy (P1-A)

## Policy
- If SLO-01 (Daily Ritual) OR SLO-02 (Journal+Analysis) is below objective for rolling 24h:
  - `release_freeze = true`
  - only `bugfix/security/hotfix` releases are allowed.
- Weekly blameless postmortem is mandatory while freeze is active.

## Runtime Contract
- Machine-readable status file: `docs/sre/error-budget-status.json`
- Gate checker: `backend/scripts/check_error_budget_freeze_gate.py`
- Service tier gate checker: `backend/scripts/check_service_tier_budget_gate.py`
- Service tier policy contract: `docs/sre/service-tiering.json`
- SLO monitor source: `backend/scripts/check_slo_burn_rate_gate.py` evaluates `ws`, `ws_burn_rate`, and `cuj`.
- CI behavior:
  - PR: can run in `allow-missing-status` mode.
  - main: status file required, freeze blocks feature deploy.

## Service Tiering (SRE-TIER-01)
- `tier_0` (Bind/Ritual/Journal/Unlock): freeze is enforced for `feature` release intent.
- `tier_1` (Share/Report/Growth/Visual): policy can allow feature rollout during tier_0 freeze when explicitly configured.
- Release intent is declared via `RELEASE_INTENT` (`feature|bugfix|security|hotfix`).
- Target tier is declared via `RELEASE_TARGET_TIER` (`tier_0|tier_1`).

## Override Rules
- Temporary override only for production incident mitigation.
- Override requires incident ID and owner.
- Suggested env flag: `RELEASE_GATE_HOTFIX_OVERRIDE=1`.

## Ownership
- Service owner updates budget status daily.
- Release manager verifies checklist before deploy.
