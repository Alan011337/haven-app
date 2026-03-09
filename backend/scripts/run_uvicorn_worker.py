#!/usr/bin/env python3
"""
Worker: 在子行程內載入 app 並執行 uvicorn。載入成功後寫入 READY_FD，
父行程可據此判斷是否逾時（例如 FastAPI import 卡住時永遠不會寫入）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parents[1]
_backend_root_str = str(_backend_root)
if _backend_root_str not in sys.path:
    sys.path.insert(0, _backend_root_str)

# 與 run_uvicorn.py 相同的 annotated_doc 預載
import importlib.util  # noqa: E402
_shim_path = _backend_root / "annotated_doc.py"
_spec = importlib.util.spec_from_file_location("annotated_doc", _shim_path)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["annotated_doc"] = _mod
_spec.loader.exec_module(_mod)
assert hasattr(_mod, "Doc")

# 可能卡在這裡（FastAPI / app.main import）
print("[worker] loading app.main...", flush=True)
from app.main import app  # noqa: E402
print("[worker] app.main loaded.", flush=True)

ready_fd = int(os.environ.get("READY_FD", "-1"))
if ready_fd >= 0:
    os.write(ready_fd, b"ready\n")
    os.close(ready_fd)

import uvicorn  # noqa: E402
host = os.environ.get("HOST", "0.0.0.0")
port = int(os.environ.get("PORT", "8000"))
uvicorn.run(app, host=host, port=port, reload=False)
