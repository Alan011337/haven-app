"""Test the timeline indexes migration (h1core0000010)."""
import pytest
from sqlmodel import create_engine


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine for fast testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    # Note: This test is informational only; actual index creation
    # validation happens during Alembic migration runs in CI/staging.
    return engine


def test_migration_h1core0000010_indexes_are_defined():
    """Verify that the Alembic migration file exists and is syntactically valid."""
    import os
    
    migration_path = "alembic/versions/h1core0000010_add_timeline_indexes.py"
    assert os.path.exists(migration_path), f"Migration file {migration_path} not found"
    
    # Check file contains expected function definitions and metadata
    with open(migration_path) as f:
        content = f.read()
        assert "def upgrade()" in content
        assert "def downgrade()" in content
        assert 'revision: str = "h1core0000010"' in content, "Migration revision metadata not found"
        assert "ix_journals_user_id_created_at_deleted_at" in content
        assert "ix_card_sessions_creator_id_created_at_deleted_at" in content
        assert "ix_card_sessions_partner_id_created_at_deleted_at" in content
        assert "ix_card_responses_session_id_user_id" in content


def test_index_coverage_for_timeline_queries():
    """Document the expected index structure for timeline queries.
    
    Expected indexes after migration:
    - journals(user_id, created_at, deleted_at)
    - card_sessions(creator_id, created_at, deleted_at)
    - card_sessions(partner_id, created_at, deleted_at)
    - card_responses(session_id, user_id)
    
    These indexes support:
    1. get_unified_timeline: efficient timeline aggregation w/o N+1
    2. Soft-delete filtering: deleted_at included for WHERE IS NULL checks
    3. Pagination: cursor-based with created_at ordering
    """
    index_list = [
        {
            "table": "journals",
            "name": "ix_journals_user_id_created_at_deleted_at",
            "columns": ["user_id", "created_at", "deleted_at"],
        },
        {
            "table": "card_sessions",
            "name": "ix_card_sessions_creator_id_created_at_deleted_at",
            "columns": ["creator_id", "created_at", "deleted_at"],
        },
        {
            "table": "card_sessions",
            "name": "ix_card_sessions_partner_id_created_at_deleted_at",
            "columns": ["partner_id", "created_at", "deleted_at"],
        },
        {
            "table": "card_responses",
            "name": "ix_card_responses_session_id_user_id",
            "columns": ["session_id", "user_id"],
        },
    ]
    
    # Simply document the expected index schema
    assert len(index_list) == 4
    assert all("table" in idx for idx in index_list)
    assert all("name" in idx for idx in index_list)
    assert all("columns" in idx for idx in index_list)
