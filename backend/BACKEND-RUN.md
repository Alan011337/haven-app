# 後端啟動說明 (Backend Run Guide)

## Localhost 單一正確啟動方式（Source of Truth）

一般本機開發現在不要再直接把 `backend/.env` 的遠端 `DATABASE_URL` 當作
localhost DB 來源。

Canonical localhost runtime：

```bash
# 專案根目錄
bash scripts/local-runtime-stop.sh
bash scripts/local-dev-db.sh start
bash scripts/local-dev-db.sh migrate
bash scripts/local-runtime-backend.sh
```

搭配前端：

```bash
# 專案根目錄，另一個 terminal
bash scripts/local-runtime-frontend.sh
```

驗證：

```bash
bash scripts/local-runtime-verify.sh
```

說明：

- `backend/.env` 仍保留 production / staging 相容的 secrets 與遠端設定
- localhost runtime 會由 `/Users/alanzeng/projects/Haven-local/config/local-dev-runtime.env`
  明確覆寫 `DATABASE_URL` 成本機 Postgres `127.0.0.1:55432`
- `frontend/.env.local` 仍提供 Supabase storage 所需 keys，但 API / WS URL 也會被
  localhost runtime script 覆寫為 `127.0.0.1`
- brand-new 空白 local Postgres 會先 bootstrap current schema 並 stamp Alembic head，之後仍走正常 upgrade path
- 詳細 runbook 見：
  `/Users/alanzeng/projects/Haven-local/docs/local-dev-runtime.md`
- canonical localhost DB 現在只接受 local Postgres；sqlite 不再是正式 localhost runtime
- canonical localhost DB 需要 Docker Compose（見 `config/local-dev-postgres.compose.yml`）

## 若 uvicorn 完全沒輸出、卡在 import FastAPI

診斷若卡在「2. importing fastapi...」：是 FastAPI 依賴的 `annotated_doc` 在你環境會卡住。專案在 `backend/annotated_doc.py` 有本機替代，需讓 Python **先**載到它：

```bash
cd backend
export ABUSE_GUARD_STORE_BACKEND=memory
export PYTHONPATH=.
export PYTHONUTF8=1
.venv-gate/bin/python -m uvicorn app.main:app --reload
```

或直接用 `./scripts/run-dev.sh`（腳本已自動設定 `PYTHONPATH`）。

若仍卡在「pre-importing fastapi」或「loading app」：  
`run-dev.sh` 已設定 `PYTHONUTF8=1`（UTF-8 模式），可減少載入 site-packages 時因編碼卡住。若依舊卡住，請將**整個專案**搬到純英文路徑（無中文、括號、空格），再執行 `RELOAD=0 ./scripts/run-dev.sh`。

---

## 為什麼後端跑不動？(Why won't the backend start?)

常見原因：

1. **`uvicorn: command not found`**  
   啟動腳本需要 `uvicorn`，但系統 PATH 裡沒有（通常因為沒啟用虛擬環境）。  
   現在 `run-dev.sh` / `run-prod.sh` 會自動使用專案內的虛擬環境（`.venv-gate` 或 `venv`），並用 `python -m uvicorn` 啟動，**只要先建立虛擬環境並安裝依賴即可**。

2. **`ModuleNotFoundError: No module named 'uvicorn'` 或 `No module named 'app'`**  
   代表目前用的 Python 環境沒有安裝依賴，或執行時不在 `backend/` 目錄。請依下方「正確啟動方式」操作。

2b. **`pip install -r requirements.txt` 或 `python -m pip --version` 完全沒輸出、卡住**  
   代表此 venv 裡 **載入 pip 模組時就阻塞**（與 FastAPI import 卡住同類）。**不要用此 venv 的 pip**，改用 **uv** 安裝依賴：  
   ```bash
   # 安裝 uv（若尚未安裝）
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # 或: brew install uv
   cd backend
   ./scripts/install-deps-uv.sh
   ```  
   或刪除 venv 後用 **get-pip.py** 重新取得 pip：  
   ```bash
   cd backend
   rm -rf venv
   python3 -m venv venv
   curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
   venv/bin/python /tmp/get-pip.py
   venv/bin/pip install -r requirements.txt
   ```

