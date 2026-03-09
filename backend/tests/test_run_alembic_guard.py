import importlib.util
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid


class RunAlembicGuardTests(unittest.TestCase):
    def test_verify_only_fails_fast_when_sqlite_file_is_missing(self) -> None:
        if importlib.util.find_spec("alembic") is None:
            self.skipTest("alembic not installed in test interpreter")

        backend_root = Path(__file__).resolve().parents[1]
        missing_name = f"tmp-missing-verify-{uuid.uuid4().hex}.db"
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{missing_name}"
        env["BACKEND_PYTHON_BIN"] = sys.executable

        result = subprocess.run(
            ["bash", "scripts/run-alembic.sh", "--mode", "verify-only"],
            cwd=backend_root,
            env=env,
            capture_output=True,
            text=True,
        )

        combined_output = f"{result.stdout}\n{result.stderr}"
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bootstrap check failed: sqlite db file not found", combined_output)

    def test_fresh_bootstrap_initializes_missing_sqlite_database(self) -> None:
        if importlib.util.find_spec("alembic") is None:
            self.skipTest("alembic not installed in test interpreter")

        backend_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "fresh-bootstrap.db"
            env = os.environ.copy()
            env["DATABASE_URL"] = f"sqlite:///{db_path}"
            env["BACKEND_PYTHON_BIN"] = sys.executable
            env.pop("ALLOW_EMPTY_DB_MIGRATION", None)

            result = subprocess.run(
                ["bash", "scripts/run-alembic.sh", "--mode", "fresh-bootstrap"],
                cwd=backend_root,
                env=env,
                capture_output=True,
                text=True,
            )

            combined_output = f"{result.stdout}\n{result.stderr}"
            self.assertEqual(result.returncode, 0, msg=combined_output)
            self.assertTrue(db_path.exists())

            conn = sqlite3.connect(str(db_path))
            try:
                version_rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
            finally:
                conn.close()
            self.assertEqual(len(version_rows), 1)

    def test_upgrade_head_fails_fast_when_sqlite_file_is_missing(self) -> None:
        if importlib.util.find_spec("alembic") is None:
            self.skipTest("alembic not installed in test interpreter")

        backend_root = Path(__file__).resolve().parents[1]
        missing_name = f"tmp-missing-{uuid.uuid4().hex}.db"
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{missing_name}"
        env["BACKEND_PYTHON_BIN"] = sys.executable
        env.pop("ALLOW_EMPTY_DB_MIGRATION", None)

        result = subprocess.run(
            ["bash", "scripts/run-alembic.sh", "upgrade", "head"],
            cwd=backend_root,
            env=env,
            capture_output=True,
            text=True,
        )

        combined_output = f"{result.stdout}\n{result.stderr}"
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bootstrap check failed: sqlite db file not found", combined_output)
        self.assertIn("set DATABASE_URL to a provisioned DB", combined_output)
        self.assertIn("bootstrap-sqlite-schema.py", combined_output)

    def test_upgrade_head_fails_fast_when_sqlite_has_no_legacy_tables(self) -> None:
        if importlib.util.find_spec("alembic") is None:
            self.skipTest("alembic not installed in test interpreter")

        backend_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "empty.db"
            db_path.touch()
            env = os.environ.copy()
            env["DATABASE_URL"] = f"sqlite:///{db_path}"
            env["BACKEND_PYTHON_BIN"] = sys.executable
            env.pop("ALLOW_EMPTY_DB_MIGRATION", None)

            result = subprocess.run(
                ["bash", "scripts/run-alembic.sh", "upgrade", "head"],
                cwd=backend_root,
                env=env,
                capture_output=True,
                text=True,
            )

        combined_output = f"{result.stdout}\n{result.stderr}"
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing legacy tables", combined_output)
        self.assertIn("bootstrap-sqlite-schema.py", combined_output)

    def test_upgrade_head_fails_fast_when_alembic_version_is_invalid(self) -> None:
        if importlib.util.find_spec("alembic") is None:
            self.skipTest("alembic not installed in test interpreter")

        backend_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "invalid-version.db"
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
                conn.commit()
            finally:
                conn.close()

            env = os.environ.copy()
            env["DATABASE_URL"] = f"sqlite:///{db_path}"
            env["BACKEND_PYTHON_BIN"] = sys.executable
            env.pop("ALLOW_EMPTY_DB_MIGRATION", None)

            result = subprocess.run(
                ["bash", "scripts/run-alembic.sh", "upgrade", "head"],
                cwd=backend_root,
                env=env,
                capture_output=True,
                text=True,
            )

        combined_output = f"{result.stdout}\n{result.stderr}"
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid alembic_version rows", combined_output)
        self.assertIn("bootstrap-sqlite-schema.py", combined_output)


if __name__ == "__main__":
    unittest.main()
