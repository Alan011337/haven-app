# ACT-02: Couple Synchronization Nudges

## Why
- 補齊「雙人同步提醒」引擎，降低配對後互動中斷。
- 以後端計算為準，統一提醒觸發規則，避免前端各自猜測。
- 內建 anti-spam（cooldown + dedupe），避免重複打擾。

## How
- Runtime：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/growth_sync_nudge_runtime.py`
  - 觸發條件：
    - `PARTNER_JOURNAL_REPLY`
    - `RITUAL_RESYNC`
    - `STREAK_RECOVERY`
  - Anti-spam：
    - `GET /api/users/sync-nudges` 會檢查最近 delivery 冷卻視窗（預設 18 小時）。
    - `POST /api/users/sync-nudges/{nudge_type}/deliver` 用穩定 `dedupe_key` + DB 唯一鍵防重放。
- API：
  - `GET /api/users/sync-nudges`
  - `POST /api/users/sync-nudges/{nudge_type}/deliver`
- Feature flag / kill-switch：
  - `growth_sync_nudges_enabled`
  - `disable_growth_sync_nudges`

## What
- Schema：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/schemas/growth.py`
- Router：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/users.py`
- 測試：`/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_sync_nudges_api.py`
- Security gate：`/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/security-gate.sh`

## DoD
1. 同步提醒 API 可回傳 nudge 清單、eligible/理由、dedupe_key。
2. delivery endpoint replay-safe：重送不重複寫入。
3. 冷卻機制生效：delivery 後短時間內回到 `cooldown_active`。
4. BOLA/authz 測試包含合法/非法（401、overpost ignored）。
5. kill-switch 可即時關閉功能。

## Test Plan
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_sync_nudges_api.py \
  tests/test_feature_flags.py \
  tests/test_feature_flags_api.py \
  tests/test_endpoint_authorization_matrix_policy.py \
  tests/test_security_gate_contract.py
```

## Failure / Degradation
- 若未配對或 flag 關閉，`GET` 回傳 `enabled=false` 與空列表，不阻斷其他核心流程。
- `deliver` 在條件不符時回 `accepted=false`（例如 `partner_required`, `dedupe_key_mismatch`）。

## Rollback
1. 立即回滾（不需 deploy）：
   - `disable_growth_sync_nudges=true`
2. 程式回退：
   - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/services/growth_sync_nudge_runtime.py`
   - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/users.py`
   - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/schemas/growth.py`
   - `git restore /Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_sync_nudges_api.py`