3. **`check_env.py` 失敗（missing_required / invalid_values）**  
   請在 `backend/.env` 設定必填變數：`DATABASE_URL`、`OPENAI_API_KEY`、`SECRET_KEY`。  
   範例（production-like defaults / 非 localhost canonical runtime）：  
   `DATABASE_URL=postgresql://...`  
   `OPENAI_API_KEY=sk-...`  
   `SECRET_KEY=至少 32 字元的密鑰`

4. **Port 8000 已被佔用**  
   改 port：`PORT=8001 ./scripts/run-dev.sh`

4b. **`[Errno 48] Address already in use` 出現在 "Started reloader process" 之後**  
   macOS 上 uvicorn 的 `--reload` 會讓主 process 與子 process 搶同一個 port。先關掉 reload 再啟動：  
   `RELOAD=0 ./scripts/run-dev.sh`  
   改程式後需手動 Ctrl+C 再重啟。

4c. **路徑含中文/括號時，卡在「loading app」、沒有 "Uvicorn running on..."**  
   專案或 venv 路徑若含中文或括號（例如 `Haven（棲）正式版 --- Gemini 版`），載入時讀檔可能卡住。  
   **解法一：僅 venv 在純英文路徑**（有時仍會卡在載入 app 程式碼時）  
   - 從**專案根目錄**執行 pip（路徑才對）：  
     `~/haven-venv/bin/pip install -r backend/requirements.txt`  
   - 若已在 `backend/` 下，用：  
     `~/haven-venv/bin/pip install -r requirements.txt`  
   - 啟動：  
     `cd backend && RELOAD=0 BACKEND_PYTHON_BIN=~/haven-venv/bin/python ./scripts/run-dev.sh`  

   **解法二：整個專案搬到純英文路徑**（最穩，避免 app 程式碼讀檔卡住）  
   ```bash
   # 複製或 clone 到不含中文的路徑，例如
   cp -R "/Users/你/Desktop/.../Haven（棲）正式版 --- Gemini 版" ~/projects/haven
   cd ~/projects/haven/backend
   python3 -m venv .venv-gate
   .venv-gate/bin/pip install -r requirements.txt
   export ABUSE_GUARD_STORE_BACKEND=memory
   BACKEND_PYTHON_BIN=.venv-gate/bin/python RELOAD=0 ./scripts/run-dev.sh
   ```

5. **執行 `./scripts/run-dev.sh` 後只看到「annotated_doc ready」或「[worker] loading app.main...」就停住、沒有「app loaded in worker」**  
   代表 worker 在 **import FastAPI / app.main** 時卡住（此環境下常見，尤其 Python 3.13）。可試：  
   - **用 Python 3.12 跑後端**（uv 會自動下載 3.12）：  
     ```bash
     cd backend
     ./scripts/run-dev-python312.sh
     ```  
     第一次會建立 `venv312` 並安裝依賴，之後直接啟動。  
   - 或手動建 Python 3.11/3.12 venv：  
     `uv venv venv312 --python 3.12` → `uv pip install -r requirements.txt --python venv312/bin/python` →  
     `BACKEND_PYTHON_BIN=venv312/bin/python ./scripts/run-dev.sh`  
   - 若仍卡住，可暫時用 **Docker** 跑後端（若專案有 Dockerfile），避開本機 import 問題。

