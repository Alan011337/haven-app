from __future__ import annotations

import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "migration-rehearsal-postgres.yml"


class MigrationRehearsalPostgresWorkflowContractTests(unittest.TestCase):
    def test_workflow_declares_postgres_service(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("services:", text)
        self.assertIn("postgres:", text)
        self.assertIn("image: postgres:16", text)

    def test_workflow_runs_upgrade_downgrade_rehearsal(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("./scripts/run-alembic.sh --mode verify-only", text)
        self.assertIn("./scripts/run-alembic.sh upgrade head", text)
        self.assertIn("./scripts/run-alembic.sh downgrade -1", text)
        self.assertIn("MIGRATION_REHEARSAL_MAX_SECONDS", text)
        self.assertIn("[migration-rehearsal] seed fixture inserted", text)
        self.assertIn("MIGRATION_REHEARSAL_ELAPSED_SECONDS", text)
        self.assertIn("elapsed_seconds", text)
        self.assertIn("migration-rehearsal-postgres", text)
        self.assertIn("Open or Update Alert Issue", text)


if __name__ == "__main__":
    unittest.main()
