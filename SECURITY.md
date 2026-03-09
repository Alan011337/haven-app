# Security — Haven

> 漏洞回報、安全基線與 CI 對應。詳盡對照見 `docs/security/owasp-api-top10-mapping.md`。

---

## 漏洞回報

若發現安全問題，請勿在公開 issue 張貼細節。請以私密方式聯繫維護者（或透過 repository 的 Security policy），我們會盡快確認並回覆。

---

## 安全基線（P0）

- **認證與授權**：JWT、self/partner 存取邊界、BOLA 測試覆蓋；見 `docs/security/endpoint-authorization-matrix.json`、`read-authorization-matrix.json`。
- **Rate limit / WS abuse**：寫入路徑與 WebSocket 限流與 backoff；`backend/app/services/rate_limit.py`、`ws_abuse_guard.py`；abuse 政策：`docs/security/abuse-budget-policy.md`。
- **Billing**：Idempotency、Webhook 簽章驗證、Ledger 對帳；evidence 由 CI 驗證 freshness。
- **Data rights**：Export/Erase API、演練與證據；`docs/security/data-rights-fire-drill.md`、`DATA_RIGHTS.md`。
- **Field-level encryption**：高敏感文字欄位採透明加密（`backend/app/core/field_encryption.py`），由 `FIELD_LEVEL_ENCRYPTION_*` 控制與 `check_env.py` 驗證。
- **Device/session hardening**：refresh token rotation + replay revoke + device binding；`docs/security/device-session-hardening.md`。

---

## Secrets 與 Key 管理

- **原則**：敏感值僅透過環境變數注入，不寫入程式碼、不進 log/trace。
- **環境分離**：開發/測試與生產使用不同 `.env` 與 key；生產 key 不提交至 repo。
- **輪替**：`SECRET_KEY`、`OPENAI_API_KEY`、`RESEND_API_KEY`、`BILLING_STRIPE_*` 等應有輪替計畫；輪替後需重啟服務或依各服務文件更新。
- **加密鍵**：`FIELD_LEVEL_ENCRYPTION_KEY` 使用 Fernet 44-char base64 key；`ENV=production` 時必須啟用 `FIELD_LEVEL_ENCRYPTION_ENABLED=true`。
- **檢查**：啟動前執行 `backend/scripts/check_env.py`；CI 在 `release-gate` 中執行。

---

## CI 安全閘門

- **Workflow**：`.github/workflows/release-gate.yml`
- **Backend 安全 gate**：`backend/scripts/security-gate.sh`（authorization matrix、evidence freshness、BOLA/rate limit 等測試）。
- **Evidence 驗證**：`backend/scripts/validate_security_evidence.py`（p0-drill、data-rights、billing、audit、soft-delete 等）。

---

## 相關文件

- OWASP API Top 10 對照（canonical）：`docs/security/owasp-api-top10-mapping.md`
- OWASP API Top 10 對照（checklist path alias）：`docs/security/owasp_api_top10_mapping.md`
- API 清單與負責：`docs/security/api-inventory.json`、`api-inventory-owner-attestation.json`
- Launch checklist：`docs/P0-LAUNCH-GATE.md`
- AI 功能告知與邊界：根目錄 `POLICY_AI.md`
