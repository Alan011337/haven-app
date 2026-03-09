# 📂 Document 2: PRD - Haven (v2.0 Official Specs)

**檔案名稱：** `02_Product_``[Requirements.md](Requirements.md)` 

**版本：** 2\.0 (Production Grade) 

**狀態：** Ready for Development

---

## 1\. 產品概觀 (Overview)

- **Product Name**: Haven (棲)

- **Codename**: Connection AI

- **Slogan**: *Where Love Grows, Safely.*

- **Core Value**: The Relationship Gym (關係健身房)

- **Platform Strategy**: Mobile-First Web App (PWA) —— 雖然是網頁，但操作手感要像原生 App。

---

## 2\. 使用者角色 (User Personas)

我們針對三種核心情境設計功能：

1. **The Explorer (探索者)**

   - *Pain Point:* 關係穩定但趨於平淡，覺得「該聊的都聊過了」。

   - *Goal:* 透過新鮮話題 (Daily Vibe/Soul Dive) 重新發現對方的另一面。

2. **The Stumbler (受挫者)**

   - *Pain Point:* 剛吵架、冷戰，或感到被誤解。不知道如何開口才不會再次受傷。

   - *Goal:* 需要「情緒翻譯機」幫忙釐清思緒，並找到下台階 (Safe Zone)。

3. **The Maintainer (維護者)**

   - *Pain Point:* 生活忙碌，沒有時間進行長篇大論的溝通。

   - *Goal:* 透過每日 3 分鐘的微互動 (Daily Action) 維持感情熱度。

---

## 3\. 功能詳解 (Feature Specifications)

### 🧡 Feature A: AI 關係健檢師 (The AI Compass)

**Priority: P0 (Core)** **定位：** 結合語音與文字的智慧情緒日記。

- **User Flow**:

   1. **Input**: 支援 **語音輸入 (Voice)** 或文字輸入。

      - *Tech*: 使用 OpenAI Whisper API 進行語音轉文字 (STT)。

   2. **Process**: 後端接收文字 -> 呼叫 GPT-5-mini -> 進行 EFT (情緒取向治療) 分析。

   3. **Output**: 前端接收 JSON -> 渲染成精美的「情緒儀表板」。

- **JSON Schema (AI 回傳格式)**: AI 必須嚴格遵守此結構，以便前端渲染：

   JSON

   ```
   {
     "mood_label": "焦慮與期待交織",
     "mood_score": 65,  // 1-100, 用於追蹤長期趨勢
     "emotional_needs": "你渴望被對方肯定，而不只是解決問題。",
     "advice_for_user": "試著先深呼吸，區分哪些是事實，哪些是你的想像。",
     "action_for_partner": "親愛的，她現在需要的不是建議，是一個擁抱並告訴她『我在這裡』。",
     "card_recommendation": "Safe Zone"
   }
   
   ```

### 🃏 Feature B: 無限卡牌引擎 (The Infinite Deck)

**Priority: P0 (Core)** **定位：** 基於情境生成的客製化行動指引。

- **UX Design**:

   - **Tinder-like Card**: 手機上可左右滑動（雖然目前是單張，但預留手勢介面）。

   - **Flip Effect**: 點擊卡牌會翻轉，正面是任務，背面是心理學原理 (The Why)。

- **Card Structure**:

   - **Front**: 具體指令 (e.g., "問他：如果你明天就會失去記憶，你最想記住我們的哪一刻？")

   - **Back**: 心理學小知識 (e.g., "懷舊共鳴能有效釋放催產素，增加親密感。")

   - **Type**: `Question` (對話) 或 `Action` (行動)。

- **Categories (完整對齊 Doc 01)**:

   1. 🔮 **Daily Vibe**: 輕鬆日常 / 破冰。

   2. 🌊 **Soul Dive**: 深度價值觀 / 靈魂拷問。

   3. 🛡️ **Safe Zone**: 衝突修復 / 安全氣囊。

   4. 🕯️ **After Dark**: 情趣探索 / 深夜模式。

   5. ✈️ **Co-Pilot**: 關係覆盤 / 未來規劃。

   6. 🧩 **Love Blueprint**: 自我探索 / 愛情藍圖。

