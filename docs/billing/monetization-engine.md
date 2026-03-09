# Haven Monetization Engine (P1 Skeleton)

## Why
- 建立以 server 為單一事實來源（source of truth）的訂閱權限（entitlements）與帳務流程。
- 降低 webhook timeout/replay 風暴風險，避免同步處理導致 Stripe 重送放大。
- 提供可驗證、可回滾、可稽核的 billing correctness 基線。

## How
- 訂閱狀態機：
  - `TRIAL -> ACTIVE -> PAST_DUE -> GRACE_PERIOD -> CANCELED`
  - 行為觸發：`START_TRIAL`, `ACTIVATE`, `UPGRADE`, `DOWNGRADE`, `MARK_PAST_DUE`, `ENTER_GRACE_PERIOD`, `CANCEL`, `REACTIVATE`
- 權限模型（server source of truth）：
  - 以 `billing_entitlement_states` 決定目前生效權限。
  - 以 `billing_ledger_entries` 保留 command/webhook 事件帳本。
- Stripe webhook：
  - 驗簽（`Stripe-Signature`）+ 容忍視窗（`BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS`）
  - replay-safe（`provider + event_id` 唯一收據）
  - payload mismatch guard（同 event_id 不同 payload 直接拒絕）
  - refund/chargeback 事件（`charge.refunded`, `charge.dispute.created`）會將 entitlement 轉入 `CANCELED`
- Grace / account hold policy（provider 對齊）：
  - `googleplay.subscription.on_hold` / `appstore.subscription.billing_retry` -> `GRACE_PERIOD`
  - `googleplay.subscription.recovered` / `appstore.subscription.recovered` -> `ACTIVE`
  - command alias `ENTER_ACCOUNT_HOLD` -> `GRACE_PERIOD`
  - policy contract：`/Users/alanzeng/Desktop/Projects/Haven/docs/security/billing-grace-account-hold-policy.json`
- 非同步處理骨架：
  - `BILLING_STRIPE_WEBHOOK_ASYNC_MODE=true` 時，API 先寫入 `QUEUED` 收據後快速回應。
  - 背景 worker 再執行 entitlement/binding/ledger 套用，成功轉 `PROCESSED`，失敗轉 `FAILED`。
  - `false`（預設）維持 inline 處理。
- 對帳：
  - `GET /api/billing/reconciliation` 提供 per-user 對帳結果。
  - `backend/scripts/run_billing_reconciliation_audit.py` 產生 evidence（JSON/MD）。

## What
- API：
  - `POST /api/billing/state-change`
  - `POST /api/billing/webhooks/stripe`
  - `GET /api/billing/reconciliation`
- 主要模型：
  - `billing_command_logs`
  - `billing_webhook_receipts`
  - `billing_entitlement_states`
  - `billing_ledger_entries`
  - `billing_customer_bindings`
- 主要設定：
  - `BILLING_STRIPE_WEBHOOK_SECRET`
  - `BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS`
  - `BILLING_STRIPE_WEBHOOK_ASYNC_MODE`

## DoD
- Webhook 驗簽失敗必拒絕（400），且不能寫入 ledger。
- 同 event replay 要回放既有結果，不重複記帳。
- payload mismatch（同 event_id，不同 payload）必回 409。
- Async mode 開啟時：
  - 首次 webhook 回 `status=QUEUED`
  - 背景處理後轉 `PROCESSED` 或 `FAILED`
  - replay 不得新增重複 ledger。
- `billing reconciliation` 可檢查 command 與 ledger 一致性。
- Entitlement parity 測試（web/iOS/android）需通過：`backend/tests/test_billing_entitlement_parity.py`
- Console drift 監控需通過：`python backend/scripts/run_billing_console_drift_audit.py`
- Grace/account-hold contract 需通過：`python backend/scripts/check_billing_grace_account_hold_policy_contract.py`

## Debug Checklist
1. 驗簽一直失敗：
   - 檢查 `BILLING_STRIPE_WEBHOOK_SECRET` 是否與 Stripe endpoint secret 一致。
   - 檢查伺服器時間誤差，必要時調整 `BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS`。
2. Webhook 卡在 `QUEUED`：
   - 檢查 `BILLING_STRIPE_WEBHOOK_ASYNC_MODE` 是否啟用。
   - 檢查應用是否允許背景任務執行（單機/容器生命週期過短會導致任務未完成）。
3. 收據變成 `FAILED`：
   - 查 audit event：`BILLING_WEBHOOK_DENIED` / `BILLING_WEBHOOK_ERROR`。
   - 檢查 customer/subscription binding 是否衝突或 user identity mismatch。
4. entitlement 與預期不一致：
   - 跑 `python backend/scripts/run_billing_reconciliation_audit.py`。
   - 檢查 `billing_ledger_entries` 的 `source_key` 是否唯一且完整。
5. webhook 設定與策略不一致：
   - 跑 `python backend/scripts/run_billing_console_drift_audit.py`。
   - 驗證 `docs/security/billing-console-drift-policy.json` 與 runtime 設定是否一致。
