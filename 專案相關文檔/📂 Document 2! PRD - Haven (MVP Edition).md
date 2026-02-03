# 📂 Document 2: PRD - Haven (MVP Edition)

**檔案名稱：** `02_Product_``[Requirements.md](Requirements.md)` 

**最後更新：** 2026-02-03

## 1\. 產品概觀 (Overview)

- **產品代號**：Connection AI

- **英文名稱**：Haven

- **核心價值**：The Relationship Gym (關係健身房)

- **Slogan**：Where Love Grows, Safely.

## 2\. 使用者角色 (User Personas)

- **The Explorer (探索者)**：感情穩定，想透過新鮮話題更了解對方。

- **The Stumbler (受挫者)**：剛吵架或冷戰，不知道如何開口，需要「台階」下。

- **The Maintainer (維護者)**：生活平淡，希望每天有一點小互動來維持熱度。

## 3\. 功能詳解 (Feature Specifications)

### 🧡 Feature A: AI 關係健檢師 (The AI Compass)

**定位**：不只是日記，而是「情緒翻譯機」。AI 必須以 **JSON 格式** 回傳分析結果，以便程式讀取。

- **User Flow**:

   1. **Input**: 使用者輸入日記 (Text) 或語音轉文字。

   2. **Process**: AI 進行 EFT 情緒分析。

   3. **Output**: 顯示 **4 維度分析卡**。

- **4 維度分析內容 (JSON Schema)**:

   1. **你的情緒 (Current Mood)**:

      - `key`: `"mood_label"`

      - `description`: 簡短的情緒標籤。

      - `examples`: \[憤怒, 焦慮, 開心, 幸福, 溫馨, 難過, 傷心, 痛苦, 平靜, 無聊, 生氣, 沮喪, 焦躁, 疲勞, 緊張, 壓力, 失眠, 憂鬱, 恐慌, 悲傷, 孤獨, 寂寞, 無助, 絕望\]

   2. **深層需求 (Underlying Needs)**:

      - `key`: `"emotional_needs"`

      - `description`: 翻譯情緒背後的語言 (e.g., "你不是在生氣，你是渴望被關注")。

      - `examples`: \[陪伴, 關心, 愛, 安全感, 被理解, 被支持, 被肯定, 被尊重, 被看見, 歸屬感, 信任, 空間\]

   3. **給你的行動建議 (Advice for You)**:

      - `key`: `"advice_for_user"`

      - `description`: 給使用者的自我反思與情緒調節建議 (Self-regulation)。

   4. **給伴侶的建議 (Advice for Your Partner)**:

      - `key`: `"action_for_partner"`

      - `description`: **Copy-Paste Ready!** 給伴侶的具體行動建議。

      - `examples`: \[給他/她一個擁抱, 幫他/她按摩, 陪他/她聊天, 泡一杯茶, 傾聽不打斷, 安靜陪伴, 牽手散步\]

   5. **推薦卡牌類型**:

      - `key`: `"card_type_recommendation"`

      - `options`: \['深度交流卡', '破冰修復卡', '色色情趣卡', '日常行動卡'\]

### 🃏 Feature B: 無限卡牌引擎 (The Infinite Deck)

**定位**：基於當下情境生成的客製化訓練。

- **生成邏輯**：`Prompt` = `User Context` + `Analysis Result` (from Feature A) + `Selected Mode`

- **卡牌結構 (Card Structure)**：

   - **Front (正面)**：具體的行動指令或問題 (Challenge/Question)。

   - **Back (背面)**：Why? (心理學小知識，解釋為什麼要做這件事)。

   - **Interaction (互動區)**：使用者填寫回答 (Journaling Input) 或點擊「已完成」 (Check button)。

- **卡牌模式 (Modes)**：

   1. **Deep Talk (深度交流)**：價值觀同步。

   2. **Repair (修復冰山)**：吵架後的破冰與和解。

   3. **Sparks (火花與情趣)**：浪漫與親密挑戰。

   4. **Appreciation (感恩)**：練習看見對方的付出。

### 🌳 Feature C: 關係存款 (Relationship Savings)

**定位**：遊戲化獎勵機制 (Gamification)。

- **機制**：

   - 每完成一張卡牌的互動（填寫回答或點擊完成），「關係存款進度條」增加。

   - 顯示累積的 **"Meaningful Moments" (有意義時刻)** 總數。

## 4\. 技術規格 (Tech Stack)

- **Frontend**: Streamlit (使用 `st.tabs` 分頁設計，`st.sidebar` 顯示歷史紀錄)。

- **Backend Logic**: Python 3.9+。

- **Database**: Supabase (PostgreSQL)

   - Table: `cards` (儲存生成內容)

   - Table: `logs` (儲存日記分析與 JSON 結果)

- **AI Engine**: **OpenAI API (gpt-5-mini)**