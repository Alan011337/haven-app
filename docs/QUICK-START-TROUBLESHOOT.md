# 前後端啟動排錯 (Quick Start Troubleshoot)

## 現象：後端只看到 "Started reloader process"、沒有 "Haven backend starting up"

**原因**：直接用 `uvicorn app.main:app --reload` 時，worker 在載入 `app` 時可能卡住（路徑或 Redis 等）。

**做法**：用專案腳本啟動，並強制用記憶體模式避免 Redis 卡住：

```bash
cd backend
export ABUSE_GUARD_STORE_BACKEND=memory
./scripts/run-dev.sh
```

成功時會看到：
- `[run_uvicorn] starting uvicorn...`
- `[run_uvicorn] uvicorn imported, loading app...`
- `INFO:     Uvicorn running on http://0.0.0.0:8000`
- 以及 log 裡有 `Haven backend starting up`

若仍卡住，可關掉 reload 再試（避免 macOS 上 port 搶用）：

```bash
RELOAD=0 ./scripts/run-dev.sh
```

---

## 現象：前端只看到 "next dev"、沒有 "Ready" 或網址

**可能**：Next.js 第一次編譯較久，或編譯錯誤沒顯示完整。

**做法**：
1. 多等 10–30 秒看是否出現 `Ready in ...` 和 `http://localhost:3000`。
2. 確認有裝依賴：`npm install`
3. 若有錯誤，可開除錯：`DEBUG=* npm run dev`

---

## 現象：首頁開 5–10 分鐘都沒好，Network 沒有 API 請求、後端有在跑

**原因**：卡在 Next.js（預設 Turbopack）編譯或產出首屏，不是卡在 API。所以瀏覽器連 API 都還沒發。

**做法**：
1. 先試改用 Webpack 跑 dev：`npm run dev:webpack`（第一次會較慢，但較穩定）。
2. 若仍卡住：在 Network 看「第一個請求」（對 `localhost:3000` 的那筆）是否一直 Pending；若是，代表 Next 編譯/SSR 卡住。
3. 必要時清快取再試：刪掉 `frontend/.next` 後重新 `npm run dev` 或 `npm run dev:webpack`。

---

## 快速驗證

- **後端**：`curl -s http://localhost:8000/health`
- **前端**：瀏覽器開 `http://localhost:3000`

詳見 `backend/BACKEND-RUN.md`。

---

## 現象：venv activate 後沒反應（無 (venv) 前綴）

**原因**：macOS 預設是 zsh，而 venv 的 `activate` 是給 bash 用的，在 zsh 裡會解析錯誤。

**做法**：
```bash
cd backend
source venv/bin/activate.zsh
```
會看到 `(venv)` 前綴。若不想 activate，可直接用 `./venv/bin/python` 或 `./scripts/run-dev.sh`。

---

## 審計驗證 (P0/P1 Audit)

- **後端單元/合約測試**：`cd backend && PYTHONPATH=. ./venv/bin/python -m pytest`（或 `python3 -m pytest` 若已啟用 venv）。需 pytest 在 venv 內。
- **Security gate**：`cd backend && bash scripts/security-gate.sh`
- **前端**：`cd frontend && npm run build && npm run lint && npm run typecheck`
- **E2E**：`cd frontend && npm run test:e2e`

完整指令見 `docs/plan/PHASE0_REPO_DISCOVERY.md` (section G) 與 `docs/plan/P0_P1_AUDIT.md` (Verification 區塊)。
