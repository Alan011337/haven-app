#!/usr/bin/env bash
# 在「純英文路徑」的專案副本裡建立 venv 並啟動後端。
# 使用方式：
#   1. 先把整個專案複製到純英文路徑，例如：
#      mkdir -p ~/projects
#      cp -R "/Users/alanzeng/Desktop/我打造的軟體產品/Haven（棲）正式版 --- Gemini 版" ~/projects/haven
#   2. 進入 backend 並執行此腳本：
#      cd ~/projects/haven/backend
#      bash scripts/setup-and-run-from-plain-path.sh
#   或從本專案直接執行（會提示你先複製）：
#      cd backend && bash scripts/setup-and-run-from-plain-path.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_DIR}"

# 檢查路徑是否含非 ASCII（中文/括號等）
CURRENT_PATH="$(pwd)"
if python3 -c "
import sys
p = r'''${CURRENT_PATH}'''
try:
    p.encode('ascii')
except UnicodeEncodeError:
    sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    : # 路徑為純 ASCII，OK
else
    echo "目前路徑含非 ASCII 字元（中文/括號等），在此路徑下啟動可能卡住。"
    echo "請先將專案複製到純英文路徑，例如："
    echo "  mkdir -p ~/projects"
    echo "  cp -R \"$(cd "${BACKEND_DIR}/../.." 2>/dev/null && pwd || echo '你的專案根目錄')\" ~/projects/haven"
    echo "  cd ~/projects/haven/backend"
    echo "  bash scripts/setup-and-run-from-plain-path.sh"
    exit 1
fi

echo "[1/3] 建立 venv..."
python3 -m venv venv
echo "[2/3] 安裝依賴..."
./venv/bin/pip install -q -r requirements.txt
echo "[3/3] 啟動後端 (RELOAD=0, ABUSE_GUARD_STORE_BACKEND=memory)..."
export ABUSE_GUARD_STORE_BACKEND=memory
export PYTHONUNBUFFERED=1
RELOAD=0 exec ./venv/bin/python scripts/run_uvicorn.py
