"""Migration contract test for durable notification outbox table (h1core0000012)."""

from __future__ import annotations

from pathlib import Path


def test_migration_h1core0000012_exists_with_expected_table_contract() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "h1core0000012_add_notification_outbox.py"
    )
    assert migration_path.exists(), f"Migration file not found: {migration_path}"

    content = migration_path.read_text(encoding="utf-8")
    assert 'revision: str = "h1core0000012"' in content
    assert 'down_revision: Union[str, Sequence[str], None] = "h1core0000011"' in content
    assert '"notification_outbox"' in content
    assert "ix_notification_outbox_status_available_at" in content
    assert "ix_notification_outbox_dedupe_key" in content
