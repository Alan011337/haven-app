import sys
import unittest
from datetime import timedelta
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, col, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api import journals  # noqa: E402
from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import card_decks, users  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.audit_event import AuditEvent, AuditEventOutcome  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.audit_log_retention import purge_expired_audit_events  # noqa: E402
from app.services.pairing_abuse_guard import PairingAbuseGuard  # noqa: E402


class AuditLogDeniedAndErrorTests(unittest.TestCase):
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
        self.deck_notify_patch = patch("app.api.routers.card_decks.queue_partner_notification")
        self.deck_notify_patch.start()
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
            user_a = User(email="sec-a@example.com", full_name="Sec A", hashed_password="hashed")
            user_b = User(email="sec-b@example.com", full_name="Sec B", hashed_password="hashed")
            user_c = User(email="sec-c@example.com", full_name="Sec C", hashed_password="hashed")
            card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Denied Card",
                description="desc",
                question="Denied card question?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            session.add(user_a)
            session.add(user_b)
            session.add(user_c)
            session.add(card)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(user_c)
            session.refresh(card)

            deck_session = CardSession(
                card_id=card.id,
                creator_id=user_a.id,
                partner_id=user_b.id,
                category=card.category.value,
                mode=CardSessionMode.DECK,
                status=CardSessionStatus.PENDING,
            )
            session.add(deck_session)

            journal = Journal(content="owner journal", user_id=user_a.id)
            session.add(journal)
            session.commit()
            session.refresh(deck_session)
            session.refresh(journal)

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.user_c_id = user_c.id
            self.deck_session_id = deck_session.id
            self.journal_id = journal.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        users.pairing_abuse_guard = self.original_pairing_guard
        users.pairing_ip_abuse_guard = self.original_pairing_ip_guard
        self.client.close()
        self.deck_socket_patch.stop()
        self.deck_notify_patch.stop()
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

    def test_user_read_denied_records_audit_event(self) -> None:
        self.current_user_id = self.user_c_id
        response = self.client.get(f"/api/users/{self.user_a_id}")
        self.assertEqual(response.status_code, 403)

        row = self._latest_audit_event("USER_READ_DENIED")
        self.assertEqual(row.actor_user_id, self.user_c_id)
        self.assertEqual(row.target_user_id, self.user_a_id)
        self.assertEqual(row.resource_id, self.user_a_id)
        self.assertEqual(row.outcome, AuditEventOutcome.DENIED)
        self.assertEqual(row.reason, "not_self_or_partner")

    def test_journal_delete_denied_records_audit_event(self) -> None:
        self.current_user_id = self.user_b_id
        response = self.client.delete(f"/api/journals/{self.journal_id}")
        self.assertEqual(response.status_code, 403)

        row = self._latest_audit_event("JOURNAL_DELETE_DENIED")
        self.assertEqual(row.actor_user_id, self.user_b_id)
        self.assertEqual(row.target_user_id, self.user_a_id)
        self.assertEqual(row.resource_id, self.journal_id)
        self.assertEqual(row.outcome, AuditEventOutcome.DENIED)
        self.assertEqual(row.reason, "not_owner")

    def test_deck_respond_denied_records_audit_event(self) -> None:
        self.current_user_id = self.user_c_id
        response = self.client.post(
            f"/api/card-decks/respond/{self.deck_session_id}",
            json={"content": "should fail"},
        )
        self.assertEqual(response.status_code, 403)

        row = self._latest_audit_event("CARD_DECK_RESPOND_DENIED")
        self.assertEqual(row.actor_user_id, self.user_c_id)
        self.assertEqual(row.target_user_id, self.user_a_id)
        self.assertEqual(row.resource_id, self.deck_session_id)
        self.assertEqual(row.outcome, AuditEventOutcome.DENIED)
        self.assertEqual(row.reason, "not_participant")

    def test_journal_create_error_records_audit_event(self) -> None:
        secret_fragment = "postgresql://svc:super-secret@db.internal:5432/haven"
        with patch(
            "app.api.journals.flush_with_error_handling",
            side_effect=RuntimeError(secret_fragment),
        ):
            with self.assertLogs("app.api.journals", level="ERROR") as captured:
                response = self.client.post("/api/journals/", json={"content": "trigger error"})
        self.assertEqual(response.status_code, 500)
        merged_logs = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged_logs)
        self.assertNotIn("super-secret", merged_logs)
        self.assertNotIn("postgresql://", merged_logs)

        row = self._latest_audit_event("JOURNAL_CREATE_ERROR")
        self.assertEqual(row.actor_user_id, self.user_a_id)
        self.assertEqual(row.resource_type, "journal")
        self.assertEqual(row.outcome, AuditEventOutcome.ERROR)
        self.assertEqual(row.reason, "RuntimeError")

    def test_data_erase_error_records_audit_event(self) -> None:
        with patch(
            "app.api.routers.users.commit_with_error_handling",
            side_effect=HTTPException(status_code=500, detail="forced failure"),
        ):
            response = self.client.delete("/api/users/me/data")
        self.assertEqual(response.status_code, 500)

        row = self._latest_audit_event("USER_DATA_ERASE_ERROR")
        self.assertIsNone(row.actor_user_id)
        self.assertEqual(row.resource_type, "user")
        self.assertEqual(row.resource_id, self.user_a_id)
        self.assertEqual(row.outcome, AuditEventOutcome.ERROR)
        self.assertEqual(row.reason, "http_500")

        with Session(self.engine) as session:
            self.assertIsNotNone(session.get(User, self.user_a_id))


class AuditLogRetentionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_purge_expired_audit_events_deletes_only_old_rows(self) -> None:
        now = utcnow()
        old_created_at = now - timedelta(days=400)
        fresh_created_at = now - timedelta(days=30)

        with Session(self.engine) as session:
            session.add(
                AuditEvent(
                    actor_user_id=None,
                    action="OLD_EVENT",
                    resource_type="system",
                    outcome=AuditEventOutcome.SUCCESS,
                    created_at=old_created_at,
                )
            )
            session.add(
                AuditEvent(
                    actor_user_id=None,
                    action="FRESH_EVENT",
                    resource_type="system",
                    outcome=AuditEventOutcome.SUCCESS,
                    created_at=fresh_created_at,
                )
            )
            session.commit()

            deleted = purge_expired_audit_events(
                session=session,
                retention_days=365,
                now=now,
            )
            session.commit()

            remaining_actions = [
                row.action
                for row in session.exec(select(AuditEvent).order_by(col(AuditEvent.created_at))).all()
            ]

        self.assertEqual(deleted, 1)
        self.assertEqual(remaining_actions, ["FRESH_EVENT"])


if __name__ == "__main__":
    unittest.main()
