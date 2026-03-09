# 📂 Document 8: 技術架構與堆疊 (Architecture & Tech Stack)

**版本：** 2\.1 (Production Grade) 

**目標：** 打造高擴展性、全端型別安全 (Type-Safe)、使用者體驗極佳的現代化 Web App (PWA)。

## 1\. 核心技術堆疊 (The "Modern Stack")

這是目前業界公認最頂尖、開發生產力最高的組合：

| 層級 | 技術選型 | 為什麼選它？ (CTO 的決策理由) | 
|---|---|---|
| **Frontend** | **Next.js 14** (App Router) | React 的最強框架。支援 Server Components，載入速度極快，SEO 完美。 | 
| **Language** | **TypeScript** | **絕對關鍵！** 任何嚴肅專案不寫純 JS。強型別能減少 80% 的低級錯誤，前後端介面更清晰。 | 
| **UI Library** | **Tailwind CSS** + **shadcn/ui** | 現代新創標配。複製貼上即可用的精美組件，開發速度是傳統 CSS 的 10 倍。 | 
| **State Mgt** | **Zustand** (Client) + **TanStack Query** (Server) | **重要區分：** `Zustand` 管 UI 狀態 (開關/深色模式)；`TanStack Query` 管 API 資料 (快取/自動同步)。 | 
| **Backend** | **FastAPI** (Python) | 取代 Flask。效能最高、原生支援異步 (Async)、自動生成 Swagger 文件。 | 
| **ORM** | **SQLModel** | **\[新增\]** FastAPI 作者親自開發。完美結合 SQLAlchemy 與 Pydantic，讓資料庫操作就像寫 Python 物件一樣直覺。 | 
| **Database** | **Supabase** (PostgreSQL) | 關聯式資料庫的王者。我們只用它的 DB 和 Auth 功能，不依賴它的邊緣函數，保持架構單純。 | 
| **AI Engine** | **OpenAI SDK** + **Pydantic** | **\[修正\]** 放棄 LangChain (過度封裝)。直接使用 OpenAI 的 `Structured Outputs` 搭配 `Pydantic` 定義格式，JSON 解析更精準穩定。 | 

匯出到試算表

---

## 2\. 系統架構圖 (System Architecture)

我們採用 **前後端分離 (Client-Server Architecture)** 架構。

程式碼片段

```
graph TD
    User((User Devices)) -->|HTTPS| Frontend[Next.js Client (PWA)]
    
    subgraph "Frontend Layer (Vercel)"
        Frontend -->|Zustand| ClientState[UI State Store]
        Frontend -->|TanStack Query| ServerState[Data Cache & Auto-Sync]
    end
    
    Frontend -->|REST API (JSON)| Backend[FastAPI Server]
    
    subgraph "Backend Layer (Render/Railway)"
        Backend -->|Pydantic| Schema[Data Validation]
        Backend -->|SQLModel| ORM[Database ORM]
        Backend -->|Auth Middleware| Auth[Supabase Auth]
        
        ORM <-->|SQL| DB[(Supabase PostgreSQL)]
        
        Backend -->|API Call| OpenAI[OpenAI GPT-5-mini]
        
        note[External Services]
        OpenAI -.->|JSON Analysis| Backend
    end

```

---

## 3\. 專案目錄結構 (Monorepo Structure)

這將是你下達 `mkdir` 指令後的第一個結構，保持整潔至關重要。

Plaintext

```
haven-v2/
├── frontend/                # Next.js 專案
│   ├── src/
│   │   ├── app/             # 頁面路由 (Pages)
│   │   ├── components/      # UI 元件 (shadcn)
│   │   ├── lib/             # 工具函式 (api client, utils)
│   │   └── hooks/           # Custom Hooks (useJournal, useCards)
│   ├── public/              # 靜態檔案 (manifest.json, icons)
│   └── ...
│
├── backend/                 # FastAPI 專案
│   ├── app/
│   │   ├── api/             # API Endpoints (routers)
│   │   ├── core/            # 設定檔 (config, security)
│   │   ├── db/              # 資料庫連線 (session)
│   │   ├── models/          # SQLModel 資料模型 (Table Schema)
│   │   ├── schemas/         # Pydantic 驗證模型 (Req/Res Body)
│   │   └── services/        # 商業邏輯 (AI, Sentiment)
│   ├── main.py              # 程式進入點
│   └── requirements.txt
│
└── README.md
```