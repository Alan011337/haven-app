# RET-01: First Delight Moment

## Why
- 補齊「first delight moment」里程碑事件，讓成長漏斗可量測首次雙人互動閉環。
- 以 server-side 規則判定是否達成，避免前端自行判定造成漏算或重複事件。
- 內建 dedupe，避免重送導致事件被重複記錄。

## How
- Runtime：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/growth_first_delight_runtime.py`
  - 達成條件（可配置常數）：
    - pair journals >= 2
    - pair card responses >= 2
  - `evaluate_first_delight` 回傳是否 eligible、是否已 delivered、以及 dedupe key。
  - `acknowledge_first_delight` 以穩定 pair dedupe key 寫入 `CujEvent(FIRST_DELIGHT_DELIVERED)`，重送回 `deduped=true`。
- API：
  - `GET /api/users/first-delight`
  - `POST /api/users/first-delight/ack`
- Feature flag / kill-switch：
  - `growth_first_delight_enabled`
  - `disable_growth_first_delight`

## What
- Runtime service：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/growth_first_delight_runtime.py`
- Schema：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/schemas/growth.py`
- Router：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/users.py`
- 測試：`/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_first_delight_api.py`
- Security artifacts：
  - `/Users/alanzeng/Desktop/Projects/Haven/docs/security/endpoint-authorization-matrix.json`
  - `/Users/alanzeng/Desktop/Projects/Haven/docs/security/api-inventory.json`
  - `/Users/alanzeng/Desktop/Projects/Haven/docs/security/growth-kill-switch-coverage.json`

## DoD
1. 可讀取 first delight 狀態（enabled/eligible/delivered/reason/dedupe_key）。
2. ack endpoint replay-safe：同 dedupe key 重送不重複寫入事件。
3. kill-switch 可立即停用功能（回傳 `enabled=false`）。
4. 新 endpoint 有 authz 測試（合法/非法/未登入）。
5. payload 不含 email/token 等 PII。

## Test Plan
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_first_delight_api.py \
  tests/test_feature_flags.py \
  tests/test_feature_flags_api.py \
  tests/test_endpoint_authorization_matrix_policy.py \
  tests/test_security_gate_contract.py
```

## Failure / Degradation
- 未配對、feature 關閉、kill-switch 啟用時：
  - `GET` 回傳 `enabled=false` 與空/安全預設欄位，不阻斷核心 CUJ。
- `POST /ack` 在 dedupe key 不符或無 partner 時：
  - 回 `accepted=false` 與明確 reason。

## Rollback
1. 立即回滾（不需 deploy）：
   - `disable_growth_first_delight=true`
2. 程式回退：
   - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/services/growth_first_delight_runtime.py`
   - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/users.py`
   - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/schemas/growth.py`
   - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_first_delight_api.py`
