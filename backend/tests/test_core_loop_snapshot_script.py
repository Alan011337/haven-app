from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.datetime_utils import utcnow  # noqa: E402
from app.models.events_log import EventsLog  # noqa: E402
from app.models.user import User  # noqa: E402

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_core_loop_snapshot.py"
_SPEC = importlib.util.spec_from_file_location("run_core_loop_snapshot", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load script module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class CoreLoopSnapshotScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.original_engine = _MODULE.engine
        _MODULE.engine = self.engine

        with Session(self.engine) as session:
            self.user_a = User(
                email="core-loop-script-a@example.com",
                full_name="Core Loop Script A",
                hashed_password="hashed",
            )
            self.user_b = User(
                email="core-loop-script-b@example.com",
                full_name="Core Loop Script B",
                hashed_password="hashed",
            )
            session.add(self.user_a)
            session.add(self.user_b)
            session.commit()
            session.refresh(self.user_a)
            session.refresh(self.user_b)
            self.user_a_id = self.user_a.id
            self.user_b_id = self.user_b.id

            now = utcnow()
            session.add_all(
                [
                    EventsLog(
                        user_id=self.user_a_id,
                        partner_user_id=self.user_b_id,
                        event_name="daily_sync_submitted",
                        event_id="evt-sync-a",
                        source="test",
                        ts=now,
                        dedupe_key="dedupe-sync-a",
                    ),
                    EventsLog(
                        user_id=self.user_a_id,
                        partner_user_id=self.user_b_id,
                        event_name="daily_card_revealed",
                        event_id="evt-reveal-a",
                        source="test",
                        ts=now,
                        dedupe_key="dedupe-reveal-a",
                    ),
                    EventsLog(
                        user_id=self.user_a_id,
                        partner_user_id=self.user_b_id,
                        event_name="card_answer_submitted",
                        event_id="evt-answer-a",
                        source="test",
                        ts=now,
                        dedupe_key="dedupe-answer-a",
                    ),
                    EventsLog(
                        user_id=self.user_a_id,
                        partner_user_id=self.user_b_id,
                        event_name="appreciation_sent",
                        event_id="evt-app-a",
                        source="test",
                        ts=now,
                        dedupe_key="dedupe-app-a",
                    ),
                    EventsLog(
                        user_id=self.user_a_id,
                        partner_user_id=self.user_b_id,
                        event_name="daily_loop_completed",
                        event_id="evt-loop-a",
                        source="server",
                        ts=now,
                        dedupe_key="dedupe-loop-a",
                    ),
                ]
            )
            session.commit()

    def tearDown(self) -> None:
        _MODULE.engine = self.original_engine
        self.engine.dispose()

    def test_main_writes_snapshot_and_latest_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "core-loop-snapshot.json"
            latest_path = Path(tmpdir) / "core-loop-snapshot-latest.json"
            exit_code = _MODULE.main(
                [
                    "--window-days",
                    "1",
                    "--output",
                    str(output_path),
                    "--latest-path",
                    str(latest_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertTrue(latest_path.exists())

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_kind"], "core-loop-snapshot")
            self.assertEqual(payload["metric"], "core_loop")
            self.assertEqual(payload["snapshot"]["counts"]["active_users_total"], 1)
            self.assertEqual(payload["evaluation"]["status"], "insufficient_data")

    def test_fail_on_degraded_returns_non_zero(self) -> None:
        with Session(self.engine) as session:
            session.add(
                EventsLog(
                    user_id=self.user_b_id,
                    partner_user_id=None,
                    event_name="daily_sync_submitted",
                    event_id="evt-sync-b",
                    source="test",
                    ts=utcnow(),
                    dedupe_key="dedupe-sync-b",
                )
            )
            session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "core-loop-snapshot.json"
            latest_path = Path(tmpdir) / "core-loop-snapshot-latest.json"
            exit_code = _MODULE.main(
                [
                    "--window-days",
                    "1",
                    "--min-active-users",
                    "1",
                    "--target-daily-loop-completion-rate",
                    "1.0",
                    "--target-dual-reveal-pair-rate",
                    "1.0",
                    "--fail-on-degraded",
                    "--output",
                    str(output_path),
                    "--latest-path",
                    str(latest_path),
                ]
            )
            self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
