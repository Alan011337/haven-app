# P2-G. React Native / Expo 遷移評估 [Native-01]

**目標**：從「能用」到「絲滑到離不開」，建立移動端霸權。  
**範圍**：Core Flow（抽卡、日記）移植到 React Native 的路徑評估，共用後端與邏輯層。

---

## 1. 評估結論摘要

| 項目 | 評估 |
|------|------|
| **可行性** | ✅ 高。後端已就緒；前端 Core Flow 邊界清楚，可透過 `haven-shared` 共用類型與 API 契約。 |
| **建議時機** | Phase 1.5 平行軌道（與現有 Next.js 迭代並行）。 |
| **建議技術** | **Expo**（SDK 52+），React Native 之上，利於 OTA、建置、權限與 PWA 經驗延續。 |
| **風險** | 中。需處理 RN 與 React 19 相容性、離線佇列在 RN 的儲存與 replay、推送與深鏈。 |

---

## 2. Core Flow 範圍

以下為「Core Flow」—— 必須在 native 上絲滑運作、與後端及共用邏輯對齊的流程。

| 流程 | 說明 | 後端 API | 共用層 |
|------|------|----------|--------|
| **日記** | 撰寫、列表、刪除、伴侶日記、安全分級 | `POST/GET/DELETE /journals/`、`GET /journals/partner` | `haven-shared` types + `HavenApiClient.createJournal/getJournals/...` |
| **每日抽卡** | 抽卡、回答、解鎖、等待伴侶 | `GET /cards/daily-status`、`GET /cards/draw`、`POST /cards/respond` | 同上 + `getDailyStatus`、`drawDailyCard`、`respondDailyCard` |
| **牌組房** | 選分類、抽卡、回答、歷史 | `POST /card-decks/draw`、`POST /card-decks/respond/:id`、`GET /card-decks/history` | 同上 + `drawDeckCard`、`respondToDeckCard`、`getDeckHistory` |

其餘（登入、設定、通知、計費、回憶長廊等）可列為 Phase 2 或漸進遷移。

---

## 3. 共用後端與邏輯層

- **後端**：無需為 native 另開 API；現有 REST + Idempotency-Key + 409 LWW 已可支援多端。
- **邏輯層**：
  - **已準備**：`packages/haven-shared`（types、api-types、query-keys、`HavenApiClient` 介面）。
  - **Web 實作**：`frontend/src/lib/api.ts`（axios）+ `frontend/src/services/api-client.ts` 等，可逐步對齊 `HavenApiClient`。
  - **Native 實作**：新建 `HavenApiNative` 實作 `HavenApiClient`，以 `fetch` + `AsyncStorage`（token、deviceId）、必要時加上離線佇列（AsyncStorage 或 RN 端 IndexedDB 替代）。

---

## 4. 遷移路徑（建議）

### Phase 1.5 平行軌道

1. **共用包穩定**
   - 維持並擴充 `haven-shared`（型別、API 契約、query-keys）。
   - 前端在可接受時機改為從 `haven-shared` 匯入型別與 query-keys，並讓現有 api-client 符合 `HavenApiClient` 介面（適配層即可）。

2. **Expo 專案建立**
   - 使用 `npx create-expo-app@latest`（Expo SDK 52+）。
   - 專案名建議：`apps/haven-mobile` 或 `mobile`，與 `frontend`、`packages/haven-shared` 並列。
   - 依賴：`haven-shared`、`@tanstack/react-query`、`expo-secure-store`（或 AsyncStorage）、`expo-auth-session`（若 OAuth）。

3. **Core Flow 移植順序**
   - **日記**：登入後首屏或 Tab「日記」→ 列表 + 撰寫 + 刪除（呼叫 `createJournal`、`getJournals`、`deleteJournal`）。
   - **每日抽卡**：Tab「今日」→ `getDailyStatus` / `drawDailyCard` / `respondDailyCard`，UI 依設計稿用 RN 元件重做。
   - **牌組房**：選分類 → `drawDeckCard` → 回答 → `respondToDeckCard`，歷史 `getDeckHistory`。

4. **每步產物**
   - 實作 `HavenApiNative`（fetch + token/deviceId 從 SecureStore/AsyncStorage 讀取）。
   - 螢幕級元件（JournalList, JournalInput, DailyCardScreen, DeckRoomScreen）僅依賴 `HavenApiClient` 與 `haven-shared` 型別，不依賴 Next.js 或 web-only API。

---

## 5. 技術要點

| 議題 | 說明 |
|------|------|
| **React 19** | Expo/React Native 對 React 19 的支援需查當時版本文檔；若尚未穩定，可暫用 React 18 與對應 Expo SDK。 |
| **認證** | Token 存於 `expo-secure-store` 或 AsyncStorage；登入頁可先用帳密呼叫既有 backend 登入 API，之後再考慮 OAuth/深鏈。 |
| **離線佇列** | P2-F 離線佇列目前為 web IndexedDB；RN 端可用 AsyncStorage 或 `expo-sqlite` 存 operation queue，replay 邏輯與 `haven-shared` 無關，可複用規則（Idempotency-Key、X-Client-Timestamp）。 |
| **推送** | 沿用後端 Web Push 契約；RN 使用 FCM/APNs，需後端支援 device token 與 channel 區分。 |
| **深鏈** | Expo 使用 `expo-linking`；與後端或 web 的 invite/notification 連結對齊 scheme。 |

---

## 6. 工作量粗估（僅供 Phase 1.5 規劃）

| 階段 | 內容 | 人天（粗估） |
|------|------|----------------|
| 共用包與前端對齊 | 穩定 haven-shared、frontend 改用其 types/queryKeys、實作 HavenApiClient 適配 | 2–3 |
| Expo 專案與 API 層 | 新建 app、HavenApiNative、登入/登出、token 儲存 | 2–3 |
| 日記 Core Flow | 列表 + 撰寫 + 刪除 + 伴侶日記（僅讀） | 3–5 |
| 每日抽卡 Core Flow | 狀態、抽卡、回答、解鎖、等待伴侶 | 3–5 |
| 牌組房 Core Flow | 分類、抽卡、回答、歷史 | 3–5 |
| 離線/推送/深鏈 | 依產品優先級分階段 | 5+ |

*以上為單人全端粗估，實際依團隊與設計變更調整。*

---

## 7. DoD（Phase 1.5 可驗收條件）

- [x] `haven-shared` 可被 frontend 與 mobile 依賴，型別與 API 契約一致。
- [x] Expo 專案已建立（`apps/haven-mobile`），實作 `HavenApiNative`，可呼叫後端 journals API（需 token，目前可經 web 登入後取得或後續加登入頁）。
- [x] Core Flow：日記 在 native 上可完成列表 + 發布端到端（有 token 時）。
- [x] 文件：本評估已執行；Expo 專案 scaffold 見 `apps/haven-mobile/README.md`。

---

## 8. 參考

- 共用包：`packages/haven-shared/README.md`
- 後端 API：`backend/app/api/`、`docs/` 下相關 API 說明
- P2-F 離線：`docs/P2-F-OFFLINE-FIRST-COMPLETE.md`、RFC-004
