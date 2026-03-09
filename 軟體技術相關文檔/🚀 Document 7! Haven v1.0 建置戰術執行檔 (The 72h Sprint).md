# 🚀 Document 7: Haven v1.0 建置戰術執行檔 (The 72h Sprint)

**目標：** 在 72 小時內，完成前後端架構，並實現 **「雙人自動同步」** 的核心體驗。 

**原則：** Backend Logic First (邏輯優先) -> Data Flow (資料流暢通) -> UI Polish (最後再修介面)。 

**狀態：** 🔒 Locked (規格凍結，立即執行)

---

## 🟢 優先級 P0: 核心基礎與雙人連線 (The Foundation)

*這些功能沒做完，v1.0 的承諾就無法兌現。*

### 1\. 基礎設施與身份 (Infrastructure & Auth)

- **Monorepo**: 建立 `haven-v2` 專案，內含 `frontend` (Next.js 14) + `backend` (FastAPI)。

- **Database**: 在 Supabase 建立 5 張核心資料表，重點檢查 `users` 表是否包含 `partner_id` 與 `invite_code` 欄位。

- **Auth**: 實作最基礎的 Email/Password 註冊與登入 (Supabase Auth)。

### 2\. 伴侶綁定機制 (The Pairing System) \[⬆️ 關鍵 P0\]

- **前端**：在登入後的首頁或設定頁：

   - **顯示**：「我的邀請碼 (My Invite Code)」(由 Backend 生成)。

   - **輸入**：「輸入伴侶邀請碼 (Enter Partner Code)」。

- **後端**：

   - 實作 `POST /api/v1/users/pair`。

   - 邏輯：驗證碼正確 -> 找到 User B -> 將 User A 的 `partner_id` 設為 B，將 B 的 `partner_id` 設為 A (雙向綁定)。

### 3\. 核心功能 A：日記與自動同步 (Journal & Auto-Sync)

- **User A (輸入)**：寫日記 (Text) -> 送出。

- **Backend (處理)**：AI 分析情緒與需求 -> 存入 `analyses` -> 檢查 `partner_id`。

- **User B (同步)**：

   - 打開 App，首頁的 **「伴侶動態 (Partner Insights)」** 區塊自動 query 資料庫。

   - **顯示**：看到 AI 轉譯後的建議 (e.g., "Alan 今天工作壓力有點大，需要你的肯定")。*注意：P0 階段先不顯示原始日記，保護隱私並降低複雜度。*

- **Backup**: 保留「複製文字」按鈕，以防萬一。

### 4\. 核心功能 B：卡牌互動 (Card Interaction)

- **User A (發起)**：抽卡 -> 填寫回答 -> 送出。

- **User B (接收)**：

   - 首頁出現 **「換你了 (Your Turn)」** 提示卡。

   - 顯示內容：「Alan 回答了一張關於 *Soul Dive* 的卡牌，他也想聽聽你的想法。」

   - **行動**：點擊 -> 進入回答頁面 -> 填寫後才顯示 User A 的答案 (簡易版 Blind Reveal)。

---

## 🟡 優先級 P1: 體驗優化 (上線後 48 小時內)

- **UI Polish**: 引入 `shadcn/ui` (Card, Button, Toast)，告別原生 HTML 的陽春感。

- **Flip Animation**: 實作 CSS 3D 翻轉效果，讓查看「心理學原理」有儀式感。

- **PWA Setup**: 設定 `manifest.json` 與 Icons，讓 Vicky 能將網頁「加入主畫面」，隱藏瀏覽器網址列，體驗如原生 App。

---

## 🔴 優先級 P2: 未來擴充 (Next Sprint)

*這些是錦上添花，等核心迴圈跑順了再說。*

1. **語音輸入 (Voice Input)**：暫時移除，避免處理 Audio Blob 上傳的技術坑，先專注於文字流暢度。

2. **關係存款 (Gamification)**：視覺化的進度條與動畫，暫時先在後端記分就好，前端不顯示也沒關係。

3. **歷史回顧 (History View)**：製作精美的時間軸頁面。

4. **Google Login**：MVP 用 Email 驗證碼或密碼即可。

---

### ✅ Definition of Done (完工標準)

1. Alan 和 Vicky 的手機都能登入 App。

2. Alan 輸入邀請碼，兩人帳號成功綁定。

3. Alan 在手機寫日記，Vicky 的手機能看到 AI 建議。

4. Alan 回答卡牌，Vicky 也能回答同一張卡牌，並看到彼此的答案。