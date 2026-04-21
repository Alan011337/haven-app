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
from app.db.session import get_read_session, get_session  # noqa: E402
from app.models.analysis import Analysis  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.journal_attachment import JournalAttachment  # noqa: E402
from app.models.user import User  # noqa: E402


class JournalSharingVisibilityApiTests(unittest.TestCase):
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
            alice = User(email="journal-share-a@example.com", full_name="Alice", hashed_password="hashed")
            bob = User(email="journal-share-b@example.com", full_name="Bob", hashed_password="hashed")
            stranger = User(
                email="journal-share-stranger@example.com",
                full_name="Stranger",
                hashed_password="hashed",
            )
            session.add(alice)
            session.add(bob)
            session.add(stranger)
            session.commit()
            session.refresh(alice)
            session.refresh(bob)
            session.refresh(stranger)

            alice.partner_id = bob.id
            bob.partner_id = alice.id
            session.add(alice)
            session.add(bob)
            session.commit()

            ready_translated = Journal(
                title="Ready translated-only",
                content="RAW SECRET LINE",
                user_id=alice.id,
                visibility="PARTNER_TRANSLATED_ONLY",
                content_format="markdown",
                partner_translation_status="READY",
                partner_translated_content="TRANSLATED PARTNER MARKER",
            )
            pending_translated = Journal(
                title="Pending translated-only",
                content="PENDING RAW SECRET",
                user_id=alice.id,
                visibility="PARTNER_TRANSLATED_ONLY",
                content_format="markdown",
                partner_translation_status="PENDING",
                partner_translated_content=None,
            )
            failed_with_stale_translation = Journal(
                title="Failed translated-only",
                content="FAILED RAW SECRET",
                user_id=alice.id,
                visibility="PARTNER_TRANSLATED_ONLY",
                content_format="markdown",
                partner_translation_status="FAILED",
                partner_translated_content="STALE TRANSLATION",
            )
            ready_blank_translation = Journal(
                title="Blank translated-only",
                content="BLANK RAW SECRET",
                user_id=alice.id,
                visibility="PARTNER_TRANSLATED_ONLY",
                content_format="markdown",
                partner_translation_status="READY",
                partner_translated_content="   ",
            )
            original = Journal(
                title="Original share",
                content="ORIGINAL PARTNER MARKER",
                user_id=alice.id,
                visibility="PARTNER_ORIGINAL",
                content_format="markdown",
                partner_translation_status="NOT_REQUESTED",
            )
            private = Journal(
                title="Private journal",
                content="PRIVATE RAW SECRET",
                user_id=alice.id,
                visibility="PRIVATE",
                content_format="markdown",
                partner_translation_status="NOT_REQUESTED",
            )
            session.add(ready_translated)
            session.add(pending_translated)
            session.add(failed_with_stale_translation)
            session.add(ready_blank_translation)
            session.add(original)
            session.add(private)
            session.commit()
            for journal in (
                ready_translated,
                pending_translated,
                failed_with_stale_translation,
                ready_blank_translation,
                original,
                private,
            ):
                session.refresh(journal)

            session.add(
                Analysis(
                    journal_id=ready_translated.id,
                    mood_label="vulnerable",
                    emotional_needs="NEEDS SHOULD NOT LEAK",
                    action_for_partner="ACTION SHOULD NOT LEAK",
                    advice_for_partner="ADVICE SHOULD NOT LEAK",
                    card_recommendation="SAFE_ZONE",
                    parse_success=True,
                )
            )
            session.add(
                Analysis(
                    journal_id=original.id,
                    mood_label="steady",
                    emotional_needs="Original needs context",
                    action_for_partner="Original action",
                    advice_for_partner="Original advice",
                    card_recommendation="SAFE_ZONE",
                    parse_success=True,
                )
            )
            session.add(
                JournalAttachment(
                    journal_id=ready_translated.id,
                    user_id=alice.id,
                    file_name="translated-secret-photo.jpg",
                    mime_type="image/jpeg",
                    size_bytes=1024,
                    storage_path="journals/translated-secret-photo.jpg",
                )
            )
            session.add(
                JournalAttachment(
                    journal_id=original.id,
                    user_id=alice.id,
                    file_name="shared-photo.jpg",
                    mime_type="image/jpeg",
                    size_bytes=2048,
                    storage_path="journals/shared-photo.jpg",
                )
            )
            session.commit()

            self.alice_id = alice.id
            self.bob_id = bob.id
            self.stranger_id = stranger.id
            self.ready_translated_id = ready_translated.id

        self.current_user_id = self.alice_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_owner_read_keeps_partner_translation_content_suppressed(self) -> None:
        with patch("app.api.journals.journal_storage_enabled", return_value=True), patch(
            "app.api.journals.create_signed_journal_attachment_url",
            new=AsyncMock(return_value="https://example.com/translated-secret-photo.jpg"),
        ):
            response = self.client.get(f"/api/journals/{self.ready_translated_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["title"], "Ready translated-only")
        self.assertEqual(payload["content"], "RAW SECRET LINE")
        self.assertEqual(payload["visibility"], "PARTNER_TRANSLATED_ONLY")
        self.assertEqual(payload["partner_translation_status"], "READY")
        self.assertNotIn("partner_translated_content", payload)
        self.assertEqual(len(payload["attachments"]), 1)
        self.assertEqual(payload["attachments"][0]["file_name"], "translated-secret-photo.jpg")

    def test_partner_feed_only_returns_ready_translated_content_without_original_leakage(self) -> None:
        self.current_user_id = self.bob_id

        with patch("app.api.journals.journal_storage_enabled", return_value=True), patch(
            "app.api.journals.create_signed_journal_attachment_url",
            new=AsyncMock(return_value="https://example.com/shared-photo.jpg"),
        ):
            response = self.client.get("/api/journals/partner")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        titles = {item["title"] for item in payload}
        self.assertIn("Ready translated-only", titles)
        self.assertIn("Original share", titles)
        self.assertNotIn("Pending translated-only", titles)
        self.assertNotIn("Failed translated-only", titles)
        self.assertNotIn("Blank translated-only", titles)
        self.assertNotIn("Private journal", titles)

        translated_item = next(item for item in payload if item["title"] == "Ready translated-only")
        self.assertEqual(translated_item["visibility"], "PARTNER_TRANSLATED_ONLY")
        self.assertEqual(translated_item["content"], "")
        self.assertEqual(translated_item["partner_translation_status"], "READY")
        self.assertEqual(translated_item["partner_translated_content"], "TRANSLATED PARTNER MARKER")
        self.assertEqual(translated_item["attachments"], [])
        self.assertNotIn("RAW SECRET LINE", str(translated_item))
        self.assertNotIn("translated-secret-photo.jpg", str(translated_item))
        self.assertIsNone(translated_item["emotional_needs"])
        self.assertIsNone(translated_item["action_for_partner"])
        self.assertIsNone(translated_item["advice_for_partner"])
        self.assertIsNone(translated_item["card_recommendation"])

        original_item = next(item for item in payload if item["title"] == "Original share")
        self.assertEqual(original_item["visibility"], "PARTNER_ORIGINAL")
        self.assertEqual(original_item["content"], "ORIGINAL PARTNER MARKER")
        self.assertEqual(original_item["partner_translated_content"], None)
        self.assertEqual(original_item["attachments"][0]["file_name"], "shared-photo.jpg")
        self.assertEqual(original_item["emotional_needs"], "Original needs context")
        self.assertEqual(original_item["action_for_partner"], "Original action")
        self.assertEqual(original_item["advice_for_partner"], "Original advice")

    def test_partner_feed_requires_verified_pair_scope(self) -> None:
        self.current_user_id = self.stranger_id

        response = self.client.get("/api/journals/partner")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


if __name__ == "__main__":
    unittest.main()
