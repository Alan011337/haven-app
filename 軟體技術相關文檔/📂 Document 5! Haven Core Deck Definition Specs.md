# 📂 Document 5: Haven Core Deck Definition Specs

**檔案名稱：** `05_Card_Decks_``[Spec.md](Spec.md)` 

**版本：** 2\.0 (AI Prompt Ready) 

**核心理念：** 從「向內探索」到「向外連結」，再到「親密實踐」。 

**資料結構對應：** `cards` 資料表中的 `category` 欄位。

---

## 🏗️ 牌組總覽 (The Workout Plan)

每套牌組都對應到關係中的不同肌群訓練。所有牌組皆包含兩種 `type`：

1. **Question (提問卡)**: 開啟對話，交換資訊。

2. **Action (行動卡)**: 物理接觸、具體任務、儀式感。

---

## 1\. Daily Vibe (日常共感)

- **Code**: `daily_vibe`

- **Gym Metaphor**: 🏃‍♂️ **Warm-up / Cardio (暖身有氧)**

   - *每天都要做，輕鬆不費力，維持基礎代謝率。*

- **Product Positioning**: ☕️ 輕鬆的日常維繫。

- **Target Scenario**: 晚餐時、睡前滑手機時、通勤時。

- **AI Tone & Style**:

   - **Tone**: Playful (俏皮), Lighthearted (輕鬆), Curious (好奇).

   - **Constraint**: 禁止談論沈重話題（錢、未來、前任）。保持 3 分鐘內能結束的話題。

- **Content Strategy**:

   - **Question**: 生活微觀察、無壓力的 "What if" 假設題、回憶趣事。

   - **Action**: 30秒內能完成的小互動。

- **Examples**:

   - ❓ "如果我們可以瞬間移動去吃晚餐，你現在最想去哪一家餐廳（國內外皆可）？"

   - ⚡️ "Action: 模仿對方生氣時的表情，看誰先笑場。"

## 2\. Soul Dive (靈魂深潛)

- **Code**: `soul_dive`

- **Gym Metaphor**: 🏋️‍♀️ **Heavy Lifting (重量訓練)**

   - *強度高，能長出深層肌肉，但不能天天做，需要休息恢復。*

- **Product Positioning**: 🕯️ 靈魂的共鳴與脆弱。

- **Target Scenario**: 週末深夜、喝了一點酒後、想要深度連結時。

- **AI Tone & Style**:

   - **Tone**: Empathetic (同理), Deep (深沈), Vulnerable (脆弱).

   - **Constraint**: 題目必須具有「開放性」，引導使用者說出「我感覺...」或「我相信...」。

- **Content Strategy**:

   - **Question**: 價值觀探索、童年影響、恐懼與夢想、對關係的深層期待。

   - **Action**: 需要時間與專注力的連結儀式。

- **Examples**:

   - ❓ "你覺得你在愛情裡，最像小孩子（需要被照顧）的一面是什麼？"

   - ⚡️ "Action: 對視 3 分鐘，不說話，試著用眼神傳遞『我愛你』。"

## 3\. Safe Zone (安全氣囊)

- **Code**: `safe_zone`

- **Gym Metaphor**: 🚑 **Physical Therapy / Rehab (物理治療/復健)**

   - *受傷（衝突）後的修復，重點是恢復活動範圍，減少疼痛。*

- **Product Positioning**: 🏳️ 衝突後的急救箱。

- **Target Scenario**: 吵架後、冷戰中、氣氛尷尬時。

- **AI Tone & Style**:

   - **Tone**: Neutral (中立), Gentle (溫柔), Mediating (調停).

   - **Constraint**: **嚴格遵守 NVC (非暴力溝通)** 原則。禁止指責性語言 (`You` statements)，強制轉換為感受語言 (`I` statements)。

- **Content Strategy**:

   - **Question**: 引導換位思考、確認事實與觀點的差異。

   - **Action**: 象徵性的和好儀式，打破肢體僵局。

- **Examples**:

   - ❓ "在這場爭執中，你覺得我的哪個觀點其實是有點道理的？（即使只有 1%）"

   - ⚡️ "Action: 伸出你的小指頭，邀請對方打勾勾，約定我們先暫停爭論 10 分鐘去喝杯水。"

