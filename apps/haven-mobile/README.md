# Haven Mobile (Expo)

React Native / Expo app for Haven. Shares backend and `haven-shared` with the Next.js web app.

## Setup

```bash
cd apps/haven-mobile
npm install
```

Optional: set API base URL via `EXPO_PUBLIC_API_URL` (e.g. in `.env` or EAS env). Default: `http://localhost:8000/api`.

## Run

```bash
npx expo start
```

Then press `i` for iOS simulator or `a` for Android emulator. For physical device, scan the QR code (Expo Go).

## Core Flow（全數完成）

- **登入** (`/login`): Email + 密碼，呼叫後端 `POST /auth/token`，成功後將 token 存入 SecureStore 並導回首頁。
- **日記** (首頁 `/`): 未登入時顯示「請先登入」；登入後可看列表與發布日記。導覽：「今日抽卡」「牌組」「登出」。
- **今日抽卡** (`/daily`): 抽今日共感卡片 → 題目與回答 → 送出後等待伴侶或顯示雙方回答（與 web 每日儀式一致）。
- **牌組** (`/deck`): 選擇牌組分類（八大類）→ 抽卡 → 回答 → 送出；下方顯示最近紀錄（`getDeckHistory`）。

## Structure

- `api/HavenApiNative.ts` – implements `HavenApiClient` (fetch + SecureStore for token/deviceId).
- `app/` – Expo Router screens. `index.tsx` = journal list + create.

## Dependencies

- `haven-shared`: shared types, API contract, query keys (file link to `../../packages/haven-shared`).
