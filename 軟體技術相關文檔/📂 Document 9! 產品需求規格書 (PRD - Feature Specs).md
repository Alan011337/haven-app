# 📂 Document 9: 產品需求規格書 (PRD - Feature Specs)

**版本：** 2\.1 (Aligned with Tactics) 

**目標：** 定義 Haven v1.0 正式版的功能細節與驗收標準。 

**原則：** **Connection First (連結優先)** > Features Second (功能次之)。

---

## 1\. 核心互動迴圈 (The Core Loop) - 🟢 P0 (必備)

*這層級的功能決定了 App 的基本價值：輸入 -> 分析 -> 同步。*

### 1\.1 智慧日記與即時同步 (Smart Journal & Sync)

- **User Story**: 「我今天心情不好，寫了幾句抱怨，Vicky 打開 App 就能知道該怎麼安慰我，而不需要看到我傷人的原話。」

- **Spec**:

   - **Input**: 文字輸入框 (Textarea)，支援換行。

   - **Analysis**: 後端呼叫 GPT-5-mini，產出 `mood` (情緒), `needs` (需求), `action_for_partner` (給對方的建議)。

   - **Sync (關鍵)**: 使用 **TanStack Query** 在前端進行背景輪詢 (Polling) 或重整，確保 User B 能在 10 秒內看到 User A 的最新狀態。

- **Acceptance Criteria (驗收標準)**: User A 送出日記後，User B 的手機在不手動重整的情況下，能自動顯示 User A 的狀態卡片。

### 1\.2 關係儀表板 (Relationship Dashboard)

- **User Story**: 「打開 App，我想一眼看到我們現在的關係『天氣』如何。」

- **Spec**:

   - **Header**: 顯示雙方的頭像與連結狀態。

   - **Weather Widget**: 根據最新的 AI 情緒分析，顯示對應的 Emoji (☀️/☁️/🌧️)。

   - **Action Card**: 最顯眼的區塊，顯示 AI 給予的「今日行動建議」(e.g., "給 Alan 一個擁抱").

- **Tech**: 使用 `shadcn/ui` 的 `Card` 與 `Badge` 組件。

### 1\.3 伴侶綁定 (Pairing System)

- **User Story**: 「剛註冊完，我要能立刻連上我的另一半。」

- **Spec**:

   - 簡單的 **Invite Code (6碼)** 機制。

   - 綁定成功後，觸發全螢幕慶祝動畫 (Confetti)。

---

## 2\. 體驗增強功能 (Experience Enhancers) - 🟡 P1 (上線後 48h)

*這些功能讓 App 變得「好用」且「有趣」。*

### 2\.1 語音日記 (Voice Journaling)

- **User Story**: 「開車或走路時，我不想打字，只想用說的。」

- **Spec**:

   - **UI**: 輸入框旁新增「麥克風」按鈕。長按錄音，放開送出。

   - **Tech**: 前端使用 `MediaRecorder API` 錄製 Blob -> 上傳後端 -> OpenAI Whisper API 轉文字 -> 進入原本的分析流程。

   - *注意：這放在 P1 是因為處理音訊格式相容性 (iOS vs Android) 需要一點時間调试。*

### 2\.2 記憶迴廊 (Memory Lane)

- **User Story**: 「我想看看上個月我們吵架那天，到底是為了什麼。」

- **Spec**:

   - **Calendar View**: 使用 `react-day-picker` 顯示日曆。有寫日記的日子下方有小圓點。

   - **List View**: 無限捲動 (Infinite Scroll) 的日記卡片流。

### 2\.3 關係存款視覺化 (Savings Visualizer)

- **User Story**: 「我想看到我們的關係正在累積正向分數。」

- **Spec**:

   - **Progress Bar**: 首頁顯示一條共同累積的進度條。

   - **Animation**: 每次完成互動，分數 `+10` 並有數字跳動動畫。

---

## 3\. 未來擴充願景 (Future Vision) - 🔴 P2 (下一階段)

*這些功能很棒，但不要現在做，會卡死開發進度。*

### 3\.1 虛擬情感教練 (AI Chat Mode)

- **Spec**: 針對 AI 的建議進行追問 (e.g., "為什麼你建議我道歉？明明是他的錯")。

- **Tech**: 需要實作 **WebSocket** 或 **Vercel AI SDK (Streams)**，複雜度較高，先用單向建議即可。

### 3\.2 雙人即時繪圖/遊戲

- **Spec**: 一起畫畫或玩小遊戲。

- **Reason**: 這屬於娛樂範疇，偏離核心價值，優先級最低。