# P0 Launch Readiness Gate (LAUNCH-01)

> 上線前逐項勾選；每項對應 CI job / 測試名稱 / 文件。對應 `docs/p0-execution-protocol.md` 與 `.github/workflows/release-gate.yml`。

---

## 核心 CUJ SLI 全綠

| 勾選 | 子項 | CI / 測試 / 文件 |
|------|------|------------------|
| ☐ | Bind/Ritual/Journal/Unlock 合成監控 | `GET /health`, `GET /health/slo`；`backend/tests/test_health_endpoint.py`；`docs/ops/uptimerobot-setup.md` |
| ☐ | WS SLI + burn-rate 達標（main 必過） | `backend/scripts/check_slo_burn_rate_gate.py`；`.github/workflows/release-gate.yml`（main 分支） |

---

## OWASP / BOLA 測試全通過

| 勾選 | 子項 | CI / 測試 / 文件 |
|------|------|------------------|
| ☐ | Endpoint + Read Authorization Matrix | `backend/scripts/check_endpoint_authorization_matrix.py`, `check_read_authorization_matrix.py`；`backend/scripts/security-gate.sh` |
| ☐ | 各 resource BOLA 測試 | `test_user_authorization_matrix.py`, `test_journal_authorization_matrix.py`, `test_card_authorization_matrix.py`, `test_card_deck_authorization_matrix.py`, `test_notification_authorization_matrix.py`, `test_billing_authorization_matrix.py`；security-gate.sh |
| ☐ | Token misuse / WebSocket auth | `test_auth_token_misuse_regression.py`, `test_auth_token_misuse_write_paths.py`, `test_websocket_auth_guard.py`；security-gate.sh |
| ☐ | Threat model contract (STRIDE) | `docs/security/threat-model-stride.json`, `backend/scripts/check_threat_model_contract.py`, `backend/tests/test_threat_model_contract_policy.py` |
| ☐ | Abuse economics contract | `docs/security/abuse-economics-policy.json`, `backend/scripts/check_abuse_economics_contract.py`, `backend/tests/test_abuse_economics_contract_policy.py` |
| ☐ | Abuse economics runtime gate | `GET /health/slo -> sli.abuse_economics`；`backend/scripts/check_slo_burn_rate_gate.py`（`abuse_economics_block` 會阻擋 release） |
| ☐ | Prompt abuse policy contract | `docs/security/prompt-abuse-policy.json`, `backend/scripts/check_prompt_abuse_policy_contract.py`, `backend/tests/test_prompt_abuse_policy_contract.py` |
| ☐ | Abuse model contract | `docs/security/abuse-model-policy.json`, `backend/scripts/check_abuse_model_contract.py`, `backend/tests/test_abuse_model_contract_policy.py` |
| ☐ | Encryption posture contract | `docs/security/encryption-posture-policy.json`, `backend/scripts/check_encryption_posture_contract.py`, `backend/tests/test_encryption_posture_contract_policy.py` |
| ☐ | Consent receipt contract | `docs/security/consent-receipt-policy.json`, `backend/scripts/check_consent_receipt_contract.py`, `backend/tests/test_consent_receipt_contract_policy.py` |

---

## Billing 正確性

| 勾選 | 子項 | CI / 測試 / 文件 |
|------|------|------------------|
| ☐ | Idempotency + Ledger 對帳 | `test_billing_idempotency_api.py`, `test_billing_authorization_matrix.py`；`backend/scripts/validate_security_evidence.py --kind billing-reconciliation` |
| ☐ | Webhook 簽章驗證 | `test_billing_webhook_security.py`；`docs/security/billing-webhook-fire-drill.md` |

---

## 事故演練與降級

| 勾選 | 子項 | CI / 測試 / 文件 |
|------|------|------------------|
| ☐ | AI Outage / WS Storm 演練 | `docs/ops/incident-response-playbook.md`；可選 canary guard：`backend/scripts/run_canary_guard.py`, `.github/workflows/canary-guard.yml` |
| ☐ | Push/WS 降級（Fallback polling/inbox） | 文件/設計在 incident-response；前端 polling 已存在（通知） |

---

## Data Rights 演練完成

| 勾選 | 子項 | CI / 測試 / 文件 |
|------|------|------------------|
| ☐ | Access/Export/Erase 端到端 | `GET /api/users/me/data-export`, `DELETE /api/users/me/data`；`backend/tests/test_data_rights_api.py`；`docs/security/data-rights-fire-drill.md` |
| ☐ | 證據 freshness gate | `validate_security_evidence.py --kind data-rights-fire-drill`；security-gate.sh |

---

## Legal / Age / 內容

| 勾選 | 子項 | CI / 測試 / 文件 |
|------|------|------------------|
| ☐ | Age gating + 條款同意 | 註冊頁勾選「已滿 18 歲並同意服務條款與隱私權政策」；`/legal/terms`、`/legal/privacy` |
| ☐ | Legal compliance bundle contract | `docs/security/legal-compliance-bundle.json` + `backend/scripts/check_legal_compliance_bundle_contract.py` + `backend/tests/test_legal_compliance_bundle_contract_policy.py` |
| ☐ | Consent receipt 實際落庫 | `POST /api/users/` 需 `age_confirmed` + version；`backend/tests/test_user_consent_receipt_api.py`（`USER_CONSENT_ACK`） |
| ☐ | Legal stub 版本化 | `docs/legal/PRIVACY_POLICY.md`、`docs/legal/TERMS_OF_SERVICE.md`（version + 日期） |
| ☐ | Store compliance matrix | `docs/security/store-compliance-matrix.json` + `backend/scripts/check_store_compliance_contract.py` + `backend/tests/test_store_compliance_contract_policy.py` |
| ☐ | Secrets / key management contract + drill | `docs/security/secrets-key-management-policy.json` + `docs/security/keys.md` + `scripts/key-rotation-drill.sh` + `backend/scripts/check_secrets_key_management_contract.py` + `backend/scripts/validate_security_evidence.py --kind key-rotation-drill` + `backend/tests/test_secrets_key_management_contract_policy.py` |
| ☐ | 八大牌組 seed 驗證 | `npm run seed:cards:validate`（可加 `--strict` 強制每類 ≥ SEED_MIN_PER_CATEGORY） |