### 📊 Feature C: 關係儀表板 (The Relationship Dashboard)

**Priority: P1 (Enhancement)** **定位：** 視覺化的關係健康度追蹤。

- **Relationship Savings (關係存款)**:

   - 每完成一次日記或卡牌，進度條 (ProgressBar) 增加。

   - 顯示累積的 **"Meaningful Moments"** 總數。

- **Calendar View (記憶迴廊)**:

   - 在日曆上顯示過去哪幾天有互動，點擊可回顧當時的 AI 分析。

---

## 4\. 技術規格 (Tech Stack) - *Major Upgrade*

我們將採用 **Modern Web Stack** (現代化網頁架構)：

### 📱 Frontend (Client Side)

- **Framework**: **Next.js 14+** (App Router)

   - *Why*: 支援 SSR (伺服器渲染) 與 RSC (React Server Components)，效能極佳，對 SEO 友善。

- **Language**: **TypeScript** (Strict Mode)

- **Styling**: **Tailwind CSS** + **shadcn/ui** (極美、極快、現代化的 UI 組件庫)。

- **State Management**: **Zustand** (輕量級全域狀態管理)。

- **Animations**: **Framer Motion** (用於翻卡、進場動畫)。

### ⚙️ Backend (Server Side)

- **Framework**: **FastAPI** (Python)

   - *Why*: Python 是 AI 的原生語言，FastAPI 效能高且支援非同步 (Async)。

- **API Doc**: 自動生成 **Swagger UI** (方便前後端對接)。

- **Data Validation**: **Pydantic** (確保資料格式永遠正確)。

### 🗄️ Database & Infra

- **Database**: **Supabase** (PostgreSQL)

- **Auth**: Supabase Auth (支援 Email, Google Login)。

- **AI Model**: **OpenAI GPT-5-mini** (主腦) + **Whisper-1** (語音)。

---

## 5\. 資料庫設計概要 (Database Schema Draft)

為了完整記錄「AI 提問 -> 用戶回答」的互動閉環，我們需要採用 **關聯式設計**：

1. **`users` (使用者表)**

   - `id` (UUID): 使用者唯一碼

   - `email`: 登入帳號

   - `partner_id`: 連結另一半的 ID (預留)

   - `savings_score`: 關係存款分數

2. **`journals` (日記表)**

   - `id` (UUID)

   - `user_id`: 誰寫的

   - `content`: 日記原文 (Text)

   - `audio_url`: 語音檔連結 (Optional)

   - `created_at`: 撰寫時間

3. **`analyses` (AI 分析表)**

   - `id` (UUID)

   - `journal_id`: 對應哪一篇日記

   - `mood_label`: 情緒標籤 (e.g., "焦慮")

   - `emotional_needs`: 深層需求分析

   - `advice_for_user`: 給 User 的建議 (Text/JSON)

   - `action_for_partner`: 給 User’s Partner 的建議 (Text/JSON)

4. **`cards` (卡牌內容表 - The Questions)** *此表儲存「系統預設題目」與「AI 生成題目」*

   - `id` (UUID)

   - `user_id`: (Nullable) 若為空則為系統公用卡，若有值則為該用戶專屬卡。

   - `category`: 類別 (e.g., Soul Dive)

   - `type`: Question / Action

   - `front_content`: 卡牌正面 (題目/指令)

   - `back_content`: 卡牌背面 (心理學原理)

   - `created_at`: 生成時間

5. **`card_responses` (卡牌回應表 - The Answers)** *此表記錄一次完整的「互動事件」，包含雙方的回答*

   - `id` (UUID)

   - `card_id`: 對應哪張卡牌 (FK)

   - `user_id`: **發起者** ID (誰抽這張卡的)

   - `partner_id`: **回應者** ID (對方的 ID)

   - `user_response`: 發起者的回答內容 (Text)

   - `partner_response`: 對方的回答內容 (Text) —— *預設為 NULL，直到對方回答*

   - `mood_after`: 回答完的心情 (Optional)

   - `created_at`: 建立時間 (發起時間)

   - `updated_at`: 更新時間 (對方回答的時間)