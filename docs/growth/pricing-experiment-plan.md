# Pricing Experiment Plan (MON-04)

## Why
- 在不破壞核心 CUJ 的前提下，建立可控的 pricing 實驗框架。
- 把「上線前可驗證」和「上線後可回滾」變成標準流程，而不是臨時判斷。

## How
- Server-side feature flags 作為唯一開關來源：
  - `growth_ab_experiment_enabled`
  - `growth_pricing_experiment_enabled`
- Kill-switch:
  - `disable_pricing_experiment`
- 分桶策略：
  - 使用 `user_id + experiment_key` 做 deterministic hash，確保使用者跨端黏著。
- Guardrails：
  - 任何 guardrail 指標超過門檻，立即切回 control（kill-switch）。
- Runtime service：
  - allocator 與 guardrail 判定集中在 `pricing_experiment_runtime.py`，避免 CLI-only 邏輯漂移。

## What
- Policy-as-code:
  - `/Users/alanzeng/Desktop/Projects/Haven/docs/security/pricing-experiment-policy.json`
- Contract gate:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_pricing_experiment_policy_contract.py`
- Dry-run tool:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_pricing_experiment_dry_run.py`
- Runtime allocator service:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/pricing_experiment_runtime.py`
- Guardrail evidence snapshot:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_pricing_experiment_guardrail_snapshot.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/.github/workflows/pricing-experiment-guardrail.yml`

## Success Metrics
- `pricing.experiment.checkout_start_rate`
- `pricing.experiment.checkout_complete_rate`
- `pricing.experiment.trial_to_active_rate`

## Guardrail Metrics
- `pricing.experiment.refund_rate`
- `pricing.experiment.chargeback_rate`
- `pricing.experiment.p0_cuj_failure_rate`
- `pricing.experiment.support_ticket_rate`

## DoD
- policy contract 在 `security-gate.sh` 中強制執行。
- dry-run 可產生 deterministic assignment，並顯示 eligibility/kill-switch 原因。
- Release checklist 有明確「pricing 實驗開關與回滾」檢查點。

## Failure / Degradation
- 任一必要旗標缺失或 policy 驗證失敗：實驗停用，回落 control。
- 任一 guardrail 超標：切 `disable_pricing_experiment=true`，停止變體曝光。

## Observability
- 建議事件（canonical）：
  - `growth.pricing.experiment.assigned.v1`
  - `growth.pricing.experiment.checkout_started.v1`
  - `growth.pricing.experiment.checkout_completed.v1`
  - `growth.pricing.experiment.guardrail_triggered.v1`
- Runtime counters（server memory snapshot）：
  - `pricing_experiment_assignment_total`
  - `pricing_experiment_assignment_control_total`
  - `pricing_experiment_assignment_variant_total`
  - `pricing_experiment_assignment_ineligible_total`
  - `pricing_experiment_guardrail_evaluations_total`
  - `pricing_experiment_guardrail_triggered_total`
  - `pricing_experiment_guardrail_pass_total`

## Security / Privacy
- 不記錄 email/token/IP。
- 實驗決策僅使用 UUID、flag 狀態、experiment key。

## Rollback
1. 將 `disable_pricing_experiment=true`。
2. 將 `growth_pricing_experiment_enabled=false`。
3. 若需緊急回退，revert 相關 commit 並重跑 security/release gate。

## Local Commands
1. deterministic allocator dry-run：
   - `cd /Users/alanzeng/Desktop/Projects/Haven/backend && PYTHONUTF8=1 PYTHONPATH=. python scripts/run_pricing_experiment_dry_run.py --user-id 00000000-0000-0000-0000-000000000001 --experiment-key pricing_paywall_copy_v1 --has-partner --include-runtime-snapshot`
2. guardrail snapshot（允許缺資料）：
   - `cd /Users/alanzeng/Desktop/Projects/Haven/backend && PYTHONUTF8=1 PYTHONPATH=. python scripts/run_pricing_experiment_guardrail_snapshot.py --allow-missing-metrics`
3. guardrail triggered drill：
   - `cd /Users/alanzeng/Desktop/Projects/Haven/backend && PYTHONUTF8=1 PYTHONPATH=. python scripts/run_pricing_experiment_guardrail_snapshot.py --metrics-path /tmp/pricing-metrics.json --fail-on-triggered`

## Debug Checklist
1. 使用者分桶不穩定：
   - 檢查 `experiment_key` 是否被意外變更。
2. 變體無流量：
   - 檢查 `growth_ab_experiment_enabled` / `growth_pricing_experiment_enabled`。
3. 應急停用失敗：
   - 檢查 `disable_pricing_experiment` 是否由 server 解析成功。
