# Billing Grace / Account Hold Policy

## Why
- 將 `grace period / account hold` 從「口頭規則」變成可驗證契約，避免平台事件造成 entitlement 漂移。
- 讓 Stripe / App Store / Google Play 的暫停扣款情境有一致的 server 判定與回復路徑。

## How
- 以 policy-as-code 固化 provider 對應規則：`/Users/alanzeng/Desktop/Projects/Haven/docs/security/billing-grace-account-hold-policy.json`
- 以 contract gate 驗證：
  - 檔案 schema / references 完整
  - account-hold 一律映射到 `GRACE_PERIOD`
  - recovered 一律映射到 `ACTIVE`
  - cancellation 一律映射到 `CANCELED`
  - runtime router 必須包含指定事件 marker
- 在 billing router 增加 account-hold alias 與 provider 事件 mapping。

## What
- Policy check script:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_billing_grace_account_hold_policy_contract.py`
- Runtime mapping:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/billing.py`
  - `ENTER_ACCOUNT_HOLD -> GRACE_PERIOD`
  - `googleplay.subscription.on_hold -> GRACE_PERIOD`
  - `googleplay.subscription.recovered -> ACTIVE`
  - `appstore.subscription.billing_retry -> GRACE_PERIOD`
  - `appstore.subscription.recovered -> ACTIVE`
- Tests:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_billing_idempotency_api.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_billing_webhook_security.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_billing_grace_account_hold_policy_contract.py`

## DoD
- account-hold 事件可把 entitlement 轉為 `GRACE_PERIOD`。
- recovered 事件可把 entitlement 從 grace/past_due 收斂回 `ACTIVE`。
- canceled 後收到 account-hold 事件必拒絕（409），且不得寫入 ledger。
- contract gate 與 security-gate 必須都會檢查 policy。

## Debug Checklist
1. account-hold 事件未生效：
   - 檢查 webhook `type` 是否為 policy 支援值。
   - 檢查 `billing_customer_bindings` 是否能把 provider customer 映射到 user。
2. recovered 後仍是 `GRACE_PERIOD`：
   - 檢查 recovered 事件是否被 replay 或 signature 驗證失敗。
   - 檢查 webhook transition guard 是否拒絕（查看回應 409 detail）。
3. security-gate 失敗：
   - 先跑 `python backend/scripts/check_billing_grace_account_hold_policy_contract.py` 看 reason。
   - 確認 policy 的 references 檔案路徑存在。
