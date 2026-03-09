"""Test migration contract for timeline cursor tie-break indexes (h1core0000011)."""

from __future__ import annotations

from pathlib import Path


def test_migration_h1core0000011_exists_with_expected_indexes() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "h1core0000011_add_timeline_cursor_tiebreak_indexes.py"
    )
    assert migration_path.exists(), f"Migration file not found: {migration_path}"

    content = migration_path.read_text(encoding="utf-8")
    assert 'revision: str = "h1core0000011"' in content
    assert 'down_revision: Union[str, Sequence[str], None] = "h1core0000010"' in content
    assert "ix_journals_user_deleted_created_id" in content
    assert "ix_card_sessions_creator_deleted_created_id" in content
    assert "ix_card_sessions_partner_deleted_created_id" in content
