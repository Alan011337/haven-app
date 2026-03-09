import json
import sys
import unittest
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.journals import router as journals_router  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.audit_event import AuditEvent  # noqa: E402
from app.models.gamification_score_event import GamificationScoreEvent  # noqa: E402
from app.models.user import User  # noqa: E402


class GamificationReplayProtectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(journals_router, prefix="/api/journals")

        self.current_user_id = None

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        def override_get_current_user() -> User:
            if self.current_user_id is None:
                raise RuntimeError("current_user_id is not set")
            with Session(self.engine) as session:
                user = session.get(User, self.current_user_id)
                if not user:
                    raise RuntimeError("user not found")
                return user

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

        with Session(self.engine) as session:
            user = User(
                email="score-a@example.com",
                full_name="Score A",
                hashed_password="hashed",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            self.user_id = user.id
        self.current_user_id = self.user_id

        self.analyze_patch = patch(
            "app.api.journals.analyze_journal",
            new=AsyncMock(
                return_value={
                    "mood_label": "happy",
                    "safety_tier": 0,
                    "parse_success": True,
                    "prompt_version": "test",
                }
            ),
        )
        self.analyze_patch.start()
        self.notify_patch = patch("app.api.journals.queue_partner_notification")
        self.notify_patch.start()

    def tearDown(self) -> None:
        self.notify_patch.stop()
        self.analyze_patch.stop()
        self.client.close()
        self.engine.dispose()

    def test_same_day_same_content_replay_does_not_gain_duplicate_score(self) -> None:
        first = self.client.post("/api/journals/", json={"content": "I feel calm and grateful"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["score_gained"], 10)
        self.assertEqual(first.json()["new_savings_score"], 10)

        second = self.client.post("/api/journals/", json={"content": "I feel calm and grateful"})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["score_gained"], 0)
        self.assertEqual(second.json()["new_savings_score"], 10)

        with Session(self.engine) as session:
            events = session.exec(select(GamificationScoreEvent)).all()
            self.assertEqual(len(events), 1)
            user = session.get(User, self.user_id)
            self.assertIsNotNone(user)
            assert user is not None
            self.assertEqual(user.savings_score, 10)

            audit_rows = session.exec(
                select(AuditEvent).where(AuditEvent.action == "JOURNAL_CREATE")
            ).all()
            self.assertEqual(len(audit_rows), 2)
            metadata = json.loads(audit_rows[-1].metadata_json or "{}")
            self.assertTrue(metadata.get("score_replay_blocked"))

    def test_normalized_content_whitespace_replay_is_blocked(self) -> None:
        first = self.client.post("/api/journals/", json={"content": "We had a kind talk tonight."})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["score_gained"], 10)

        second = self.client.post(
            "/api/journals/",
            json={"content": "  We   had   a   kind talk   tonight.  "},
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["score_gained"], 0)
        self.assertEqual(second.json()["new_savings_score"], 10)

    def test_different_content_still_scores(self) -> None:
        first = self.client.post("/api/journals/", json={"content": "I feel loved."})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["score_gained"], 10)

        second = self.client.post("/api/journals/", json={"content": "I feel excited about us."})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["score_gained"], 10)
        self.assertEqual(second.json()["new_savings_score"], 20)

        with Session(self.engine) as session:
            events = session.exec(select(GamificationScoreEvent)).all()
            self.assertEqual(len(events), 2)


if __name__ == "__main__":
    unittest.main()
