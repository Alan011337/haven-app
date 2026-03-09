"""Migration contract test for API idempotency + events rollup tables (h1core0000016)."""

from pathlib import Path


def test_migration_h1core0000016_exists_with_expected_tables() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "h1core0000016_add_idempotency_and_events_rollup.py"
    )
    assert migration_path.exists(), "Expected migration file is missing."
    content = migration_path.read_text(encoding="utf-8")
    assert 'revision: str = "h1core0000016"' in content
    assert 'down_revision: Union[str, Sequence[str], None] = "h1core0000015"' in content
    assert '"api_idempotency_records"' in content
    assert '"events_log_daily_rollups"' in content
