#!/usr/bin/env python3
"""Run pip install with step markers so we see where it blocks."""
import os
import socket
import subprocess
import sys

def log(msg: str) -> None:
    print(msg, flush=True)

log("[pip-with-log] 0. Checking PyPI reachability (pypi.org:443)...")
try:
    s = socket.create_connection(("pypi.org", 443), timeout=5)
    s.close()
    log("[pip-with-log] 0. PyPI reachable.")
except OSError as e:
    log("[pip-with-log] 0. PyPI not reachable: " + str(e) + " (pip may hang)")

log("[pip-with-log] 1. Testing pip --version (if this hangs, pip module load blocks)...")
try:
    rc_v = subprocess.run([sys.executable, "-u", "-m", "pip", "--version"], env={**os.environ, "PYTHONUNBUFFERED": "1"}, capture_output=True, timeout=10)
    log("[pip-with-log] 1. pip --version done (code %s)." % rc_v.returncode)
except subprocess.TimeoutExpired:
    log("[pip-with-log] 1. pip --version HANGED (timeout 10s).")
except Exception as e:
    log("[pip-with-log] 1. Error: " + str(e))
log("[pip-with-log] 2. Starting pip install...")
os.environ["PYTHONUNBUFFERED"] = "1"
argv = [sys.executable, "-u", "-m", "pip", "install", "-v", "--no-cache-dir"]
argv.extend(sys.argv[1:])
log("[pip-with-log] 3. Exec: " + " ".join(argv))
try:
    rc = subprocess.run(argv, env=os.environ, stdout=None, stderr=None)
    log("[pip-with-log] 4. Pip exited with code " + str(rc.returncode))
except Exception as e:
    log("[pip-with-log] 4. Error: " + str(e))
    sys.exit(1)
