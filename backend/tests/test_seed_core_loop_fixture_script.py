from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from sqlmodel import Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.events_log import EventsLog  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.core_loop_runtime import (  # noqa: E402
    build_core_loop_snapshot,
    evaluate_core_loop_snapshot,
)

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "seed_core_loop_fixture.py"
_SPEC = importlib.util.spec_from_file_location("seed_core_loop_fixture", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load script module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class SeedCoreLoopFixtureScriptTests(unittest.TestCase):
    def test_main_seeds_fixture_that_passes_core_loop_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = Path(tmpdir) / "core-loop-fixture.db"
            database_url = f"sqlite:///{database_path}"

            exit_code = _MODULE.main(
                [
                    "--database-url",
                    database_url,
                ]
            )

            self.assertEqual(exit_code, 0)
            engine = create_engine(database_url, connect_args={"check_same_thread": False})
            with Session(engine) as session:
                users_total = len(session.exec(select(User)).all())
                events_total = len(session.exec(select(EventsLog)).all())
                snapshot = build_core_loop_snapshot(session=session, window_days=1)
            evaluation = evaluate_core_loop_snapshot(snapshot)

            self.assertEqual(users_total, 10)
            self.assertGreater(events_total, 0)
            self.assertEqual(snapshot["counts"]["active_users_total"], 10)
            self.assertEqual(snapshot["counts"]["loop_completed_users_total"], 4)
            self.assertEqual(evaluation["status"], "pass")


if __name__ == "__main__":
    unittest.main()
