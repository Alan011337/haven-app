# 📂 Document 3: Roadmap (The Execution Plan)

**檔案名稱：** `03_``[Roadmap.md](Roadmap.md)` 

**目標：** 從零打造 Haven 2.0 正式版 (Next.js + FastAPI + Supabase)。 

**最後更新：** 2026-02-04 (Migrated to Modern Stack)

---

## 🏁 Phase 0: Architecture & Environment (地基工程)

**目標：** 搭建專業的前後端分離架構，確保開發環境整潔。

- **Step 0.1: Monorepo Setup (專案初始化)**

   - 建立主資料夾 `haven-v2`。

   - 初始化 Frontend: `npx create-next-app@latest frontend` (Next.js 14, TS, Tailwind)。

   - 初始化 Backend: 建立 `backend` 資料夾，設定 Python 虛擬環境與 FastAPI。

- **Step 0.2: Database Migration (資料庫建置)**

   - 在 Supabase 建立新的 Project。

   - 執行 SQL Script 建立 5 張核心資料表：`users`, `journals`, `analyses`, `cards`, `card_responses` (依照 Doc 2 規格)。

- **Step 0.3: Connection (管線串接)**

   - 設定 Frontend `.env` (Supabase Key, API URL)。

   - 設定 Backend `.env` (OpenAI Key, DB Connection String)。

## 🧠 Phase 1: The Backend Brain (FastAPI 核心)

**目標：** 讓後端邏輯獨立運作，能透過 Swagger UI 測試 API。

- **Step 1.1: Data Models (資料模型)**

   - 使用 `Pydantic` 定義資料驗證格式 (Schema)。

   - 確保 `JournalInput`, `AnalysisOutput`, `CardResponse` 的結構正確。

- **Step 1.2: AI Service (大腦邏輯)**

   - 移植並優化 `[sentiment.py](sentiment.py)` 到 FastAPI。

   - 實作 `POST /api/v1/journal/analyze`：接收文字/語音 -> 回傳 JSON 分析。

   - 實作 `POST /api/v1/cards/generate`：根據情境生成新卡牌。

- **Step 1.3: CRUD Operations (資料讀寫)**

   - 實作卡牌互動 API：

      - `GET /api/v1/cards/draw` (抽卡)

      - `POST /api/v1/cards/respond` (存回答)

## 🎨 Phase 2: The Frontend Experience (Next.js 介面)

**目標：** 打造如原生 App 般滑順的手機網頁 (PWA)。

- **Step 2.1: UI Components (原子元件)**

   - 安裝 `shadcn/ui`。

   - 建置基礎元件：Button, Card, Input, Toast (通知), Progress (進度條)。

- **Step 2.2: The Journal Flow (日記功能)**

   - 製作「語音輸入按鈕」 (整合 Browser Speech API 或 Whisper)。

   - 製作「情緒儀表板」：視覺化顯示 AI 回傳的分析結果。

- **Step 2.3: The Card Engine (卡牌功能)**

   - 製作 **Tinder-style** 的卡牌介面。

   - 實作「翻轉動畫 (Flip Animation)」：點擊查看背面心理學知識。

   - 實作對話框：讓使用者輸入回答並送出。

## 🔐 Phase 3: Integration & Identity (整合與身份)

**目標：** 將前後端接上，並綁定使用者身份。

- **Step 3.1: API Integration (接生)**

   - 前端使用 `fetch` 或 `React Query` 呼叫 FastAPI。

   - 處理 Loading 狀態與錯誤訊息 (Toast)。

- **Step 3.2: Auth & Profile (身份驗證)**

   - 實作 Supabase Auth (Email 登入)。

   - 實作 `Profile Page`：顯示關係存款分數、設定伴侶 ID。

- **Step 3.3: Gamification (遊戲化)**

   - 實作「關係存款」進度條動畫。

   - (Optional) 實作「記憶迴廊」日曆視圖。

## 🚀 Phase 4: Launch (發布)

**目標：** 部署到公開網路，讓 Vicky 在手機上使用。

- **Backend Deploy**: 部署至 **Render** 或 **Railway**。

- **Frontend Deploy**: 部署至 **Vercel**。

- **Domain**: 設定專屬網址 (e.g., `[haven.love](haven.love)`)。

- **Go Live**: 傳送連結，正式上線。