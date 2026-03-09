from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_notification_outbox_recovery.py"


def test_notification_outbox_recovery_script_json_dry_run() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--json"],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, f"stderr={result.stderr}\nstdout={result.stdout}"
    payload = json.loads(result.stdout)
    assert "mode" in payload
    assert payload["mode"] in {"dry_run", "apply"}
    assert "dead_rows" in payload
    assert "dead_letter_rate" in payload
    assert "replayed" in payload
