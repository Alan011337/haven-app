"""Test migration contract for timeline hot-path indexes (h1core0000015)."""

from __future__ import annotations

from pathlib import Path


def test_migration_h1core0000015_exists_with_expected_indexes() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "h1core0000015_add_timeline_hot_path_indexes.py"
    )
    assert migration_path.exists(), f"Migration file not found: {migration_path}"

    content = migration_path.read_text(encoding="utf-8")
    assert 'revision: str = "h1core0000015"' in content
    assert 'down_revision: Union[str, Sequence[str], None] = "h1core0000014"' in content
    assert "ix_card_sessions_mode_status_creator_deleted_created_id" in content
    assert "ix_card_sessions_mode_status_partner_deleted_created_id" in content
    assert "ix_card_responses_session_deleted_user" in content
