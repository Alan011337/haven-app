# Core Loop Metrics (PR-3)

## Why
- 把 PRD v0 的 Daily Core Loop 變成可量測指標：`daily_loop_completion_rate`、`dual_reveal_pair_rate`。
- 提供可重跑 snapshot 腳本，讓 D1 完成率與雙人 reveal 閉環可追溯。

## Snapshot Contract
- Runtime service:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/core_loop_runtime.py`
  - `build_core_loop_snapshot(...)`
  - `evaluate_core_loop_snapshot(...)`
- Script:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_core_loop_snapshot.py`
  - 輸出預設：
    - `docs/growth/evidence/core-loop-snapshot-<timestamp>.json`
    - `docs/growth/evidence/core-loop-snapshot-latest.json`
- Daily workflow:
  - `/Users/alanzeng/Desktop/Projects/Haven/.github/workflows/core-loop-snapshot.yml`
  - 排程：`03:30 UTC`，每日產生 snapshot artifact + latest pointer。

## Metrics Definition
- `daily_loop_completion_rate`
  - 分子：`daily_loop_completed` 去重 user 數
  - 分母：至少觸發一個 core-loop required event 的 active user 數
- `dual_reveal_pair_rate`
  - 分子：同一 pair 在視窗內雙方都觸發 `daily_card_revealed` 的 pair 數
  - 分母：至少一方觸發 `daily_card_revealed` 的 pair 數

## Commands
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_core_loop_snapshot.py --window-days 1
```

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_core_loop_snapshot.py \
  --window-days 1 \
  --min-active-users 20 \
  --target-daily-loop-completion-rate 0.35 \
  --target-dual-reveal-pair-rate 0.2 \
  --fail-on-degraded
```

## DoD
- Runtime tests:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_core_loop_runtime.py`
- Script tests:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_core_loop_snapshot_script.py`
- 驗收命令：
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
ruff check .
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_core_loop_runtime.py \
  tests/test_core_loop_snapshot_script.py
```

## Rollback
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
git restore \
  /Users/alanzeng/Desktop/Projects/Haven/backend/app/services/core_loop_runtime.py \
  /Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_core_loop_snapshot.py \
  /Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_core_loop_runtime.py \
  /Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_core_loop_snapshot_script.py \
  /Users/alanzeng/Desktop/Projects/Haven/docs/growth/core-loop-metrics.md
```
