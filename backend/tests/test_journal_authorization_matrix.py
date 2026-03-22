# AUTHZ_MATRIX: GET /api/journals/{journal_id}
# AUTHZ_MATRIX: POST /api/journals/
# AUTHZ_MATRIX: PATCH /api/journals/{journal_id}
# AUTHZ_MATRIX: POST /api/journals/{journal_id}/attachments
# AUTHZ_MATRIX: DELETE /api/journals/{journal_id}/attachments/{attachment_id}
# AUTHZ_MATRIX: DELETE /api/journals/{journal_id}
# AUTHZ_DENY_MATRIX: GET /api/journals/{journal_id}
# AUTHZ_DENY_MATRIX: PATCH /api/journals/{journal_id}
# AUTHZ_DENY_MATRIX: POST /api/journals/{journal_id}/attachments
# AUTHZ_DENY_MATRIX: DELETE /api/journals/{journal_id}/attachments/{attachment_id}
# AUTHZ_DENY_MATRIX: DELETE /api/journals/{journal_id}

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
from app.db.session import get_read_session, get_session  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.journal_attachment import JournalAttachment  # noqa: E402
from app.models.user import User  # noqa: E402


class JournalAuthorizationMatrixTests(unittest.TestCase):
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
        app.dependency_overrides[get_read_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user

        self.client = TestClient(app)

        with Session(self.engine) as session:
            self.user_a = User(email="a@example.com", full_name="A", hashed_password="hashed")
            self.user_b = User(email="b@example.com", full_name="B", hashed_password="hashed")
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

            self.owner_journal = Journal(
                title="Owner Draft",
                content="# 原始內容\n\n只有作者可以改。",
                user_id=self.user_a.id,
                visibility="PARTNER_TRANSLATED_ONLY",
                content_format="markdown",
                partner_translation_status="READY",
                partner_translated_content="這是一封已整理好的譯文。",
            )
            self.shared_original_journal = Journal(
                title="Shared Original",
                content="# 直接分享的原文\n\n- 真實原文",
                user_id=self.user_a.id,
                visibility="PARTNER_ORIGINAL",
                content_format="markdown",
                partner_translation_status="NOT_REQUESTED",
            )
            self.private_journal = Journal(
                title="Private Journal",
                content="這篇不應該出現在伴侶閱讀室。",
                user_id=self.user_a.id,
                visibility="PRIVATE",
                content_format="markdown",
                partner_translation_status="NOT_REQUESTED",
            )
            session.add(self.owner_journal)
            session.add(self.shared_original_journal)
            session.add(self.private_journal)
            session.commit()
            session.refresh(self.owner_journal)
            session.refresh(self.shared_original_journal)
            session.refresh(self.private_journal)

            self.owner_attachment = JournalAttachment(
                journal_id=self.owner_journal.id,
                user_id=self.user_a.id,
                file_name="owner-photo.jpg",
                mime_type="image/jpeg",
                size_bytes=1024,
                storage_path="journals/owner-photo.jpg",
            )
            self.shared_original_attachment = JournalAttachment(
                journal_id=self.shared_original_journal.id,
                user_id=self.user_a.id,
                file_name="shared-photo.jpg",
                mime_type="image/jpeg",
                size_bytes=2048,
                storage_path="journals/shared-photo.jpg",
            )
            session.add(self.owner_attachment)
            session.add(self.shared_original_attachment)
            session.commit()
            session.refresh(self.owner_attachment)
            session.refresh(self.shared_original_attachment)

            self.user_a_id = self.user_a.id
            self.user_b_id = self.user_b.id
            self.journal_id = self.owner_journal.id
            self.owner_attachment_id = self.owner_attachment.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_read_journal_detail_allows_owner(self) -> None:
        with patch("app.api.journals.journal_storage_enabled", return_value=True), patch(
            "app.api.journals.create_signed_journal_attachment_url",
            new=AsyncMock(return_value="https://example.com/owner-photo.jpg"),
        ):
            response = self.client.get(f"/api/journals/{self.journal_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], str(self.journal_id))
        self.assertEqual(payload["title"], "Owner Draft")
        self.assertEqual(payload["visibility"], "PARTNER_TRANSLATED_ONLY")
        self.assertEqual(len(payload["attachments"]), 1)
        self.assertEqual(payload["attachments"][0]["url"], "https://example.com/owner-photo.jpg")

    def test_read_journal_detail_rejects_non_owner(self) -> None:
        self.current_user_id = self.user_b_id
        response = self.client.get(f"/api/journals/{self.journal_id}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "你沒有權限查看這篇日記")

    def test_patch_journal_allows_owner(self) -> None:
        with patch(
            "app.api.journals.analyze_journal",
            new=AsyncMock(return_value={"mood_label": "calm", "parse_success": True}),
        ), patch(
            "app.api.journals.translate_journal_for_partner",
            new=AsyncMock(return_value="整理後的新版譯文。"),
        ), patch(
            "app.api.journals.create_signed_journal_attachment_url",
            new=AsyncMock(return_value="https://example.com/owner-photo.jpg"),
        ):
            response = self.client.patch(
                f"/api/journals/{self.journal_id}",
                json={
                    "title": "Updated Title",
                    "content": "# 更新後內容\n\n現在這一頁已被改寫。",
                    "visibility": "PARTNER_TRANSLATED_ONLY",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["title"], "Updated Title")
        self.assertEqual(payload["content"], "# 更新後內容\n\n現在這一頁已被改寫。")
        self.assertEqual(payload["partner_translation_status"], "READY")

    def test_patch_journal_rejects_non_owner(self) -> None:
        self.current_user_id = self.user_b_id
        response = self.client.patch(
            f"/api/journals/{self.journal_id}",
            json={"content": "不應成功"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "你沒有權限查看這篇日記")

    def test_upload_attachment_allows_owner(self) -> None:
        with patch("app.api.journals.journal_storage_enabled", return_value=True), patch(
            "app.api.journals.upload_journal_attachment_bytes",
            new=AsyncMock(return_value="journals/uploaded-photo.jpg"),
        ), patch(
            "app.api.journals.create_signed_journal_attachment_url",
            new=AsyncMock(return_value="https://example.com/uploaded-photo.jpg"),
        ):
            response = self.client.post(
                f"/api/journals/{self.journal_id}/attachments",
                files={"file": ("uploaded-photo.jpg", b"abc123", "image/jpeg")},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["file_name"], "uploaded-photo.jpg")
        self.assertEqual(payload["url"], "https://example.com/uploaded-photo.jpg")

        with Session(self.engine) as session:
            attachments = session.exec(
                select(JournalAttachment).where(JournalAttachment.journal_id == self.journal_id)
            ).all()
            self.assertEqual(len(attachments), 2)

    def test_upload_attachment_rejects_non_owner(self) -> None:
        self.current_user_id = self.user_b_id
        with patch("app.api.journals.journal_storage_enabled", return_value=True):
            response = self.client.post(
                f"/api/journals/{self.journal_id}/attachments",
                files={"file": ("uploaded-photo.jpg", b"abc123", "image/jpeg")},
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "你沒有權限查看這篇日記")

    def test_delete_attachment_allows_owner(self) -> None:
        with patch(
            "app.api.journals.delete_journal_attachment_object",
            new=AsyncMock(return_value=None),
        ):
            response = self.client.delete(
                f"/api/journals/{self.journal_id}/attachments/{self.owner_attachment_id}"
            )

        self.assertEqual(response.status_code, 204)
        with Session(self.engine) as session:
            deleted = session.get(JournalAttachment, self.owner_attachment_id)
            self.assertIsNotNone(deleted)
            assert deleted is not None
            self.assertIsNotNone(deleted.deleted_at)

    def test_delete_attachment_rejects_non_owner(self) -> None:
        self.current_user_id = self.user_b_id
        response = self.client.delete(
            f"/api/journals/{self.journal_id}/attachments/{self.owner_attachment_id}"
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "你沒有權限查看這篇日記")

    def test_delete_journal_allows_owner(self) -> None:
        response = self.client.delete(f"/api/journals/{self.journal_id}")
        self.assertEqual(response.status_code, 204)

        with Session(self.engine) as session:
            deleted = session.get(Journal, self.journal_id)
            self.assertIsNotNone(deleted)
            assert deleted is not None
            self.assertIsNotNone(deleted.deleted_at)

    def test_delete_journal_rejects_non_owner(self) -> None:
        self.current_user_id = self.user_b_id
        response = self.client.delete(f"/api/journals/{self.journal_id}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "你沒有權限刪除這篇日記")

    def test_create_journal_rejects_overposted_sensitive_fields(self) -> None:
        response = self.client.post(
            "/api/journals/",
            json={
                "content": "this should fail",
                "user_id": str(self.user_b_id),
                "safety_tier": 3,
            },
        )

        self.assertEqual(response.status_code, 422)
        serialized = str(response.json())
        self.assertIn("user_id", serialized)
        self.assertIn("safety_tier", serialized)

        with Session(self.engine) as session:
            journals = session.exec(select(Journal)).all()
            self.assertEqual(len(journals), 3)

    def test_partner_feed_respects_visibility_and_translation_no_leak(self) -> None:
        self.current_user_id = self.user_b_id
        with patch("app.api.journals.journal_storage_enabled", return_value=True), patch(
            "app.api.journals.create_signed_journal_attachment_url",
            new=AsyncMock(return_value="https://example.com/shared-photo.jpg"),
        ):
            response = self.client.get("/api/journals/partner")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        titles = {item["title"] for item in payload}
        self.assertIn("Owner Draft", titles)
        self.assertIn("Shared Original", titles)
        self.assertNotIn("Private Journal", titles)

        translated_item = next(item for item in payload if item["title"] == "Owner Draft")
        self.assertEqual(translated_item["visibility"], "PARTNER_TRANSLATED_ONLY")
        self.assertEqual(translated_item["content"], "")
        self.assertEqual(translated_item["partner_translated_content"], "這是一封已整理好的譯文。")
        self.assertNotIn("只有作者可以改。", str(translated_item))

        original_item = next(item for item in payload if item["title"] == "Shared Original")
        self.assertEqual(original_item["visibility"], "PARTNER_ORIGINAL")
        self.assertIn("直接分享的原文", original_item["content"])
        self.assertEqual(original_item["partner_translated_content"], None)
        self.assertEqual(len(original_item["attachments"]), 1)
        self.assertEqual(
            original_item["attachments"][0]["url"],
            "https://example.com/shared-photo.jpg",
        )


if __name__ == "__main__":
    unittest.main()
