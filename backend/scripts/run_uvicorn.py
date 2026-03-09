#!/usr/bin/env python3
"""
Bootstrap: 先將 backend 根目錄加入 sys.path，再啟動 uvicorn。
RELOAD=0 時改由子行程載入 app，父行程等「ready」逾時則報錯，避免主行程卡在 FastAPI import。
"""
from __future__ import annotations

import importlib.util
import os
import signal
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parents[1]
_backend_root_str = str(_backend_root)
if _backend_root_str not in sys.path:
    sys.path.insert(0, _backend_root_str)

# 在 import uvicorn 前強制把我們的 annotated_doc 註冊到 sys.modules
print("[run_uvicorn] preloading backend annotated_doc into sys.modules...", flush=True)
_shim_path = _backend_root / "annotated_doc.py"
_spec = importlib.util.spec_from_file_location("annotated_doc", _shim_path)
assert _spec and _spec.loader, "backend/annotated_doc.py not found"
_mod = importlib.util.module_from_spec(_spec)
sys.modules["annotated_doc"] = _mod
_spec.loader.exec_module(_mod)
assert hasattr(_mod, "Doc"), "backend/annotated_doc must provide Doc"
print("[run_uvicorn] annotated_doc ready.", flush=True)

host = os.environ.get("HOST", "0.0.0.0")
port = os.environ.get("PORT", "8000")
reload = os.environ.get("RELOAD", "1").strip().lower() in ("1", "true", "yes")

if reload:
    # Exec into uvicorn so the reloader's child runs "python -m uvicorn ...", not
    # "python run_uvicorn.py" again (which would bind the same port twice → Errno 48).
    # app.main now preloads annotated_doc at import time, so the child gets the shim.
    print("[run_uvicorn] exec uvicorn (reload)...", flush=True)
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", _backend_root_str)
    if _backend_root_str not in env["PYTHONPATH"].split(os.pathsep):
        env["PYTHONPATH"] = _backend_root_str + os.pathsep + env["PYTHONPATH"]
    # Only watch app/ so venv/venv312/.venv-gate and site-packages never trigger reload
    argv = [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", host, "--port", str(port), "--reload",
        "--reload-dir", "app",
    ]
    os.execve(sys.executable, argv, env)
else:
    # RELOAD=0: run app in main process (RUN_APP_IN_MAIN_PROCESS=1) or in worker subprocess
    run_in_main = os.environ.get("RUN_APP_IN_MAIN_PROCESS", "").strip().lower() in ("1", "true", "yes")
    if run_in_main:
        # Load and run in this process; avoids worker subprocess hang on some macOS/Python envs.
        # Pre-import pydantic_settings so the one-time hang (if any) happens here; then
        # app.main and its deps (which use config.settings) see it already in sys.modules.
        print("[run_uvicorn] warming up pydantic_settings...", flush=True)
        import pydantic_settings  # noqa: F401
        print("[run_uvicorn] loading app in main process...", flush=True)
        import uvicorn
        from app.main import app  # noqa: E402
        print("[run_uvicorn] app loaded. Starting uvicorn at http://%s:%s" % (host, port), flush=True)
        uvicorn.run(app, host=host, port=int(port), reload=False)
        sys.exit(0)
    # Worker path: spawn child to load app, wait for ready
    import select
    import subprocess

    rd, wr = os.pipe()
    env = os.environ.copy()
    env["READY_FD"] = str(wr)
    env["HOST"] = host
    env["PORT"] = port
    worker_script = _backend_root / "scripts" / "run_uvicorn_worker.py"
    proc = subprocess.Popen(
        [sys.executable, str(worker_script)],
        env=env,
        cwd=str(_backend_root),
        pass_fds=(wr,),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    os.close(wr)
    LOAD_TIMEOUT = 60
    r, _, _ = select.select([rd], [], [], LOAD_TIMEOUT)
    if r:
        data = os.read(rd, 64).decode("utf-8", errors="ignore")
        os.close(rd)
        if data.strip() == "ready":
            print("[run_uvicorn] app loaded in worker (PID %s). Server at http://%s:%s" % (proc.pid, host, port), flush=True)
            def forward(signum, frame):
                proc.terminate()
                sys.exit(128 + signum if signum in (2, 15) else 0)
            signal.signal(signal.SIGINT, forward)
            signal.signal(signal.SIGTERM, forward)
            sys.exit(proc.wait())
    os.close(rd)
    proc.terminate()
    proc.wait(timeout=5)
    print(
        "\n[run_uvicorn] App did not load within %s seconds (often: FastAPI import hangs on this machine).\n"
        "Common causes: iCloud dataless files in repo/venv, or a blocked dependency import.\n"
        "Try: materialize files (`python ../scripts/check-worktree-materialization.py --root ..`),\n"
        "then rerun. You can also force main-process load with RUN_APP_IN_MAIN_PROCESS=1.\n"
        "See backend/BACKEND-RUN.md for recovery steps.\n"
        % LOAD_TIMEOUT,
        file=sys.stderr,
        flush=True,
    )
    sys.exit(1)
