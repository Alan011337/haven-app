import json
import sys
import unittest
import uuid
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, col, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api import journals  # noqa: E402
from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import card_decks, cards, users  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.audit_event import AuditEvent  # noqa: E402
from app.models.billing import BillingEntitlementState  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_response import CardResponse  # noqa: E402
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.pairing_abuse_guard import PairingAbuseGuard  # noqa: E402


class AuditLogBaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        self.analyze_patch = patch("app.api.journals.analyze_journal", new=AsyncMock(return_value={}))
        self.analyze_patch.start()
        self.journal_notify_patch = patch("app.api.journals.queue_partner_notification")
        self.journal_notify_patch.start()
        self.cards_notify_patch = patch("app.api.routers.cards.queue_partner_notification")
        self.cards_notify_patch.start()
        self.deck_notify_patch = patch("app.api.routers.card_decks.queue_partner_notification")
        self.deck_notify_patch.start()
        self.cards_socket_patch = patch(
            "app.api.routers.cards.manager.send_personal_message",
            new=AsyncMock(),
        )
        self.cards_socket_patch.start()
        self.deck_socket_patch = patch(
            "app.api.routers.card_decks.manager.send_personal_message",
            new=AsyncMock(),
        )
        self.deck_socket_patch.start()

        self.original_pairing_guard = users.pairing_abuse_guard
        self.original_pairing_ip_guard = users.pairing_ip_abuse_guard
        users.pairing_abuse_guard = PairingAbuseGuard(
            limit_count=100,
            window_seconds=300,
            failure_threshold=100,
            cooldown_seconds=300,
        )
        users.pairing_ip_abuse_guard = PairingAbuseGuard(
            limit_count=1000,
            window_seconds=300,
            failure_threshold=1000,
            cooldown_seconds=300,
        )

        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")
        app.include_router(journals.router, prefix="/api/journals")
        app.include_router(cards.router, prefix="/api/cards")
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
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

        with Session(self.engine) as session:
            user_a = User(email="audit-a@example.com", full_name="Audit A", hashed_password="hashed")
            user_b = User(
                email="audit-b@example.com",
                full_name="Audit B",
                hashed_password="hashed",
                invite_code="PAIRB1",
                invite_code_created_at=utcnow(),
            )
            card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Audit Card",
                description="desc",
                question="Audit test question?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            session.add(user_a)
            session.add(user_b)
            session.add(card)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(card)

            session.add(
                BillingEntitlementState(
                    user_id=user_a.id,
                    lifecycle_state="ACTIVE",
                    current_plan="premium",
                )
            )
            session.commit()

            deck_session = CardSession(
                card_id=card.id,
                creator_id=user_a.id,
                partner_id=user_b.id,
                category=card.category.value,
                mode=CardSessionMode.DECK,
                status=CardSessionStatus.PENDING,
            )
            session.add(deck_session)
            session.commit()
            session.refresh(deck_session)

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.card_id = card.id
            self.deck_session_id = deck_session.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        users.pairing_abuse_guard = self.original_pairing_guard
        users.pairing_ip_abuse_guard = self.original_pairing_ip_guard
        self.client.close()
        self.deck_socket_patch.stop()
        self.cards_socket_patch.stop()
        self.deck_notify_patch.stop()
        self.cards_notify_patch.stop()
        self.journal_notify_patch.stop()
        self.analyze_patch.stop()
        self.engine.dispose()

    def _latest_audit_event(self, action: str) -> AuditEvent:
        with Session(self.engine) as session:
            row = session.exec(
                select(AuditEvent)
                .where(AuditEvent.action == action)
                .order_by(col(AuditEvent.created_at).desc())
            ).first()
            self.assertIsNotNone(row)
            assert row is not None
            return row

    def test_journal_create_records_audit_event(self) -> None:
        response = self.client.post("/api/journals/", json={"content": "audit journal"})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        row = self._latest_audit_event("JOURNAL_CREATE")
        self.assertEqual(row.actor_user_id, self.user_a_id)
        self.assertEqual(row.resource_type, "journal")
        self.assertEqual(row.resource_id, uuid.UUID(payload["id"]))
        metadata = json.loads(row.metadata_json or "{}")
        self.assertIn("score_gained", metadata)
        self.assertIn("has_analysis", metadata)

    def test_journal_delete_records_audit_event(self) -> None:
        with Session(self.engine) as session:
            journal = Journal(content="delete me", user_id=self.user_a_id)
            session.add(journal)
            session.commit()
            session.refresh(journal)
            journal_id = journal.id

        response = self.client.delete(f"/api/journals/{journal_id}")
        self.assertEqual(response.status_code, 204)

        row = self._latest_audit_event("JOURNAL_DELETE")
        self.assertEqual(row.actor_user_id, self.user_a_id)
        self.assertEqual(row.resource_type, "journal")
        self.assertEqual(row.resource_id, journal_id)

    def test_pair_success_records_audit_event(self) -> None:
        response = self.client.post(
            "/api/users/pair",
            json={"invite_code": "pairb1"},
            headers={"x-forwarded-for": "203.0.113.42"},
        )
        self.assertEqual(response.status_code, 200)

        row = self._latest_audit_event("USER_PAIR")
        self.assertEqual(row.actor_user_id, self.user_a_id)
        self.assertEqual(row.target_user_id, self.user_b_id)
        self.assertEqual(row.resource_type, "user_pairing")
        self.assertEqual(row.resource_id, self.user_b_id)
        metadata = json.loads(row.metadata_json or "{}")
        self.assertEqual(metadata.get("client_ip"), "203.0.x.x")

    def test_card_response_records_audit_event(self) -> None:
        response = self.client.post(
            "/api/cards/respond",
            json={"card_id": str(self.card_id), "content": "card audit"},
        )
        self.assertEqual(response.status_code, 200)

        row = self._latest_audit_event("CARD_RESPOND")
        self.assertEqual(row.actor_user_id, self.user_a_id)
        self.assertEqual(row.resource_type, "card")
        self.assertEqual(row.resource_id, self.card_id)
        metadata = json.loads(row.metadata_json or "{}")
        self.assertIn("is_new_response", metadata)

    def test_deck_response_records_audit_event(self) -> None:
        response = self.client.post(
            f"/api/card-decks/respond/{self.deck_session_id}",
            json={"content": "deck audit"},
        )
        self.assertEqual(response.status_code, 200)

        row = self._latest_audit_event("CARD_DECK_RESPOND")
        self.assertEqual(row.actor_user_id, self.user_a_id)
        self.assertEqual(row.resource_type, "card_session")
        self.assertEqual(row.resource_id, self.deck_session_id)
        metadata = json.loads(row.metadata_json or "{}")
        self.assertEqual(metadata.get("session_status"), "WAITING_PARTNER")

    def test_deck_reveal_log_does_not_include_session_id(self) -> None:
        with Session(self.engine) as session:
            existing = session.exec(
                select(CardResponse).where(
                    CardResponse.session_id == self.deck_session_id,
                    CardResponse.user_id == self.user_a_id,
                )
            ).first()
            self.assertIsNone(existing)
            session.add(
                CardResponse(
                    card_id=self.card_id,
                    session_id=self.deck_session_id,
                    user_id=self.user_a_id,
                    content="first response",
                )
            )
            session.commit()

        self.current_user_id = self.user_b_id
        with self.assertLogs("app.api.routers.card_decks", level="INFO") as captured:
            response = self.client.post(
                f"/api/card-decks/respond/{self.deck_session_id}",
                json={"content": "second response"},
            )
        self.assertEqual(response.status_code, 200)
        merged = "\n".join(captured.output)
        self.assertIn("Deck session completed. Broadcasting reveal event.", merged)
        self.assertNotIn(str(self.deck_session_id), merged)

    def test_data_export_records_audit_event(self) -> None:
        response = self.client.get("/api/users/me/data-export")
        self.assertEqual(response.status_code, 200)

        row = self._latest_audit_event("USER_DATA_EXPORT")
        self.assertEqual(row.actor_user_id, self.user_a_id)
        self.assertEqual(row.resource_type, "user")
        self.assertEqual(row.resource_id, self.user_a_id)
        metadata = json.loads(row.metadata_json or "{}")
        self.assertIn("journals", metadata)
        self.assertIn("analyses", metadata)
        self.assertIn("card_responses", metadata)
        self.assertIn("card_sessions", metadata)
        self.assertIn("notification_events", metadata)

    def test_data_erase_records_audit_event(self) -> None:
        response = self.client.delete("/api/users/me/data")
        self.assertEqual(response.status_code, 200)

        row = self._latest_audit_event("USER_DATA_ERASE")
        self.assertIsNone(row.actor_user_id)
        self.assertEqual(row.resource_type, "user")
        self.assertEqual(row.resource_id, self.user_a_id)
        metadata = json.loads(row.metadata_json or "{}")
        self.assertEqual(metadata.get("erased_user_id"), str(self.user_a_id))
        self.assertEqual(metadata.get("users"), 1)

        with Session(self.engine) as session:
            self.assertIsNone(session.get(User, self.user_a_id))


if __name__ == "__main__":
    unittest.main()
