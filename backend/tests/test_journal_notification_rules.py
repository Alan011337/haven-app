import sys
import unittest
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.journals import router as journals_router  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.rate_limit import reset_rate_limit_state_for_tests  # noqa: E402


class JournalNotificationRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_rate_limit_state_for_tests()
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
            self.user_a = User(email="a@example.com", full_name="Alpha", hashed_password="hashed")
            self.user_b = User(email="b@example.com", full_name="Beta", hashed_password="hashed")
            self.user_c = User(email="c@example.com", full_name="Solo", hashed_password="hashed")
            self.user_a.partner_id = self.user_b.id
            self.user_b.partner_id = self.user_a.id
            session.add(self.user_a)
            session.add(self.user_b)
            session.add(self.user_c)
            session.commit()
            session.refresh(self.user_a)
            session.refresh(self.user_b)
            session.refresh(self.user_c)

        self.current_user_id = self.user_a.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()
        reset_rate_limit_state_for_tests()

    def test_create_journal_queues_scoped_notification(self) -> None:
        with patch("app.api.journals.analyze_journal", AsyncMock(return_value={})):
            with patch("app.api.journals.queue_partner_notification") as mock_queue:
                response = self.client.post(
                    "/api/journals/",
                    json={"content": "今天有點累，但我在努力。"},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        journal_id = payload["id"]

        self.assertEqual(mock_queue.call_count, 1)
        kwargs = mock_queue.call_args.kwargs
        self.assertEqual(kwargs["action_type"], "journal")
        self.assertEqual(str(kwargs["source_session_id"]), journal_id)
        self.assertTrue(str(kwargs["dedupe_key"]).startswith(f"journal:{journal_id}:"))

    def test_create_journal_solo_mode_does_not_queue_partner_notification(self) -> None:
        """LIFECYCLE-01: Solo user (partner_id=None) must not trigger partner notification."""
        self.current_user_id = self.user_c.id
        with patch("app.api.journals.analyze_journal", AsyncMock(return_value={})):
            with patch("app.api.journals.queue_partner_notification") as mock_queue:
                response = self.client.post(
                    "/api/journals/",
                    json={"content": "今天有點累，但我在努力。"},
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_queue.call_count, 0)

    def test_create_journal_rejects_blank_content(self) -> None:
        with patch("app.api.journals.queue_partner_notification") as mock_queue:
            response = self.client.post("/api/journals/", json={"content": "   "})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(mock_queue.call_count, 0)

    def test_create_journal_rejects_over_limit_content(self) -> None:
        too_long_content = "a" * 4001
        with patch("app.api.journals.queue_partner_notification") as mock_queue:
            response = self.client.post("/api/journals/", json={"content": too_long_content})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(mock_queue.call_count, 0)

    def test_create_journal_trims_content_before_persist(self) -> None:
        with patch("app.api.journals.analyze_journal", AsyncMock(return_value={})):
            response = self.client.post("/api/journals/", json={"content": "  保留這句話  "})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["content"], "保留這句話")

    def test_create_journal_rate_limited(self) -> None:
        with patch("app.api.journals.settings.JOURNAL_RATE_LIMIT_COUNT", 1), patch(
            "app.api.journals.settings.JOURNAL_RATE_LIMIT_WINDOW_SECONDS", 3600
        ), patch("app.api.journals.analyze_journal", AsyncMock(return_value={})):
            first = self.client.post("/api/journals/", json={"content": "第一篇"})
            second = self.client.post("/api/journals/", json={"content": "第二篇"})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("日記提交過於頻繁", second.json()["detail"])
        self.assertIn("Retry-After", second.headers)
        self.assertEqual(second.headers.get("X-RateLimit-Scope"), "user")
        self.assertEqual(second.headers.get("X-RateLimit-Action"), "journal_create")
        self.assertGreaterEqual(int(second.headers["Retry-After"]), 1)

    def test_create_journal_rate_limited_by_ip_dimension(self) -> None:
        with patch("app.api.journals.settings.JOURNAL_RATE_LIMIT_COUNT", 100), patch(
            "app.api.journals.settings.JOURNAL_RATE_LIMIT_WINDOW_SECONDS", 3600
        ), patch("app.api.journals.settings.JOURNAL_RATE_LIMIT_IP_COUNT", 1), patch(
            "app.api.journals.settings.JOURNAL_RATE_LIMIT_DEVICE_COUNT", 100
        ), patch("app.api.journals.settings.JOURNAL_RATE_LIMIT_PARTNER_PAIR_COUNT", 100), patch(
            "app.api.journals.analyze_journal", AsyncMock(return_value={})
        ):
            first = self.client.post(
                "/api/journals/",
                json={"content": "ip first"},
                headers={"x-forwarded-for": "198.51.100.88"},
            )
            self.current_user_id = self.user_b.id
            second = self.client.post(
                "/api/journals/",
                json={"content": "ip second"},
                headers={"x-forwarded-for": "198.51.100.88"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("日記提交過於頻繁", second.json()["detail"])
        self.assertEqual(second.headers.get("X-RateLimit-Scope"), "ip")
        self.assertEqual(second.headers.get("X-RateLimit-Action"), "journal_create")

    def test_create_journal_rate_limited_by_device_dimension(self) -> None:
        with patch("app.api.journals.settings.JOURNAL_RATE_LIMIT_COUNT", 100), patch(
            "app.api.journals.settings.JOURNAL_RATE_LIMIT_WINDOW_SECONDS", 3600
        ), patch("app.api.journals.settings.JOURNAL_RATE_LIMIT_IP_COUNT", 100), patch(
            "app.api.journals.settings.JOURNAL_RATE_LIMIT_DEVICE_COUNT", 1
        ), patch("app.api.journals.settings.JOURNAL_RATE_LIMIT_PARTNER_PAIR_COUNT", 100), patch(
            "app.api.journals.settings.RATE_LIMIT_DEVICE_HEADER", "x-device-id"
        ), patch("app.api.journals.analyze_journal", AsyncMock(return_value={})):
            first = self.client.post(
                "/api/journals/",
                json={"content": "device first"},
                headers={"x-forwarded-for": "198.51.100.89", "x-device-id": "shared-device-a"},
            )
            self.current_user_id = self.user_b.id
            second = self.client.post(
                "/api/journals/",
                json={"content": "device second"},
                headers={"x-forwarded-for": "198.51.100.90", "x-device-id": "shared-device-a"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("日記提交過於頻繁", second.json()["detail"])
        self.assertEqual(second.headers.get("X-RateLimit-Scope"), "device")
        self.assertEqual(second.headers.get("X-RateLimit-Action"), "journal_create")

    def test_create_journal_rate_limited_by_partner_pair_dimension(self) -> None:
        with patch("app.api.journals.settings.JOURNAL_RATE_LIMIT_COUNT", 100), patch(
            "app.api.journals.settings.JOURNAL_RATE_LIMIT_WINDOW_SECONDS", 3600
        ), patch("app.api.journals.settings.JOURNAL_RATE_LIMIT_IP_COUNT", 100), patch(
            "app.api.journals.settings.JOURNAL_RATE_LIMIT_DEVICE_COUNT", 100
        ), patch("app.api.journals.settings.JOURNAL_RATE_LIMIT_PARTNER_PAIR_COUNT", 1), patch(
            "app.api.journals.analyze_journal", AsyncMock(return_value={})
        ):
            first = self.client.post(
                "/api/journals/",
                json={"content": "pair first"},
                headers={"x-forwarded-for": "198.51.100.91", "x-device-id": "pair-device-a"},
            )
            self.current_user_id = self.user_b.id
            second = self.client.post(
                "/api/journals/",
                json={"content": "pair second"},
                headers={"x-forwarded-for": "198.51.100.92", "x-device-id": "pair-device-b"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("日記提交過於頻繁", second.json()["detail"])
        self.assertEqual(second.headers.get("X-RateLimit-Scope"), "partner_pair")
        self.assertEqual(second.headers.get("X-RateLimit-Action"), "journal_create")

    def test_create_multiple_journals_use_distinct_dedupe_keys(self) -> None:
        with patch("app.api.journals.analyze_journal", AsyncMock(return_value={})):
            with patch("app.api.journals.queue_partner_notification") as mock_queue:
                first = self.client.post("/api/journals/", json={"content": "第一篇日記"})
                second = self.client.post("/api/journals/", json={"content": "第二篇日記"})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        first_journal_id = first.json()["id"]
        second_journal_id = second.json()["id"]

        self.assertEqual(mock_queue.call_count, 2)
        first_key = str(mock_queue.call_args_list[0].kwargs["dedupe_key"])
        second_key = str(mock_queue.call_args_list[1].kwargs["dedupe_key"])

        self.assertNotEqual(first_key, second_key)
        self.assertTrue(first_key.startswith(f"journal:{first_journal_id}:"))
        self.assertTrue(second_key.startswith(f"journal:{second_journal_id}:"))


if __name__ == "__main__":
    unittest.main()
