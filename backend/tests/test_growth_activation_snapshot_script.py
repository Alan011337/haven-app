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

from app.core.config import settings  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.models.user import User  # noqa: E402

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_growth_activation_funnel_snapshot.py"
_SPEC = importlib.util.spec_from_file_location("run_growth_activation_funnel_snapshot", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load script module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class GrowthActivationSnapshotScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.original_engine = _MODULE.engine
        _MODULE.engine = self.engine

        self.original_feature_flags = settings.FEATURE_FLAGS_JSON
        self.original_kill_switches = settings.FEATURE_KILL_SWITCHES_JSON
        settings.FEATURE_FLAGS_JSON = '{"growth_activation_dashboard_enabled": true}'
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_growth_activation_dashboard": false}'

        with Session(self.engine) as session:
            now = utcnow()
            user_a = User(
                email="activation-script-a@example.com",
                full_name="Activation Script A",
                hashed_password="hashed",
                terms_accepted_at=now,
            )
            user_b = User(
                email="activation-script-b@example.com",
                full_name="Activation Script B",
                hashed_password="hashed",
                terms_accepted_at=now,
            )
            session.add(user_a)
            session.add(user_b)
            session.commit()

    def tearDown(self) -> None:
        _MODULE.engine = self.original_engine
        settings.FEATURE_FLAGS_JSON = self.original_feature_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_kill_switches
        self.engine.dispose()

    def test_main_writes_snapshot_and_latest_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "activation-funnel-snapshot.json"
            latest_path = Path(tmpdir) / "activation-funnel-snapshot-latest.json"
            exit_code = _MODULE.main(
                [
                    "--window-days",
                    "30",
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
            self.assertEqual(payload["artifact_kind"], "growth-activation-funnel-snapshot")
            self.assertEqual(payload["snapshot"]["status"], "ok")
            self.assertEqual(payload["snapshot"]["counts"]["signup_completed_users"], 2)

    def test_main_fail_on_degraded_returns_non_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "activation-funnel-snapshot.json"
            latest_path = Path(tmpdir) / "activation-funnel-snapshot-latest.json"
            exit_code = _MODULE.main(
                [
                    "--window-days",
                    "30",
                    "--min-signups",
                    "1",
                    "--target-bind-rate",
                    "0.8",
                    "--target-first-journal-rate",
                    "0.8",
                    "--target-first-deck-rate",
                    "0.8",
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
