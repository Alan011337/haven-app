#!/usr/bin/env python3
"""
找出後端啟動時卡在哪一個 import（順序與 app.main 一致）。
執行：在 backend 目錄下
  cd backend
  export ABUSE_GUARD_STORE_BACKEND=memory
  export PYTHONPATH=.
  export PYTHONUTF8=1
  .venv-gate/bin/python scripts/diagnose_startup.py
"""
from __future__ import annotations

import sys
from pathlib import Path

def step(msg: str) -> None:
    print(msg, flush=True)

# 與 main.py 相同的 path 設定
_backend_root = Path(__file__).resolve().parents[1]
_backend_root_str = str(_backend_root)
if _backend_root_str not in sys.path:
    sys.path.insert(0, _backend_root_str)

step("1. path ok, importing annotated_doc...")
import annotated_doc as _annotated_doc  # noqa: E402
assert hasattr(_annotated_doc, "Doc"), "backend/annotated_doc.py must provide Doc"
step("2. annotated_doc ok, importing pydantic...")
step("3. pydantic ok")
step("4. importing stdlib (contextlib, json, logging, os, time, uuid)...")
step("5. stdlib ok")
step("5b. force annotated_doc into sys.modules (so deps get our shim)...")
import annotated_doc as _ad2  # noqa: E402
_ad_path = getattr(_ad2, "__file__", "") or ""
assert _ad_path.startswith(str(_backend_root)), f"annotated_doc must be from backend, got {_ad_path!r}"
step("5c. importing starlette (fastapi dep)...")
step("6. starlette ok, importing fastapi...")
step("7. fastapi ok")
step("8. importing jose...")
step("9. jose ok")
step("10. importing sqlmodel...")
step("11. sqlmodel ok")
step("12. importing app.core.config...")
step("13. config ok")
step("14. importing app.api (login, journals)...")
step("15. app.api ok")
step("16. importing app.api.routers (billing, cards, users, card_decks)...")
step("17. routers ok")
step("18. importing app.core.datetime_utils, socket_manager, db.session, models.user...")
step("19. core/db/models ok")
step("20. importing app.services (abuse_state_store, ws_abuse_guard, ...)...")
step("21. services ok")
step("22. importing app.middleware, structured_logger...")
step("23. middleware/logger ok")
step("24. importing app.main (full module - will run module-level code)...")
step("25. app.main ok - startup would succeed")
