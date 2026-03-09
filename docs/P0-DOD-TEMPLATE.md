# P0 DoD Template — 每任務完成定義

> 每個開發項目必須包含下列六項（對應 P0-A META-02）。PR 或 issue 可引用本範本。

---

## 1. 成功定義

- 簡述「完成」的驗收條件（例如：API 回傳 200、某測試通過、文件已更新）。

## 2. 失敗 / 降級行為

- 當條件不滿足時會發生什麼（例如：回傳 4xx/5xx、fallback 到 polling、顯示 warning 不送 email）。

## 3. 觀測點（Log / Metric）

- 哪些 log 或 metric 可確認行為（例如：`rate_limit_block`、`/health` 的某欄位、audit 事件）。

## 4. 測試（Unit / E2E）

- 對應的測試檔與案例（例如：`backend/tests/test_xxx.py::test_yyy`；若有 e2e 請註明路徑與指令）。

## 5. 安全 / 隱私檢查

- 是否涉及 PII、權限、rate limit、BOLA；是否已用 redaction、authz test 或 policy 腳本覆蓋。

## 6. 回滾策略

- 如何還原（例如：revert commit、feature flag 關閉、DB 遷移 downgrade、重啟服務）。

---

**引用**：來自 `docs/p0-execution-protocol.md` § Definition of Done。Launch checklist：`docs/P0-LAUNCH-GATE.md`。
