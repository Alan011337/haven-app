# Growth NSM (P1)

## Why
- NSM 採用 `WRM (Weekly Relationship Moments)`，直接衡量「雙方互動閉環」，避免只看流量或單邊活躍。
- 這個指標是成長與留存共同 guardrail：若 WRM 下滑，優先修復互動體驗而非堆疊曝光。

## How
- 伺服器端以 `cuj_events` 做 rolling 7 天計算（UTC）：
  - 檔案：`/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/growth_nsm_runtime.py`
  - `build_growth_nsm_snapshot(...)`：彙整 eligible events、pair 去重、雙方參與判定、WRM 比率。
  - `evaluate_growth_nsm_snapshot(...)`：輸出 `pass/degraded/insufficient_data`（不阻斷核心 CUJ）。
- 每日 snapshot job：
  - 檔案：`/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_growth_nsm_snapshot.py`
  - 輸出：`docs/growth/evidence/wrm-snapshot-*.json` 與 `wrm-snapshot-latest.json`
- 每日 workflow：
  - 檔案：`/Users/alanzeng/Desktop/Projects/Haven/.github/workflows/growth-nsm-snapshot.yml`
  - 排程：`03:20 UTC`，執行 snapshot 並上傳 artifact。

## What
- 定義版本：`WRM_DEFINITION_VERSION=1.0.0`
- 計算視窗：預設 `7` 天，可透過 `--window-days` 覆蓋。
- 目前 eligible event 最小集合（server 來源）：
  - `RITUAL_RESPOND`
  - `RITUAL_UNLOCK`
  - `JOURNAL_SUBMIT`
  - `JOURNAL_ANALYSIS_DELIVERED`
- Pair 判定：
  - 對同一 pair（normalized `user_id:partner_user_id`）累積事件。
  - 該 pair 在視窗內需觀測到「雙方 actor 都出現」才算 `WRM`。
- 觀測輸出：
  - `counts.active_pairs_observed_total`
  - `counts.wrm_pairs_total`
  - `metrics.wrm_active_pair_rate`
  - `counts.events_by_name`
  - `evaluation.status/reasons`

## DoD
- Daily snapshot 會自動產生且可追溯（workflow artifact + latest pointer）。
- WRM 計算邏輯有單元測試覆蓋雙方參與/單邊/低樣本降級。
- 指標輸出不包含 raw PII（僅摘要指標與 pair fingerprint sample）。

## Local Runbook
1. 產生 snapshot：
   - `cd /Users/alanzeng/Desktop/Projects/Haven/backend && PYTHONUTF8=1 PYTHONPATH=. python scripts/run_growth_nsm_snapshot.py --window-days 7`
2. 調整門檻 dry-run：
   - `cd /Users/alanzeng/Desktop/Projects/Haven/backend && PYTHONUTF8=1 PYTHONPATH=. python scripts/run_growth_nsm_snapshot.py --window-days 7 --min-events 20 --min-pairs 5 --target-wrm-active-pair-rate 0.35`
3. 強制 degraded 失敗（演練 gate）：
   - `cd /Users/alanzeng/Desktop/Projects/Haven/backend && PYTHONUTF8=1 PYTHONPATH=. python scripts/run_growth_nsm_snapshot.py --window-days 7 --min-events 1 --min-pairs 1 --target-wrm-active-pair-rate 1.0 --fail-on-degraded`

## Debug Checklist
1. `wrm_pairs_total` 異常下降：
   - 先查 `counts.events_by_name` 是否某類事件掉量（可能是前端事件漏送）。
2. `active_pairs_observed_total` 正常但 `wrm_active_pair_rate` 降低：
   - 檢查是否變成單邊互動（`one_sided_pairs_total` 上升）。
3. 與 BI 報表不一致：
   - 對齊 UTC 視窗與 eligible event 集合版本（`definition_version`）。

## Rollback
- 關閉每日 job：停用 workflow `growth-nsm-snapshot.yml`。
- 保留 runtime 但不執行：停止排程即可，不影響核心 API。
- 若需快速回退程式：`git restore /Users/alanzeng/Desktop/Projects/Haven/backend/app/services/growth_nsm_runtime.py /Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_growth_nsm_snapshot.py /Users/alanzeng/Desktop/Projects/Haven/.github/workflows/growth-nsm-snapshot.yml /Users/alanzeng/Desktop/Projects/Haven/docs/growth/nsm.md`
