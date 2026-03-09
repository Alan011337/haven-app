import sys
import unittest
import uuid
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.user import User  # noqa: E402
from app.services.notification_payloads import build_partner_notification_payload  # noqa: E402


class NotificationPayloadBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_build_payload_with_sender_partner(self) -> None:
        with Session(self.engine) as session:
            sender = User(email="sender@example.com", full_name="Sender", hashed_password="hashed")
            partner = User(email="partner@example.com", full_name="Partner", hashed_password="hashed")
            sender.partner_id = partner.id
            session.add(sender)
            session.add(partner)
            session.commit()
            session.refresh(sender)
            session.refresh(partner)

            scope_id = uuid.uuid4()
            payload = build_partner_notification_payload(
                session=session,
                sender_user=sender,
                event_type="card_waiting",
                scope_id=scope_id,
                source_session_id=scope_id,
            )

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["receiver_email"], "partner@example.com")
        self.assertEqual(payload["sender_name"], "Sender")
        self.assertEqual(payload["receiver_user_id"], partner.id)
        self.assertEqual(payload["sender_user_id"], sender.id)
        self.assertEqual(payload["source_session_id"], scope_id)
        self.assertTrue(payload["dedupe_key"].startswith(f"card_waiting:{scope_id}:"))
        self.assertEqual(payload["event_type"], "card_waiting")

    def test_build_payload_with_explicit_partner_override(self) -> None:
        with Session(self.engine) as session:
            sender = User(email="sender@example.com", full_name="Sender", hashed_password="hashed")
            override_partner = User(
                email="override@example.com",
                full_name="Override",
                hashed_password="hashed",
            )
            session.add(sender)
            session.add(override_partner)
            session.commit()
            session.refresh(sender)
            session.refresh(override_partner)

            payload = build_partner_notification_payload(
                session=session,
                sender_user=sender,
                event_type="journal",
                scope_id="journal-1",
                source_session_id=None,
                partner_user_id=override_partner.id,
            )

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["receiver_email"], "override@example.com")
        self.assertTrue(payload["dedupe_key"].startswith("journal:journal-1:"))
        self.assertEqual(payload["event_type"], "journal_created")

    def test_build_payload_returns_none_without_partner(self) -> None:
        with Session(self.engine) as session:
            sender = User(email="sender@example.com", full_name="Sender", hashed_password="hashed")
            session.add(sender)
            session.commit()
            session.refresh(sender)

            payload = build_partner_notification_payload(
                session=session,
                sender_user=sender,
                event_type="journal",
                scope_id="journal-1",
            )

        self.assertIsNone(payload)

    def test_build_payload_returns_none_when_partner_missing_email(self) -> None:
        with Session(self.engine) as session:
            sender = User(email="sender@example.com", full_name="Sender", hashed_password="hashed")
            partner = User(email="temp@example.com", full_name="Partner", hashed_password="hashed")
            sender.partner_id = partner.id
            session.add(sender)
            session.add(partner)
            session.commit()
            session.refresh(sender)
            session.refresh(partner)

            partner.email = ""
            session.add(partner)
            session.commit()

            payload = build_partner_notification_payload(
                session=session,
                sender_user=sender,
                event_type="card_revealed",
                scope_id="session-1",
            )

        self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
