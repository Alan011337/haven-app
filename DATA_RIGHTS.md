# Data Rights — Access / Export / Erase

> 最小可行實作對應 GDPR 類需求。演練與證據見 `docs/security/data-rights-fire-drill.md`。

---

## 權利與 API

- **Right to Access**：透過既有 API 取得自身與伴侶可見資料；匯出為單一包。
- **Right to Export (Data Portability)**：`GET /api/users/me/data-export`  
  - 回傳當前使用者範圍內之資料包（含 journals、analyses、card 相關、通知等）；結構見 `docs/security/data-rights-export-package-spec.json`。  
  - 下載連結或內容具效期：`expires_at`，預設由 `DATA_EXPORT_EXPIRY_DAYS`（例如 7 天）決定。
- **Right to Erasure**：`DELETE /api/users/me/data`  
  - 刪除當前帳號及與其關聯之資料；伴侶會解除配對。  
  - 可為 soft-delete 或 hard delete，依 `DATA_SOFT_DELETE_*` 設定；見 `docs/security/data-deletion-lifecycle-policy.json`、`data-rights-deletion-graph.json`。

---

## 認證

- 兩支 API 皆需有效 JWT（Bearer token）；僅能操作當前登入使用者自身資料。

---

## 測試與證據

- **單元/整合**：`backend/tests/test_data_rights_api.py`
- **Contract**：`backend/scripts/check_data_rights_contract.py`（export 結構、expiry、deletion graph）
- **演練**：每月執行 data-rights fire drill；證據由 `backend/scripts/validate_security_evidence.py --kind data-rights-fire-drill` 驗證，並在 `backend/scripts/security-gate.sh` 中強制 freshness。

---

## CI 對應

- Security gate 會檢查 data-rights 合約與演練證據有效期限；未通過則 release gate 失敗。
