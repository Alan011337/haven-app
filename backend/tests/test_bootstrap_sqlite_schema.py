import importlib.util
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


class BootstrapSqliteSchemaTests(unittest.TestCase):
    def _run_bootstrap(self, db_path: Path) -> subprocess.CompletedProcess[str]:
        backend_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path}"
        env["OPENAI_API_KEY"] = env.get("OPENAI_API_KEY", "test-key")
        env["SECRET_KEY"] = env.get("SECRET_KEY", "01234567890123456789012345678901")
        env["ABUSE_GUARD_STORE_BACKEND"] = "memory"

        return subprocess.run(
            [sys.executable, "scripts/bootstrap-sqlite-schema.py"],
            cwd=backend_root,
            env=env,
            capture_output=True,
            text=True,
        )

    def test_bootstrap_initializes_empty_sqlite_and_stamps_head(self) -> None:
        if importlib.util.find_spec("alembic") is None:
            self.skipTest("alembic not installed in test interpreter")

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "bootstrap.db"
            result = self._run_bootstrap(db_path)
            output = f"{result.stdout}\n{result.stderr}"
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("ok: initialized", output)

            conn = sqlite3.connect(str(db_path))
            try:
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertIn("alembic_version", tables)
                self.assertIn("users", tables)
                version_rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
                self.assertEqual(len(version_rows), 1)
                self.assertTrue(bool(version_rows[0][0]))
            finally:
                conn.close()

    def test_bootstrap_refuses_non_empty_database(self) -> None:
        if importlib.util.find_spec("alembic") is None:
            self.skipTest("alembic not installed in test interpreter")

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "existing.db"
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute("CREATE TABLE custom_table (id INTEGER PRIMARY KEY)")
                conn.commit()
            finally:
                conn.close()

            result = self._run_bootstrap(db_path)
            output = f"{result.stdout}\n{result.stderr}"
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn("Refusing to bootstrap non-empty sqlite DB", output)


if __name__ == "__main__":
    unittest.main()
