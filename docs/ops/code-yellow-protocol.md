# OPS-CULT-01 The "Code Yellow" Protocol（黃色代碼協議）

**P2-J**：當核心指標跌破閾值，全公司停止新功能開發，專注修復品質與效能。

## 觸發條件

當以下任一項成立時，宣布 **Code Yellow**：

- **SLO 連續違反**：例如 WS 連線接受率、訊息傳遞率、HTTP 錯誤率或延遲，在定義的時間窗口內持續超過閾值（見 `docs/sre/`、`/health/slo`）。
- **Error budget 耗盡**：當月/當週 error budget 用罄，且無已排程的修復。
- **Release gate 連續失敗**：主線 release gate 或 security gate 連續 N 次失敗，且無明確排除原因。
- **重大資安/合規事件**：經評估需全員優先修復。

（實際閾值與窗口以 `docs/sre/service-tier-policy.json` 與 runbook 為準。）

## 協議內容

1. **凍結功能開發**：暫停與新功能、新需求相關的 merge；僅允許修復品質、效能、安全與合規的變更。
2. **優先修復**：工程與 oncall 優先處理：  
   - 恢復 SLO / error budget；  
   - 修復導致 release gate 失敗的項目；  
   - 完成資安/合規補救。
3. **溝通**：在既定管道（Slack/Issue/All-hands）宣布 Code Yellow 與解除時間；每日更新進度直到解除。
4. **解除條件**：核心指標回到安全範圍、release gate 通過、且負責人簽核後，宣布解除 Code Yellow。

## 與現有機制對齊

- **Release freeze**：現有 release gate 與 tier policy 已支援「凍結發布」；Code Yellow 可視為全公司層級的凍結與優先級調整。
- **Chaos / 演練**：Chaos 演練與 incident playbook 用於「提前發現弱點」；Code Yellow 用於「事後集中修復」。

## 後續

- 將觸發閾值寫入 `docs/sre/` 或 config，並與監控/告警整合。
- 每年至少一次 tabletop 演練 Code Yellow 宣布與解除流程。
