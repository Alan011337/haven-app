# Billing Store Compliance Matrix (P1)

## Why
- 避免 Web/iOS/Android 付費路徑違反平台政策，降低下架與審核失敗風險。
- 統一產品、後端 entitlement、與商店規範的對照依據。

## How
- 採 server entitlement 判定，平台端僅作為付款來源。
- 以「平台允許/禁止」矩陣管理 UI 行為與導流策略。
- 高風險區塊（訂閱升降級、取消、重複扣款）全部由 webhook + reconciliation 驗證。

## What
| 平台 | 可用支付通道 | 不可做法 | Haven 實作策略 |
| --- | --- | --- | --- |
| Web | Stripe Checkout / Portal | 無 | Web 走 Stripe，結果以 server entitlement 生效 |
| iOS | App Store IAP (訂閱/數位內容) | App 內直接導外部支付購買數位權益 | iOS 客戶端只顯示 IAP 方案，server 做 entitlement parity |
| Android | Google Play Billing (訂閱/數位內容) | App 內繞過 Play 支付購買數位權益 | Android 客戶端只顯示 GP 方案，server 做 entitlement parity |

## DoD
- Web/iOS/Android 的 entitlement 結果在 server 層一致（parity）。
- 同一 user 透過 Web/iOS/Android 不同來源進入 billing 流程時，entitlement 仍收斂為單一正確狀態（same-user parity）。
- 任一平台 replay webhook/event 不得重複記帳或重複升權。
- Store policy 更新時，可在此文件直接定位受影響流程與 owner。
- 自動化 parity 測試：`/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_billing_entitlement_parity.py`

## Local verify
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_billing_entitlement_parity.py \
  tests/test_store_compliance_contract_policy.py
```

## Debug Checklist
1. 使用者反映「已付款但未升權」：
   - 查 `billing_webhook_receipts` 是否有對應 event。
   - 查 `billing_ledger_entries` 是否有對應 `source_key`。
   - 跑 reconciliation audit 確認是否缺 ledger。
2. 權限跨平台不一致：
   - 比對同一 user 的 entitlement state/revision 與最近 ledger。
   - 確認 iOS/Android/Web 客戶端都改為讀 server entitlement。
3. 審核卡關（iOS/Android）：
   - 先檢查是否仍在 app 內露出外部 web 支付導流。
   - 檢查文案是否清楚揭露訂閱條款與取消方式。
