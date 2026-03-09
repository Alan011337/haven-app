# P2-F. 離線優先 (Offline-First) — P0 完成對照

本文件對應 RFC-004 與 P2-F 基礎：Local queue + server ack + replay（不碰 CRDT）。

---

## ✅ P0：Local queue + server ack + replay

### 後端 (Idempotency)

| 項目 | 檔案／說明 |
|------|------------|
| 模型 | `backend/app/models/offline_operation_log.py` — `OfflineOperationLog`（user_id, idempotency_key 唯一, operation_type, resource_id, response_payload JSON） |
| Migration | `backend/alembic/versions/g1p2f0000001_offline_operation_logs.py` |
| 服務 | `backend/app/services/offline_idempotency.py` — `normalize_idempotency_key`, `get_replayed_response`, `save_idempotency_response` |
| 日記建立 | `backend/app/api/journals.py` — 支援 `Idempotency-Key` / `X-Request-Id`；replay 回傳 200 + `X-Idempotency-Replayed: true` |
| 卡片回答 | `backend/app/api/routers/cards.py` — `POST /cards/respond` 支援 `Idempotency-Key` |
| 牌組回答 | `backend/app/api/routers/card_decks.py` — `POST /card-decks/respond/{session_id}` 支援 `Idempotency-Key` |

### 前端 (Queue + Replay)

| 項目 | 檔案／說明 |
|------|------------|
| 型別 | `frontend/src/lib/offline-queue/types.ts` — operation_id, type, payload, status (queued \| inflight \| acked \| failed) |
| IndexedDB | `frontend/src/lib/offline-queue/db.ts` — 開 DB、新增、依 status 查詢、更新狀態、刪除；佇列上限 500 筆 |
| Replay | `frontend/src/lib/offline-queue/replay.ts` — `replayOne()` 依 type 呼叫 API 並帶 `Idempotency-Key`；退避 1s/2s/4s… 上限 30s |
| 佇列入口 | `frontend/src/lib/offline-queue/queue.ts` — `enqueue()`, `startReplay()`, `initOfflineReplay()`（監聽 online） |
| 網路判斷 | `frontend/src/lib/offline-queue/network.ts` — `isNetworkError()`（無 response 或 5xx） |
| 日記 | `JournalInput` — 送出帶 `idempotencyKey`；失敗且 `isNetworkError` 時 enqueue journal_create |
| 每日卡 | `DailyCard` — 同上，enqueue card_respond |
| 牌組房 | `useDeckRoom` + `useRespondToDeckCard` — 同上，enqueue deck_respond |
| UI | `OfflineQueueBanner` — 顯示「N 則待同步」「M 則同步失敗」+ 重試；`useOfflineQueueStatus` 訂閱 `haven:offline-queue-change` |
| Bootstrap | `OfflineReplayBootstrap` — 掛載時呼叫 `initOfflineReplay()` |

### PWA

| 項目 | 說明 |
|------|------|
| Manifest | `frontend/public/manifest.json` — name, short_name, start_url, display standalone, theme_color |
| Layout | `app/layout.tsx` — `metadata.manifest: "/manifest.json"` |

---

## 驗收 (DoD)

- 離線或網路失敗時：使用者可提交日記／卡片／牌組回答；寫入進入佇列，UI 顯示「已存到離線，連線後會自動同步」。
- 恢復連線後：自動 replay；成功後 pending 消失；失敗顯示「N 則同步失敗」並可手動重試。
- 重試退避：1s, 2s, 4s… 上限 30s，最多重試 10 次。

---

## ✅ P1：Conflict policy（LWW + time source）

- **Time source**：`X-Client-Timestamp`（ms since epoch），由 client 在 replay 時帶上（queue 的 `created_at_client`）。
- **Journal**：同 user、同 UTC 日已有日記時，若 client 較新則覆寫內容（LWW），否則 409「已由其他裝置更新，以伺服器為準」。
- **Card respond / Deck respond**：已有同 user 的 response 時，若 client 較新則覆寫，否則 409。
- **Client**：replay 時帶 `X-Client-Timestamp`；收到 409 時標記為 failed，錯誤訊息為「已由其他裝置更新，以伺服器為準」。
- **Backend**：`app/services/offline_conflict.py`（`parse_client_timestamp`, `lww_newer_is_client`）；journals / cards / card_decks 在寫入前做 LWW 判斷。

---

## 未實作（後續）

- **P2**：CRDT（Yjs/Automerge）— 僅 RFC，不在此階段實作。

---

## Rollback

- 後端：移除 idempotency 檢查與儲存、revert migration。
- 前端：移除 `offline-queue` 相關程式、`OfflineReplayBootstrap` / `OfflineQueueBanner`、各處 enqueue 與 `idempotencyKey`，恢復僅線上送出。