## Review readiness

| 勾選 | 子項 | CI / 測試 / 文件 |
|------|------|------------------|
| ☐ | Demo flow 可跑 | 手動或 e2e：註冊 → 配對 → 日記/抽卡 → 解鎖 |
| ☐ | Paywall / 付費揭露 | 產品/法遵確認；可連結 `docs/legal/TERMS_OF_SERVICE.md` |

---

## 本地一鍵檢查

```bash
./scripts/release-gate.sh
```

- 含：`backend/scripts/check_env.py` → `backend/scripts/security-gate.sh` → `check_slo_burn_rate_gate.py` → `pytest` → frontend `check:env` + `typecheck`
- 含 launch signoff artifact freshness gate：`backend/scripts/check_launch_signoff_gate.py`（預設 max age 14 天，可用 `LAUNCH_SIGNOFF_MAX_AGE_DAYS` 調整）
- launch signoff required checks 必含：`release_checklist_complete`、`launch_gate_complete`、`store_compliance_contract_passed`、`release_gate_local_runtime`
- 含 CUJ synthetic evidence freshness gate：`backend/scripts/check_cuj_synthetic_evidence_gate.py`（預設 max age 36 小時，可用 `CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS` 調整；`main` 預設 fail-closed）
- 可先刷新 CUJ synthetic evidence：`bash scripts/generate-cuj-synthetic-evidence-local.sh`
- 可選含 frontend e2e：`RUN_E2E=1 ./scripts/release-gate.sh`
- P0 readiness 稽核（預設 contract mode，清單 open items 只做觀測不阻擋）：
  - 快速版：`bash scripts/p0-readiness-audit.sh`
  - 嚴格清單版：`P0_READINESS_MODE=checklist bash scripts/p0-readiness-audit.sh`
  - 含 runtime gate：`RUN_RUNTIME_GATES=1 bash scripts/p0-readiness-audit.sh`
  - 輸出：`docs/security/evidence/p0-readiness-latest.json`（含 open items 的檔案/行號/內容）

## Safety regression（P0-I）

| 勾選 | 子項 | CI / 測試 / 文件 |
|------|------|------------------|
| ☐ | AI JSON schema contract | `backend/tests/test_ai_schema_contract.py` |
| ☐ | AI JSON schema fuzz | `backend/tests/test_ai_schema_fuzz.py` |
| ☐ | AI safety 邏輯 | `backend/tests/test_ai_safety_logic.py` |
| ☐ | 上述納入 security-gate | `backend/scripts/security-gate.sh` 已列為必跑 |

## AI Ops / Eval（P0-I）

| 勾選 | 子項 | CI / 測試 / 文件 |
|------|------|------------------|
| ☐ | Prompt rollout policy contract | `docs/security/prompt-rollout-policy.json`, `backend/scripts/check_prompt_rollout_policy_contract.py`, `backend/tests/test_prompt_rollout_policy_contract.py` |
| ☐ | Human + Auto eval framework contract | `docs/security/ai-eval-framework.json`, `backend/scripts/check_ai_eval_framework_contract.py`, `backend/tests/test_ai_eval_framework_contract_policy.py` |

## CUJ e2e（P0-I）

| 勾選 | 子項 | CI / 測試 / 文件 |
|------|------|------------------|
| ☐ | 前端 smoke e2e | `frontend/e2e/smoke.spec.ts`（註冊/登入/legal 頁） |
| ☐ | 本地執行 | `cd frontend && npm run test:e2e`（需先 `npm run dev` 或 `npm run start`）；首次可用 `npm run test:e2e:auto` 自動安裝 Chromium。若走 local gate：`RUN_E2E=1 E2E_BASE_URL=http://localhost:3000 bash scripts/release-gate-local.sh`（可用 `E2E_AUTO_INSTALL_BROWSER=0` 關閉自動安裝；預設先做 URL probe，可透過 `E2E_BASE_URL_PROBE_PATH` / `E2E_BASE_URL_PROBE_TIMEOUT_SECONDS` 調整） |
| ☐ | CI 漸進 gate | `.github/workflows/release-gate.yml` 內 `frontend-e2e`（PR 可容錯、main 必過） |

## 文件與流程

| 項目 | 路徑 |
|------|------|
| AI 功能告知與邊界 | 根目錄 `POLICY_AI.md` |
| PR 必填（DoD 對照） | `.github/PULL_REQUEST_TEMPLATE.md` |
| CI 故障排查對照 | `RUNBOOK.md` 的「CI Gate 故障對照」章節 |
| 最終上線簽核 | `docs/FINAL_P0_SIGNOFF.md` |

## CI 入口

- **Workflow**：`.github/workflows/release-gate.yml`（PR + push to main）
- **Security gate 詳單**：`backend/scripts/security-gate.sh`
