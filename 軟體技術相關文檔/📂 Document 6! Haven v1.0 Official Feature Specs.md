# 📂 Document 6: Haven v1.0 Official Feature Specs

**文件目標：** 定義 Haven v1.0 正式發布版的核心功能規格。 

**狀態：** 🚀 Production Ready (正式產品規格) 

**最後更新：** 2026-02-04

---

## 1\. ❤️ 愛之語 AI 翻譯機 (Love Translator)

**核心價值：** 不只是聽你說話，還要幫你「翻譯」給對方聽。

- **Input (輸入流)**：

   - **Multi-modal**: 支援 **文字** 與 **語音 (Whisper AI)**。使用者可以在通勤或開車時，用語音宣洩情緒，AI 精準轉錄並分析。

- **Process (核心處理)**：

   - **EFT Engine**: 採用情緒取向治療邏輯，提取 `Mood` (情緒標籤) 與 `Needs` (深層需求)。

- **Output (輸出流)**：

   - **Self-Insight (給自己)**: 情緒儀表板，看見自己的情緒起伏。

   - **Partner Sync (給伴侶 - 正式版功能)**:

      - **不再需要複製貼上！**

      - 當 User A 完成日記分析後，系統會自動將 **「經 AI 潤飾過的伴侶使用說明書」** (注意：不是原始抱怨日記，是翻譯過的建議) **同步** 到 User B 的「伴侶動態 (Partner Insights)」頁面。

      - User B 打開 App，會看到：「Vicky 今天有點焦慮，建議給她一個擁抱。」

## 2\. 🃏 無限牌組引擎 (The Infinite Deck)

**核心價值：** 針對不同情境的「關係健身器材」。

- **Deck Categories (完整六大肌群)**：

   - 🔮 **Daily Vibe**: 日常共感

   - 🌊 **Soul Dive**: 靈魂深潛

   - 🛡️ **Safe Zone**: 安全氣囊 (NVC 引導)

   - 🕯️ **After Dark**: 深夜模式

   - ✈️ **Co-Pilot**: 最佳副駕

   - 🧩 **Love Blueprint**: 愛情藍圖

- **Production Experience (正式版體驗)**：

   - **Native Feel**: 左右滑動切換卡牌 (Tinder-like UI)。

   - **Animation**: 精緻的 3D 翻轉動畫查看心理學原理。

   - **Context Awareness**: AI 生成題目時，會參考你們過去的日記與回答（例如：不會在你們剛吵架時推薦 After Dark）。

## 3\. 📝 雙人互動記憶庫 (Shared Journaling)

**核心價值：** 凡走過必留下痕跡，打造屬於你們的關係資料庫。

- **Real-time Interaction (即時互動)**：

   - 當 User A 回答了一張卡牌，User B 的 App 會收到通知（或紅點提示）。

   - **Blind Reveal 機制**: 針對某些深度問題，必須 **「雙方都回答後」**，才能看到對方的答案。這能確保回答的真實性，並增加期待感 (類似 Paired App 機制)。

- **History Timeline (回憶錄)**：

   - 以時間軸呈現過去的對話。點擊某一天，可以看到當天抽的卡、雙方的回答、以及當時的 AI 分析。

## 4\. 🔗 伴侶綁定與帳戶系統 (Account & Pairing)

**核心價值：** 這是「平台」與「單機軟體」的分水嶺。

- **Authentication (身份驗證)**：

   - 完整支援 **Email/Password** 與 **Social Login (Google)**。

- **Pairing Protocol (綁定協議)**：

   - **Invite Code**: 生成專屬邀請碼。

   - **Data Bonding**: 綁定後，資料庫層級建立關聯。你的 `partner_id` 寫入對方 UUID。

   - **Permission**: 嚴格定義隱私權限。日記原文預設 **私密**，只有「翻譯後的建議」與「卡牌回答」會共享。

## 5\. 🏆 關係存款 (Gamification)

**核心價值：** 建立「正向回饋迴圈」，讓經營關係上癮。

- **Relationship Level (關係等級)**：

   - 透過累積 "Meaningful Moments" 升級。

- **Streaks (連續紀錄)**：

   - 顯示「連續互動天數」，激勵使用者每天打開 App (Retention Hook)。

- **Badges (成就徽章)**：

   - 例如：「深度溝通者 (Soul Diver)」、「破冰大師 (Ice Breaker)」。

## 6\. 🔐 技術基礎建設 (Tech Infrastructure)

**核心價值：** 穩固、擴充性強、數據安全。

- **Backend**: Python FastAPI (Async/Await 高併發處理)。

- **Frontend**: Next.js 14 (React Server Components, SEO Friendly)。

- **Database**: Supabase (PostgreSQL) + RLS (Row Level Security - 確保只有你和伴侶能讀取你們的資料)。

- **Deployment**: Vercel (Frontend) + Render (Backend)。