# P2-J. 進階 Ops 完成對照

**目標**：Multi-region 準備、Chaos Engineering Pipeline、Code Yellow 協議。

---

## Ops-01 Multi-region Readiness

| 項目 | 說明 |
|------|------|
| **文件** | [docs/ops/multi-region-readiness-roadmap.md](./ops/multi-region-readiness-roadmap.md) |
| **內容** | 多區域部署路線圖與檢查清單（無狀態應用、DB 拓樸、Redis/CDN、健康與路由、資料在地化、災難復原）。現狀為單區 + read replica 就緒；多區主庫留待 Phase 2+。 |

---

## OPS-04 Chaos Engineering Pipeline

| 項目 | 說明 |
|------|------|
| **既有** | Chaos drill 已整合 CI：`.github/workflows/chaos-drill.yml`（每週五 UTC 09:00 = 台灣下午 17:00）、`scripts/chaos-drill.sh`、`backend/scripts/run_chaos_drill_audit.py`、evidence 驗證。 |
| **Vicky Disconnect** | 在 [chaos-drill-spec.md](./ops/chaos-drill-spec.md) 與 [incident-response-playbook.md](./ops/incident-response-playbook.md) 中新增「Vicky Disconnect」演練：每週五下午 tabletop/乾跑，模擬伴侶/連線中斷，驗證降級、重連與通知。 |
| **反脆弱** | 演練確保系統在故障注入下可降級與回復；失敗時 CI 上傳 artifacts 並建立/更新 alert issue。 |

---

## OPS-CULT-01 Code Yellow Protocol（黃色代碼協議）

| 項目 | 說明 |
|------|------|
| **文件** | [docs/ops/code-yellow-protocol.md](./ops/code-yellow-protocol.md) |
| **內容** | 觸發條件（SLO 連續違反、error budget 耗盡、release gate 連續失敗、重大資安/合規）；協議內容（凍結功能開發、優先修復、溝通、解除條件）；與 release freeze、Chaos 演練對齊。 |