6. **執行 `uvicorn app.main:app --reload` 後完全沒輸出、游標停住**  
   常見原因：  
   - **Redis**：`.env` 裡有 `ABUSE_GUARD_STORE_BACKEND=redis` 且設了 `ABUSE_GUARD_REDIS_URL`，但本機沒跑 Redis 或連不上，載入時可能卡住。  
     **先改回記憶體模式**（不連 Redis）再啟動：  
     ```bash
     export ABUSE_GUARD_STORE_BACKEND=memory
     uvicorn app.main:app --reload
     ```  
     或把 `backend/.env` 裡的 `ABUSE_GUARD_STORE_BACKEND` 改成 `memory` 後存檔再跑。  
   - **Import 卡住**：FastAPI / 其他套件載入過慢或卡住（例如網路問題）。可強制不緩衝輸出看卡在哪：  
     ```bash
     PYTHONUNBUFFERED=1 uvicorn app.main:app --reload
     ```

---

## 正確啟動方式 (How to run the backend)

在 **backend** 目錄下執行：

```bash
cd backend

# 1. 建立虛擬環境（若尚未建立）
python3 -m venv .venv-gate

# 2. 安裝依賴（使用顯式 Python 路徑，避免 activate 腳本絕對路徑問題）
.venv-gate/bin/pip install -r requirements.txt
# 開發時可裝
# .venv-gate/bin/pip install -r requirements-dev.txt

# 3. 啟動後端（腳本會自動用 venv 裡的 Python）
BACKEND_PYTHON_BIN=.venv-gate/bin/python ./scripts/run-dev.sh
```

或指定 Python（例如 CI 用的路徑）：

```bash
BACKEND_PYTHON_BIN=/path/to/venv/bin/python ./scripts/run-dev.sh
```

成功時會看到 uvicorn 訊息，例如：  
`Uvicorn running on http://0.0.0.0:8000`

---

## 健康檢查

啟動後可測試：

```bash
curl -s http://localhost:8000/health | head -20
```

---

## 本機穩定檢查命令（避開壞掉的 venv wrapper）

若 `source venv/bin/activate` 後出現 `ruff/pytest/alembic` 指令不存在，請改用明確 Python module 方式：

```bash
cd backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider
BACKEND_PYTHON_BIN=.venv-gate/bin/python ./scripts/run-alembic.sh upgrade head
# 分層穩定測試（unit/contract -> integration，可選 slow）
BACKEND_PYTHON_BIN=.venv-gate/bin/python ./scripts/run_pytest_stable.sh
```

說明：
- `run-alembic.sh` 會用 `python -m alembic`，不依賴 `.venv-gate/bin/alembic` wrapper 的 shebang。
- 若是全新 sqlite，先執行本文下方的 bootstrap 步驟再跑 upgrade。

### run-alembic modes（legacy / fresh / verify）

`run-alembic.sh` 支援三種模式：

```bash
# 既有資料庫（預設）
./scripts/run-alembic.sh --mode legacy-upgrade upgrade head

# Canonical localhost Postgres
DATABASE_URL=postgresql://haven:haven_local_dev@127.0.0.1:55432/haven_local ./scripts/run-alembic.sh upgrade head

# sqlite 僅保留給測試 / rehearsal
DATABASE_URL=sqlite:///./test.db ./scripts/run-alembic.sh --mode fresh-bootstrap

# 只做 preflight 驗證，不執行 migration
./scripts/run-alembic.sh --mode verify-only
```

細節與回滾策略請見：`/Users/alanzeng/Desktop/Projects/Haven/docs/backend/MIGRATION_ORCHESTRATION.md`

---

## SQLite 遷移卡在 legacy baseline 時（本機開發）

若執行 `./scripts/run-alembic.sh upgrade head` 出現：
- `missing legacy tables: users, journal` 或
- `this migration chain assumes a legacy pre-alembic schema baseline`

代表你在「全新 sqlite 檔」上直接跑到舊遷移鏈，這是目前遷移歷史的既有限制。  
建議先做一次本機 bootstrap（只適用空 sqlite）：

```bash
cd backend
export DATABASE_URL=sqlite:///./test.db
.venv-gate/bin/python scripts/bootstrap-sqlite-schema.py
```

完成後再執行：

```bash
./scripts/run-alembic.sh upgrade head
```
