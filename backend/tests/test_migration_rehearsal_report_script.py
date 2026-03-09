from __future__ import annotations

import json
import subprocess
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_migration_rehearsal_report.py"


def test_migration_rehearsal_script_dry_run_writes_report(tmp_path: Path) -> None:
    report_path = tmp_path / "rehearsal-report.json"
    result = subprocess.run(
        [
            str(SCRIPT_PATH),
            "--dry-run",
            "--report-path",
            str(report_path),
        ],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, f"stderr={result.stderr}\nstdout={result.stdout}"
    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["artifact_kind"] == "migration-rehearsal-report"
    assert payload["schema_version"] == "v1"
    assert payload["status"] == "dry_run"
    assert isinstance(payload.get("steps"), list) and len(payload["steps"]) >= 3
    assert payload["steps"][0]["status"] == "planned"

