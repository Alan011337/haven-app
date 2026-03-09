# Full-stack Top-10 Optimization Rollout (2026-03-05)

This rollout implements ten high-ROI optimizations with fail-closed contracts.

## 1) Gate helper shared module
- Added `/Users/alanzeng/Desktop/Projects/Haven/scripts/gate-common.sh`.
- `/Users/alanzeng/Desktop/Projects/Haven/scripts/release-gate-local.sh` now sources the helper.

## 2) Release/security gate consistency contract
- Added `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_gate_consistency_contract.py`.
- Added test `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_gate_consistency_contract.py`.

## 3) Deployment source-of-truth contract (Fly active / Render archived)
- Added archived marker to `/Users/alanzeng/Desktop/Projects/Haven/render.yaml`.
- Added contract script `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_deploy_source_of_truth.py`.
- Added test `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_deploy_source_of_truth_contract.py`.

## 4) API response wrapping performance guard
- Optimized JSON body extraction conditions in `/Users/alanzeng/Desktop/Projects/Haven/backend/app/main.py`.
- Added regression test `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_main_response_wrapping_guard.py`.

## 5) Runtime settings centralization
- Added `/Users/alanzeng/Desktop/Projects/Haven/backend/app/core/runtime_switches.py`.
- `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/feature_flags.py` now consumes centralized runtime switches.
- Added contract check + test:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_runtime_switch_contract.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_runtime_switch_contract.py`

## 6) Frontend polling governance
- Added `/Users/alanzeng/Desktop/Projects/Haven/frontend/src/lib/polling-policy.ts`.
- Applied to:
  - `/Users/alanzeng/Desktop/Projects/Haven/frontend/src/features/notifications/useNotificationsData.ts`
  - `/Users/alanzeng/Desktop/Projects/Haven/frontend/src/features/home/useHomeData.ts`
  - `/Users/alanzeng/Desktop/Projects/Haven/frontend/src/components/layout/Sidebar.tsx`
  - `/Users/alanzeng/Desktop/Projects/Haven/frontend/src/components/system/DegradationBanner.tsx`

## 7) API transport governance hardening
- Enhanced `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_frontend_api_transport_contract.py`:
  - reject `axios` imports outside `/frontend/src/lib/api.ts`.
- Added regression in `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_frontend_api_transport_contract.py`.

## 8) Frontend test coverage floor guard
- Added `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_frontend_test_coverage_floor.py`.
- Added `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_frontend_test_coverage_floor.py`.

## 9) File hygiene guard + cleanup
- Removed duplicate test filename with space suffix:
  - deleted `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_journal_queue 2.py`
- Added hygiene contract:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_file_hygiene_contract.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_file_hygiene_contract.py`

## 10) AI router modularization (cache policy)
- Added `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/ai_router_cache_policy.py`.
- `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/ai_router.py` now delegates cache/fingerprint policy helpers.
- Added tests:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_ai_router_cache_policy.py`

## Final convergence fixes (post-rollout)
- Fixed notification outbox import regression:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/notification.py`
  - `is_notification_outbox_enabled` now resolves from `notification_outbox_config`.
- Fixed security evidence script import fallback for shell execution:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/validate_security_evidence.py`
  - supports both `scripts.security_evidence_utils` and local import mode.
- Upgraded Daily Card polling to adaptive governance:
  - `/Users/alanzeng/Desktop/Projects/Haven/frontend/src/components/features/DailyCard.tsx`
  - now uses `getAdaptiveIntervalMs` and visibility/online-aware re-scheduling.
- Expanded polling governance contract coverage:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_frontend_polling_governance_contract.py`
  - now includes `DailyCard.tsx`.
- Added frontend security headers baseline + gate enforcement:
  - `/Users/alanzeng/Desktop/Projects/Haven/frontend/next.config.ts`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_frontend_security_headers_contract.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_frontend_security_headers_contract.py`
  - integrated into `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/security-gate.sh`
  - integrated into `/Users/alanzeng/Desktop/Projects/Haven/scripts/release-gate-local.sh`
- Enabled timeline cursor defaults (with kill-switch rollback path retained):
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/core/_settings_impl.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/feature_flags.py`

## Gate integration
- `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/security-gate.sh` now includes:
  - deploy SoT contract
  - gate consistency contract
  - file hygiene contract
  - polling governance contract
  - runtime switch contract
  - frontend test coverage floor
- `/Users/alanzeng/Desktop/Projects/Haven/scripts/release-gate-local.sh` now runs:
  - gate consistency contract
  - deploy SoT contract
  - file hygiene contract
