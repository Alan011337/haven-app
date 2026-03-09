# 📂 Document 10: 工程規範 (Engineering Standards)

**版本：** 2\.0 (Pro Standard) 

**目標：** 建立嚴格的 Code Quality 管控，確保前後端協作順暢，減少低級錯誤。

## 1\. 專案結構 (Monorepo Structure)

我們將採用清晰的模組化結構，並明確區分 **ORM 模型 (存資料)** 與 **Pydantic Schema (傳資料)**。

Plaintext

```
haven-v2/
├── frontend/                 # Next.js 14 (App Router)
│   ├── src/
│   │   ├── app/              # 頁面路由 (Pages & Layouts)
│   │   ├── components/       # UI 元件
│   │   │   ├── ui/           # shadcn 通用元件 (Button, Card...)
│   │   │   └── features/     # 專案特定元件 (JournalCard, MoodChart...)
│   │   ├── hooks/            # 自定義 React Hooks (useJournal, useAuth)
│   │   ├── lib/              # 工具函式 (api-client, utils)
│   │   └── types/            # TypeScript 型別定義 (對應後端 Schema)
│   └── ...
│
├── backend/                  # FastAPI 專案
│   ├── app/
│   │   ├── api/              # API Routes (Endpoints)
│   │   │   ├── v1/           # 版本控制
│   │   │   │   ├── users.py
│   │   │   │   └── journals.py
│   │   ├── core/             # 核心設定 (Config, Security, DB Session)
│   │   ├── models/           # SQLModel (資料庫 Table 定義) -> 對應 DB
│   │   ├── schemas/          # Pydantic (API Request/Response 定義) -> 對應 Frontend
│   │   └── services/         # 商業邏輯 (AI Service, Sentiment Logic)
│   ├── alembic/              # 資料庫遷移腳本 (Migration Scripts)
│   └── main.py               # 程式進入點
│
├── .env                      # 環境變數 (絕對不能進 Git!)
└── README.md

```

## 2\. 開發流程規範 (Workflow & Git)

### 2\.1 Branching Strategy (分支策略)

- **`main`**: 生產環境 (Production)。隨時可部署的穩定版本。

- **`dev`**: 開發主線 (Development)。所有的 Feature 做完後合併至此。

- **`feat/xxx`**: 功能分支 (e.g., `feat/voice-input`, `feat/auth-login`)。

   - *規則：* 一個分支只做一件事。做完 -> Push -> Pull Request (PR) -> Merge to `dev`。

### 2\.2 Commit Message 規範 (Conventional Commits)

讓 Commit 紀錄像說故事一樣清晰：

- `feat: ...` : 新增功能 (e.g., `feat: implement daily vibe card logic`)

- `fix: ...` : 修復 Bug (e.g., `fix: resolve jwt token expiration issue`)

- `ui: ...` : 樣式/介面調整 (e.g., `ui: update dashboard color scheme`)

- `chore: ...` : 雜事/依賴更新 (e.g., `chore: install tanstack-query`)

- `refactor: ...` : 重構程式碼 (不影響功能)

## 3\. 程式碼品質管控 (Quality Control)

### 3\.1 Linter & Formatter (自動整容)

- **Frontend**:

   - **ESLint**: 抓邏輯錯誤 (e.g., 用了未定義的變數)。

   - **Prettier**: 統一排版 (自動加分號、縮排)。

   - *設定：* VS Code 設定 "Format On Save"，存檔即排版。

- **Backend**:

   - **Ruff**: Python 界的新神話，速度極快的 Linter + Formatter (取代 Flake8/Black)。

### 3\.2 Pre-commit Hooks (守門員) **\[新增\]**

- 安裝 `husky` (前端) 或 `pre-commit` (後端)。

- **作用**：在你執行 `git commit` 時自動跑檢查。如果程式碼格式很爛或有語法錯誤，**禁止提交**。這能防止髒 Code 污染 `main` 分支。

## 4\. API 契約與型別安全 (The Contract) **\[關鍵\]**

這是前後端分離最容易出錯的地方。我們制定以下規則：

1. **Swagger Source of Truth**: 後端 FastAPI 會自動生成 `/docs` (OpenAPI JSON)。

2. **Naming Convention**:

   - URL 路徑用 **kebab-case** (e.g., `/api/v1/daily-journal`)。

   - JSON 欄位用 **camelCase** (前端習慣) 或 **snake_case** (Python 習慣)。*為了開發順暢，我們統一：後端輸出 JSON 時自動轉為 **camelCase** 給前端。*

3. **Type Sync**:

   - 後端的 `schemas/``[journal.py](journal.py)` 修改後，前端的 `types/journal.ts` 必須手動（或使用工具）同步更新，確保欄位名稱一致。