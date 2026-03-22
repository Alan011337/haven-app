import sys
import unittest
import uuid
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
from app.db.session import get_read_session, get_session  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.rate_limit import reset_rate_limit_state_for_tests  # noqa: E402


class JournalCreateUpdateContractRegressionTests(unittest.TestCase):
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
        app.dependency_overrides[get_read_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user

        self.client = TestClient(app)

        with Session(self.engine) as session:
            self.user_a = User(email="contract-a@example.com", full_name="Alpha", hashed_password="hashed")
            self.user_b = User(email="contract-b@example.com", full_name="Beta", hashed_password="hashed")
            session.add(self.user_a)
            session.add(self.user_b)
            session.commit()
            session.refresh(self.user_a)
            session.refresh(self.user_b)

            self.user_a.partner_id = self.user_b.id
            self.user_b.partner_id = self.user_a.id
            session.add(self.user_a)
            session.add(self.user_b)
            session.commit()
            self.user_a_id = self.user_a.id
            self.user_b_id = self.user_b.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()
        reset_rate_limit_state_for_tests()

    def test_create_journal_accepts_flat_v3_payload(self) -> None:
        with patch("app.api.journals.is_async_journal_analysis_enabled", return_value=False), patch(
            "app.api.journals.analyze_journal",
            new=AsyncMock(return_value={"parse_success": True, "mood_label": "calm"}),
        ), patch(
            "app.api.journals.translate_journal_for_partner",
            new=AsyncMock(return_value="整理後的伴侶譯文。"),
        ), patch("app.api.journals.queue_partner_notification"):
            response = self.client.post(
                "/api/journals/",
                json={
                    "title": "新的頁面",
                    "content": "# 第一段\n\n這是一篇可保存的內容。",
                    "visibility": "PARTNER_TRANSLATED_ONLY",
                    "content_format": "markdown",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["title"], "新的頁面")
        self.assertEqual(payload["content"], "# 第一段\n\n這是一篇可保存的內容。")
        self.assertEqual(payload["visibility"], "PARTNER_TRANSLATED_ONLY")
        self.assertEqual(payload["content_format"], "markdown")
        self.assertFalse(payload["is_draft"])
        self.assertEqual(payload["partner_translation_status"], "READY")
        with Session(self.engine) as session:
            journal = session.get(Journal, uuid.UUID(payload["id"]))
            assert journal is not None
            self.assertFalse(journal.is_draft)
            self.assertEqual(journal.partner_translated_content, "整理後的伴侶譯文。")

    def test_create_draft_accepts_blank_content_and_skips_translation(self) -> None:
        with patch("app.api.journals.translate_journal_for_partner", new=AsyncMock()) as translate_mock, patch(
            "app.api.journals.queue_partner_notification"
        ) as notify_mock:
            response = self.client.post(
                "/api/journals/",
                json={
                    "title": "空白草稿",
                    "content": "",
                    "is_draft": True,
                    "visibility": "PARTNER_TRANSLATED_ONLY",
                    "content_format": "markdown",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["title"], "空白草稿")
        self.assertEqual(payload["content"], "")
        self.assertTrue(payload["is_draft"])
        self.assertEqual(payload["partner_translation_status"], "NOT_REQUESTED")
        translate_mock.assert_not_awaited()
        notify_mock.assert_not_called()
        with Session(self.engine) as session:
            journal = session.get(Journal, uuid.UUID(payload["id"]))
            assert journal is not None
            self.assertTrue(journal.is_draft)
            self.assertIsNone(journal.partner_translated_content)

    def test_create_draft_with_idempotency_key_replays_json_safe_payload(self) -> None:
        headers = {"Idempotency-Key": "journal-draft-idem-1234"}

        with patch("app.api.journals.translate_journal_for_partner", new=AsyncMock()) as translate_mock, patch(
            "app.api.journals.queue_partner_notification"
        ) as notify_mock:
            first = self.client.post(
                "/api/journals/",
                headers=headers,
                json={
                    "title": "可重放草稿",
                    "content": "",
                    "is_draft": True,
                    "visibility": "PARTNER_TRANSLATED_ONLY",
                    "content_format": "markdown",
                },
            )
            second = self.client.post(
                "/api/journals/",
                headers=headers,
                json={
                    "title": "可重放草稿",
                    "content": "",
                    "is_draft": True,
                    "visibility": "PARTNER_TRANSLATED_ONLY",
                    "content_format": "markdown",
                },
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_payload = first.json()
        second_payload = second.json()
        self.assertEqual(second_payload["id"], first_payload["id"])
        self.assertTrue(second_payload["is_draft"])
        self.assertEqual(second_payload["content"], "")
        translate_mock.assert_not_awaited()
        notify_mock.assert_not_called()

    def test_update_journal_accepts_flat_v3_payload(self) -> None:
        with Session(self.engine) as session:
            journal = Journal(
                title="原始標題",
                content="原始內容",
                user_id=self.user_a_id,
                visibility="PRIVATE",
                content_format="markdown",
                partner_translation_status="NOT_REQUESTED",
            )
            session.add(journal)
            session.commit()
            session.refresh(journal)
            journal_id = journal.id

        with patch(
            "app.api.journals.analyze_journal",
            new=AsyncMock(return_value={"parse_success": True, "mood_label": "steady"}),
        ), patch(
            "app.api.journals.translate_journal_for_partner",
            new=AsyncMock(return_value="更新後的伴侶譯文。"),
        ):
            response = self.client.patch(
                f"/api/journals/{journal_id}",
                json={
                    "title": "更新後標題",
                    "content": "# 更新後內容\n\n第二段也在。",
                    "visibility": "PARTNER_TRANSLATED_ONLY",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["title"], "更新後標題")
        self.assertEqual(payload["content"], "# 更新後內容\n\n第二段也在。")
        self.assertEqual(payload["visibility"], "PARTNER_TRANSLATED_ONLY")
        self.assertEqual(payload["content_format"], "markdown")
        self.assertFalse(payload["is_draft"])
        self.assertEqual(payload["partner_translation_status"], "READY")
        with Session(self.engine) as session:
            journal = session.get(Journal, journal_id)
            assert journal is not None
            self.assertFalse(journal.is_draft)
            self.assertEqual(journal.partner_translated_content, "更新後的伴侶譯文。")

    def test_update_draft_can_finalize_into_substantive_journal(self) -> None:
        with Session(self.engine) as session:
            journal = Journal(
                title="暫存草稿",
                content="",
                is_draft=True,
                user_id=self.user_a_id,
                visibility="PARTNER_TRANSLATED_ONLY",
                content_format="markdown",
                partner_translation_status="NOT_REQUESTED",
            )
            session.add(journal)
            session.commit()
            session.refresh(journal)
            journal_id = journal.id

        with patch(
            "app.api.journals.analyze_journal",
            new=AsyncMock(return_value={"parse_success": True, "mood_label": "steady"}),
        ), patch(
            "app.api.journals.translate_journal_for_partner",
            new=AsyncMock(return_value="整理好的伴侶譯文。"),
        ):
            response = self.client.patch(
                f"/api/journals/{journal_id}",
                json={
                    "title": "正式的一頁",
                    "content": "先從一張圖片開始，接著把感受寫出來。",
                    "is_draft": False,
                    "visibility": "PARTNER_TRANSLATED_ONLY",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["is_draft"])
        self.assertEqual(payload["partner_translation_status"], "READY")
        with Session(self.engine) as session:
            journal = session.get(Journal, journal_id)
            assert journal is not None
            self.assertFalse(journal.is_draft)
            self.assertEqual(journal.partner_translated_content, "整理好的伴侶譯文。")

    def test_create_journal_blank_content_returns_explicit_field_validation_error(self) -> None:
        response = self.client.post(
            "/api/journals/",
            json={
                "title": "空白內容",
                "content": "   ",
                "visibility": "PARTNER_TRANSLATED_ONLY",
                "content_format": "markdown",
            },
        )

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertEqual(payload["detail"][0]["loc"], ["body", "content"])
        self.assertEqual(payload["detail"][0]["msg"], "Value error, content must not be blank")

    def test_partner_feed_excludes_drafts_even_when_visibility_is_shared(self) -> None:
        with Session(self.engine) as session:
            journal = Journal(
                title="草稿中的共享頁面",
                content="",
                is_draft=True,
                user_id=self.user_a_id,
                visibility="PARTNER_TRANSLATED_ONLY",
                content_format="markdown",
                partner_translation_status="NOT_REQUESTED",
            )
            session.add(journal)
            session.commit()

        self.current_user_id = self.user_b_id
        response = self.client.get("/api/journals/partner")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


if __name__ == "__main__":
    unittest.main()
