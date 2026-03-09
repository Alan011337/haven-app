# AI Cost & Quality Monitor（P1-I 基線）

## 目的
- 以低風險方式建立 AI 成本與品質監控基線，不阻塞核心 CUJ。
- 提供可執行的 drift/cost 快照輸出，供 release 與營運稽核。

## 指標（最小集）
- `schema_compliance_rate`（目標 >= 99.9）
- `hallucination_proxy_rate`（目標 <= 0.05）
- `avg_tokens_per_analysis`（觀察）
- `estimated_cost_usd_per_active_couple`（目標 <= 1.5）
- `drift_score`（相對變動平均；目標 <= 0.2）

## 執行腳本
- `backend/scripts/run_ai_quality_snapshot.py`
- `backend/scripts/fetch_latest_ai_quality_snapshot_evidence.py`
- `backend/scripts/check_ai_quality_snapshot_freshness_gate.py`
- `backend/scripts/run_ai_eval_drift_detector.py`

範例（baseline 回退模式）：

```bash
cd backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/run_ai_quality_snapshot.py \
  --allow-missing-current \
  --output /tmp/ai-quality-snapshot.json
```

## 輸出
- JSON artifact（預設輸出到 `docs/security/evidence/ai-quality-snapshot-*.json`）
- `latest` 指標檔：`docs/security/evidence/ai-quality-snapshot-latest.json`
- Drift detector artifact：`docs/security/evidence/ai-eval-drift-*.json`
- Drift detector `latest`：`docs/security/evidence/ai-eval-drift-latest.json`
- 主要欄位：
  - `generated_at`
  - `thresholds`
  - `baseline`
  - `current`
  - `evaluation.result` (`pass`/`degraded`)
  - `evaluation.degraded_reasons`

## 降級策略
- 若品質或成本超標：標記 `degraded` 並觸發告警/降模型建議。
- `degraded` 僅降級，不阻斷核心 CUJ / journal write。
- release gate 僅在 evidence 缺失/過舊/契約無效時阻擋；`degraded` 會顯示在 summary 但不 fail job。

## CI / Daily cadence
- Daily workflow: `.github/workflows/ai-quality-snapshot.yml`
  - 每日產出 timestamped snapshot + `latest` pointer。
  - 執行 freshness + contract gate。
  - 執行 drift detector（threshold: `drift_score_max`; `critical` 使用 `1.5x` multiplier）。
  - 若結果為 `degraded`，自動開/更新 tracking issue（非阻斷，供後續修復）。
  - 若恢復 `pass`，自動關閉既有 degraded tracking issue。
  - 若 drift detector 為 `degraded/critical`，會開/更新 `[P1][AI] Drift detector alert`（同樣 non-blocking）。
- Release workflow: `.github/workflows/release-gate.yml`
  - 先抓取最近一次 daily workflow artifact 中的 `ai-quality-snapshot-latest.json` 到 `/tmp/ai-quality-snapshot-latest.json`。
  - 再跑 freshness gate 並輸出 summary（含 evidence source run/artifact 與 non-blocking degraded 註記）。
- Local script: `scripts/release-gate.sh`
  - 預設 `RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE=local_snapshot`（本機生成快照）。
  - 可切換 `RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE=daily_artifact` 以對齊 CI；必要時搭配 `RELEASE_GATE_AI_QUALITY_EVIDENCE_REPO=<owner/repo>`。
  - 會輸出 `ai quality summary`（`source_result` / `gate_result` / `evaluation_result` / `evidence_age_hours`）供 triage。
- Local script: `scripts/release-gate-local.sh`
  - 與 `release-gate.sh` 相同，支援 `RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE=local_snapshot|daily_artifact`。
  - 若使用 `daily_artifact` 且來源暫時不可得，可配合 `RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE=1` 做非阻斷本機演練。
  - 會輸出 `ai quality summary`（`source_result` / `gate_result` / `evaluation_result` / `evidence_age_hours`）供值班快速判讀是來源問題或新鮮度問題。
  - `daily_artifact` 模式會先清除舊的 `/tmp/ai-quality-snapshot-latest.json`，避免誤用過期證據造成假綠燈。
