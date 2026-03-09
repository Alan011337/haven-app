from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "clean-evidence-noise.sh"


def test_clean_evidence_noise_script_exists_and_is_executable() -> None:
    assert SCRIPT_PATH.exists()
    assert SCRIPT_PATH.stat().st_mode & 0o111, "clean-evidence-noise.sh must be executable"


def test_clean_evidence_noise_script_targets_latest_and_timestamped_untracked_noise() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "git -C" in source
    assert "ls-files --error-unmatch" in source
    assert "\"*-latest.json\"" in source
    assert "EVIDENCE_NOISE_PRUNE_TIMESTAMPED" in source
    assert "\"*-20??????T??????Z." in source
    assert "removed_untracked_timestamped" in source
    assert "docs/security/evidence" in source
    assert "docs/sre/evidence" in source
