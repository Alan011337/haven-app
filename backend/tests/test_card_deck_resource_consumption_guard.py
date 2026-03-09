import sys
import unittest
from pathlib import Path
from typing import Generator
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import card_decks  # noqa: E402
from app.db.session import get_read_session, get_session  # noqa: E402
from app.models.user import User  # noqa: E402


class CardDeckResourceConsumptionGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(card_decks.router, prefix="/api/card-decks")

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
        app.dependency_overrides[get_read_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

        with Session(self.engine) as session:
            user = User(
                email="deck-resource@example.com",
                full_name="Deck Resource",
                hashed_password="hashed",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            self.current_user_id = user.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_history_rejects_limit_above_cap(self) -> None:
        response = self.client.get("/api/card-decks/history", params={"limit": 101})
        self.assertEqual(response.status_code, 422)
        self.assertIn("less than or equal to 100", str(response.json()))

    def test_history_rejects_too_wide_date_range(self) -> None:
        response = self.client.get(
            "/api/card-decks/history",
            params={"revealed_from": "2024-01-01", "revealed_to": "2025-12-31"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("查詢區間不可超過", response.json()["detail"])

    def test_history_summary_rejects_too_wide_date_range(self) -> None:
        response = self.client.get(
            "/api/card-decks/history/summary",
            params={"revealed_from": "2024-01-01", "revealed_to": "2025-12-31"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("查詢區間不可超過", response.json()["detail"])

    def test_history_summary_allows_valid_date_range(self) -> None:
        response = self.client.get(
            "/api/card-decks/history/summary",
            params={"revealed_from": "2025-01-01", "revealed_to": "2025-12-31"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_records"], 0)
        self.assertEqual(payload["this_month_records"], 0)

    def test_history_emits_observability_log(self) -> None:
        with patch("app.api.routers.card_decks.logger.info") as mock_info:
            response = self.client.get("/api/card-decks/history", params={"limit": 20, "offset": 0})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_info.call_count, 1)
        call_args = mock_info.call_args.args
        self.assertIn("deck_history_metrics", call_args[0])
        self.assertEqual(call_args[1], "history")
        self.assertEqual(call_args[2], self.current_user_id)
        self.assertIsNone(call_args[3])  # category
        self.assertIsNone(call_args[4])  # revealed_from
        self.assertIsNone(call_args[5])  # revealed_to
        self.assertEqual(call_args[6], 20)  # limit
        self.assertEqual(call_args[7], 0)  # offset
        self.assertEqual(call_args[8], 0)  # result_count
        self.assertIsNone(call_args[9])  # total_records
        self.assertIsInstance(call_args[10], int)  # duration_ms

    def test_history_summary_emits_observability_log(self) -> None:
        with patch("app.api.routers.card_decks.logger.info") as mock_info:
            response = self.client.get(
                "/api/card-decks/history/summary",
                params={"revealed_from": "2025-01-01", "revealed_to": "2025-12-31"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_info.call_count, 1)
        call_args = mock_info.call_args.args
        self.assertIn("deck_history_metrics", call_args[0])
        self.assertEqual(call_args[1], "history_summary")
        self.assertEqual(call_args[2], self.current_user_id)
        self.assertIsNone(call_args[3])  # category
        self.assertEqual(call_args[4], "2025-01-01")
        self.assertEqual(call_args[5], "2025-12-31")
        self.assertIsNone(call_args[6])  # limit
        self.assertIsNone(call_args[7])  # offset
        self.assertIsNone(call_args[8])  # result_count
        self.assertEqual(call_args[9], 0)  # total_records
        self.assertIsInstance(call_args[10], int)  # duration_ms


if __name__ == "__main__":
    unittest.main()