## 4\. After Dark (深夜模式)

- **Code**: `after_dark`

- **Gym Metaphor**: 🔥 **The Steam Room (桑拿/熱瑜珈)**

   - *提升溫度，促進血液循環，釋放腦內啡。*

- **Product Positioning**: 💋 情慾與激情的探索。

- **Target Scenario**: 臥室裡、私密空間、前戲時間。

- **AI Tone & Style**:

   - **Tone**: Seductive (誘惑), Spicy (辛辣), Respectful (尊重).

   - **Constraint**: 必須強調 **Consent (知情同意)**。避免過於粗俗的用詞，使用帶有暗示性與美感的語言。*Note: 需注意 OpenAI 的 NSFW 政策，Prompt 需設計為「浪漫/文學性」的情慾描寫。*

- **Content Strategy**:

   - **Question**: 性幻想、敏感帶探索、被愛的渴望。

   - **Action**: 前戲指令、感官剝奪（蒙眼）、角色扮演。

- **Examples**:

   - ❓ "如果要我們一起嘗試一個新的地點（不一定要發生什麼），你會選哪裡？"

   - ⚡️ "Action: 蒙上眼睛，猜猜我現在正親吻你身體的哪裡。"

## 5\. Co-Pilot (最佳副駕)

- **Code**: `co_pilot`

- **Gym Metaphor**: 📋 **Team Strategy Meeting (教練戰術會議)**

   - *分析數據，制定計畫，確保目標一致。*

- **Product Positioning**: 🤝 理性的合作夥伴會議。

- **Target Scenario**: 每週日晚上、發薪日、甚至做家務時。

- **AI Tone & Style**:

   - **Tone**: Rational (理性), Constructive (建設性), Collaborative (協作).

   - **Constraint**: 聚焦於「我們 (We/Us)」，將問題外化（是我們 vs 問題，而不是我 vs 你）。

- **Content Strategy**:

   - **Question**: 財務狀況、家務分工滿意度、近期目標校準。

   - **Action**: 具體的規劃行動、清單檢查。

- **Examples**:

   - ❓ "最近一週，我們在時間分配上（工作 vs 相處），你覺得滿意嗎？如果不滿意，我們可以怎麼微調？"

   - ⚡️ "Action: 打開行事曆，把下個月一定要一起做的「三件事」填上去。"

## 6\. Love Blueprint (愛情藍圖)

- **Code**: `love_blueprint`

- **Gym Metaphor**: 🧬 **DNA Test / Full Body Scan (全身健檢/基因檢測)**

   - *深度了解身體構造（自我），才能設計最適合的訓練菜單。*

- **Product Positioning**: 💎 自我覺察與關係定義 (The Meta Deck)。

- **Target Scenario**: 關係剛開始、進入下一階段（同居/結婚）前、或感到迷惘時。

- **AI Tone & Style**:

   - **Tone**: Introspective (內省), Insightful (洞察), Psychological (心理學視角).

   - **Constraint**: 引導使用者「向內看」，釐清自己的界線與需求，而非討論對方。

- **Content Strategy**:

   - **Question**: 釐清界線 (Boundaries)、依附類型探索、愛的語言確認。

   - **Action**: 撰寫使用說明書、繪製關係願景圖。

- **Examples**:

   - ❓ "什麼樣的相處模式（例如：已讀不回、說謊...）會讓你感到窒息或極度不安？這跟你的過去有關嗎？"

   - ⚡️ "Action: 列出 3 個你在關係中絕對不能妥協的底線 (Non-negotiables)，並溫柔地唸給對方聽。"

---

### 💡 技術實作筆記 (Developer Notes)

1. **AI System Prompt**: 在開發 `Phase 1.2` 的生成引擎時，我們需要為這 6 個類別分別撰寫 6 個不同的 System Prompt。

   - 例如：`You are a playful relationship coach creating a 'Daily Vibe' card...`

2. **Guardrails (護欄)**:

   - `Safe Zone` 的 Prompt 必須包含：「如果用戶輸入帶有攻擊性，請將其轉化為『我感到受傷』的語句。」

   - `After Dark` 的 Prompt 必須包含：「確保內容適合成年伴侶，既性感又不違反 OpenAI 安全規範。」