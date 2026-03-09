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
from app.models.cuj_event import CujEvent  # noqa: E402
from app.models.user import User  # noqa: E402

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_growth_nsm_snapshot.py"
_SPEC = importlib.util.spec_from_file_location("run_growth_nsm_snapshot", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load script module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class GrowthNsmSnapshotScriptTests(unittest.TestCase):
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
                email="growth-script-a@example.com",
                full_name="Growth Script A",
                hashed_password="hashed",
            )
            self.user_b = User(
                email="growth-script-b@example.com",
                full_name="Growth Script B",
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
            session.add(
                CujEvent(
                    user_id=self.user_a_id,
                    partner_user_id=self.user_b_id,
                    event_name="RITUAL_RESPOND",
                    event_id="evt-script-a",
                    source="test",
                    mode="DAILY_RITUAL",
                    session_id=None,
                    request_id="req-script",
                    dedupe_key="dedupe-evt-script-a",
                    metadata_json=None,
                    occurred_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                CujEvent(
                    user_id=self.user_b_id,
                    partner_user_id=self.user_a_id,
                    event_name="RITUAL_UNLOCK",
                    event_id="evt-script-b",
                    source="test",
                    mode="DAILY_RITUAL",
                    session_id=None,
                    request_id="req-script",
                    dedupe_key="dedupe-evt-script-b",
                    metadata_json=None,
                    occurred_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()

    def tearDown(self) -> None:
        _MODULE.engine = self.original_engine
        self.engine.dispose()

    def test_main_writes_snapshot_and_latest_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wrm-snapshot.json"
            latest_path = Path(tmpdir) / "wrm-snapshot-latest.json"
            exit_code = _MODULE.main(
                [
                    "--window-days",
                    "7",
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
            self.assertEqual(payload["artifact_kind"], "growth-nsm-snapshot")
            self.assertEqual(payload["metric"], "WRM")
            self.assertEqual(payload["snapshot"]["counts"]["wrm_pairs_total"], 1)
            self.assertEqual(payload["evaluation"]["status"], "insufficient_data")

    def test_main_fail_on_degraded_returns_non_zero(self) -> None:
        with Session(self.engine) as session:
            user_c = User(
                email="growth-script-c@example.com",
                full_name="Growth Script C",
                hashed_password="hashed",
            )
            session.add(user_c)
            session.commit()
            session.refresh(user_c)
            now = utcnow()
            session.add(
                CujEvent(
                    user_id=self.user_a_id,
                    partner_user_id=user_c.id,
                    event_name="JOURNAL_SUBMIT",
                    event_id="evt-script-one-sided",
                    source="test",
                    mode="JOURNAL",
                    session_id=None,
                    request_id="req-script",
                    dedupe_key="dedupe-evt-script-one-sided",
                    metadata_json=None,
                    occurred_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wrm-snapshot.json"
            latest_path = Path(tmpdir) / "wrm-snapshot-latest.json"
            exit_code = _MODULE.main(
                [
                    "--window-days",
                    "7",
                    "--min-events",
                    "1",
                    "--min-pairs",
                    "1",
                    "--target-wrm-active-pair-rate",
                    "0.9",
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
