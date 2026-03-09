# P2-G. 原生轉型準備 (Native Transition) 完成對照

**目標**：從「能用」到「絲滑到離不開」，建立移動端霸權；提早準備 React Native 共用邏輯並將遷移評估提前至 Phase 1.5。

---

## ✅ [Native First] Shared Logic Monorepo

| 項目 | 說明 |
|------|------|
| **套件** | `packages/haven-shared`：與 Next.js 前端、未來 React Native/Expo 共用。 |
| **內容** | **types**（Journal, User, Card, CardCategory）、**api-types**（CreateJournalOptions, PartnerStatus, DeckHistoryEntry, CreateJournalResponse, 等）、**query-keys**（TanStack Query key factory）、**HavenApiClient**（transport-agnostic API 介面）。 |
| **建置** | `cd packages/haven-shared && npm install && npm run build` → `dist/`（CJS + ESM + d.ts）。 |
| **消費** | 前端已加入依賴 `"haven-shared": "file:../packages/haven-shared"`，`frontend/src/types/index.ts` 與 `frontend/src/lib/query-keys.ts` 改為 re-export 自 `haven-shared`；Next 設定 `transpilePackages: ['haven-shared']`。Expo 專案同樣依賴此套件並實作 `HavenApiClient` 即可。 |

---

## ✅ [Native-01] React Native / Expo 遷移評估

| 項目 | 說明 |
|------|------|
| **文件** | [P2-G-NATIVE-EXPO-MIGRATION-EVALUATION.md](./P2-G-NATIVE-EXPO-MIGRATION-EVALUATION.md) |
| **結論** | 可行；建議 Phase 1.5 平行軌道、Expo SDK 52+；Core Flow = 日記 + 每日抽卡 + 牌組房，共用後端與 `haven-shared`。 |
| **路徑** | 共用包穩定 → 新建 Expo app → 實作 HavenApiNative → 依序移植日記、每日抽卡、牌組房。 |
| **風險** | React 19 與 RN 相容性、離線佇列在 RN 的儲存、推送與深鏈。 |

---

## ✅ Expo 專案（Phase 1.5）— Core Flow 全數完成

| 項目 | 說明 |
|------|------|
| **位置** | `apps/haven-mobile` |
| **HavenApiNative** | `api/HavenApiNative.ts`：實作 `HavenApiClient`（fetch + expo-secure-store），對接既有後端 API。 |
| **登入** | `app/login.tsx`：Email + 密碼 → `POST /auth/token`，token 存 SecureStore，導回首頁。 |
| **日記** | `app/index.tsx`：列表 + 發布（`getJournals` / `createJournal`）；首頁導覽「今日抽卡」「牌組」「登出」。 |
| **今日抽卡** | `app/daily.tsx`：`getDailyStatus` / `drawDailyCard` / `respondDailyCard`，與 web 每日儀式一致。 |
| **牌組房** | `app/deck.tsx`：選擇牌組分類 → `drawDeckCard(category)` → 回答 → `respondToDeckCard`；下方「最近紀錄」`getDeckHistory`。 |
| **執行** | `cd apps/haven-mobile && npm install && npx expo start`；可設 `EXPO_PUBLIC_API_URL` 指向後端。 |

## 後續（可選）

- 離線佇列：在 RN 端以 AsyncStorage 或 SQLite 實作 P2-F 佇列與 replay。
- 推送／深鏈：後端支援 device token，Expo 設定 scheme 與 deep links。
