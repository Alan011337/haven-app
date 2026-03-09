from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "cleanup-dev-processes.sh"


def test_cleanup_dev_processes_script_exists_and_executable() -> None:
    assert SCRIPT_PATH.exists()
    assert SCRIPT_PATH.stat().st_mode & 0o111


def test_cleanup_dev_processes_script_targets_expected_processes() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "release-gate-local\\.sh" in text
    assert "security-gate\\.sh" in text
    assert "pytest -q -p no:cacheprovider" in text
    assert "--apply" in text
