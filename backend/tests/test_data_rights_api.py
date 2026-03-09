# AUTHZ_MATRIX: DELETE /api/users/me/data
# READ_AUTHZ_MATRIX: GET /api/users/me/data-export

import sys
import unittest
import json
from datetime import datetime
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import users  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.analysis import Analysis  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_response import CardResponse, ResponseStatus  # noqa: E402
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.notification_event import (  # noqa: E402
    NotificationActionType,
    NotificationDeliveryStatus,
    NotificationEvent,
)
from app.models.audit_event import AuditEvent, AuditEventOutcome  # noqa: E402
from app.models.billing import BillingEntitlementState  # noqa: E402
from app.models.user import User  # noqa: E402


class DataRightsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

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
            user_a = User(email="a@example.com", full_name="A", hashed_password="hashed")
            user_b = User(email="b@example.com", full_name="B", hashed_password="hashed")
            user_c = User(email="c@example.com", full_name="C", hashed_password="hashed")
            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id

            card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Card",
                description="desc",
                question="How are you?",
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

            session.add(
                BillingEntitlementState(
                    user_id=user_a.id,
                    lifecycle_state="ACTIVE",
                    current_plan="premium",
                )
            )
            session.add(
                BillingEntitlementState(
                    user_id=user_b.id,
                    lifecycle_state="ACTIVE",
                    current_plan="premium",
                )
            )
            session.commit()

            journal_a = Journal(content="user-a-journal", user_id=user_a.id)
            journal_b = Journal(content="user-b-journal", user_id=user_b.id)
            session.add(journal_a)
            session.add(journal_b)
            session.commit()
            session.refresh(journal_a)
            session.refresh(journal_b)

            analysis_a = Analysis(journal_id=journal_a.id, mood_label="calm")
            analysis_b = Analysis(journal_id=journal_b.id, mood_label="happy")
            session.add(analysis_a)
            session.add(analysis_b)

            shared_session = CardSession(
                card_id=card.id,
                creator_id=user_a.id,
                partner_id=user_b.id,
                category=CardCategory.DAILY_VIBE.value,
                mode=CardSessionMode.DECK,
                status=CardSessionStatus.COMPLETED,
            )
            unrelated_session = CardSession(
                card_id=card.id,
                creator_id=user_b.id,
                partner_id=user_c.id,
                category=CardCategory.DAILY_VIBE.value,
                mode=CardSessionMode.DECK,
                status=CardSessionStatus.PENDING,
            )
            session.add(shared_session)
            session.add(unrelated_session)
            session.commit()
            session.refresh(shared_session)
            session.refresh(unrelated_session)

            session.add(
                CardResponse(
                    card_id=card.id,
                    user_id=user_a.id,
                    content="a-shared",
                    session_id=shared_session.id,
                    status=ResponseStatus.REVEALED,
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    card_id=card.id,
                    user_id=user_b.id,
                    content="b-shared",
                    session_id=shared_session.id,
                    status=ResponseStatus.REVEALED,
                    is_initiator=False,
                )
            )
            session.add(
                CardResponse(
                    card_id=card.id,
                    user_id=user_a.id,
                    content="a-library",
                    session_id=None,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    card_id=card.id,
                    user_id=user_b.id,
                    content="b-unrelated",
                    session_id=unrelated_session.id,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )

            session.add(
                NotificationEvent(
                    action_type=NotificationActionType.JOURNAL,
                    status=NotificationDeliveryStatus.SENT,
                    receiver_user_id=user_a.id,
                    sender_user_id=user_b.id,
                    receiver_email=user_a.email,
                    dedupe_key="a-recv",
                )
            )
            notif_a_send = NotificationEvent(
                action_type=NotificationActionType.CARD,
                status=NotificationDeliveryStatus.FAILED,
                receiver_user_id=user_b.id,
                sender_user_id=user_a.id,
                receiver_email=user_b.email,
                dedupe_key="a-send",
                error_message="retry_exhausted",
            )
            unrelated_notif = NotificationEvent(
                action_type=NotificationActionType.CARD,
                status=NotificationDeliveryStatus.SENT,
                receiver_user_id=user_c.id,
                sender_user_id=user_b.id,
                receiver_email=user_c.email,
                dedupe_key="unrelated",
            )
            session.add(notif_a_send)
            session.add(unrelated_notif)
            session.commit()
            session.refresh(notif_a_send)
            session.refresh(unrelated_notif)

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.user_c_id = user_c.id
            self.journal_a_id = journal_a.id
            self.journal_b_id = journal_b.id
            self.shared_session_id = shared_session.id
            self.unrelated_session_id = unrelated_session.id
            self.notification_a_send_id = notif_a_send.id
            self.notification_unrelated_id = unrelated_notif.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_data_export_is_scoped_to_current_user(self) -> None:
        response = self.client.get("/api/users/me/data-export")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["export_version"], "v1")
        self.assertIn("expires_at", payload)
        exported_at = datetime.fromisoformat(payload["exported_at"].replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(payload["expires_at"].replace("Z", "+00:00"))
        self.assertGreater(expires_at, exported_at)
        max_ttl = (expires_at - exported_at).total_seconds()
        self.assertGreaterEqual(max_ttl, 6 * 24 * 3600)
        self.assertLessEqual(max_ttl, 8 * 24 * 3600)
        self.assertEqual(payload["user"]["id"], str(self.user_a_id))
        self.assertEqual(len(payload["journals"]), 1)
        self.assertEqual(payload["journals"][0]["id"], str(self.journal_a_id))
        self.assertEqual(len(payload["analyses"]), 1)
        self.assertEqual(payload["analyses"][0]["journal_id"], str(self.journal_a_id))
        self.assertEqual(len(payload["card_responses"]), 2)
        self.assertTrue(
            all(item["user_id"] == str(self.user_a_id) for item in payload["card_responses"])
        )
        self.assertEqual(len(payload["card_sessions"]), 1)
        self.assertEqual(payload["card_sessions"][0]["id"], str(self.shared_session_id))
        self.assertEqual(len(payload["notification_events"]), 2)
        self.assertTrue(
            all(
                item.get("receiver_user_id") == str(self.user_a_id)
                or item.get("sender_user_id") == str(self.user_a_id)
                for item in payload["notification_events"]
            )
        )

    def test_data_erase_removes_current_user_data_and_unpairs_partner(self) -> None:
        response = self.client.delete("/api/users/me/data")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "erased")
        self.assertEqual(payload["deleted_user_id"], str(self.user_a_id))

        with Session(self.engine) as session:
            self.assertIsNone(session.get(User, self.user_a_id))

            partner = session.get(User, self.user_b_id)
            self.assertIsNotNone(partner)
            self.assertIsNone(partner.partner_id)

            user_b_journal = session.get(Journal, self.journal_b_id)
            self.assertIsNotNone(user_b_journal)
            self.assertEqual(user_b_journal.user_id, self.user_b_id)

            user_a_journals = session.exec(
                select(Journal).where(Journal.user_id == self.user_a_id)
            ).all()
            self.assertEqual(len(user_a_journals), 0)

            user_a_analyses = session.exec(
                select(Analysis).where(Analysis.journal_id == self.journal_a_id)
            ).all()
            self.assertEqual(len(user_a_analyses), 0)

            shared_session = session.get(CardSession, self.shared_session_id)
            self.assertIsNone(shared_session)
            unrelated_session = session.get(CardSession, self.unrelated_session_id)
            self.assertIsNotNone(unrelated_session)

            shared_responses = session.exec(
                select(CardResponse).where(CardResponse.session_id == self.shared_session_id)
            ).all()
            self.assertEqual(len(shared_responses), 0)

            user_a_responses = session.exec(
                select(CardResponse).where(CardResponse.user_id == self.user_a_id)
            ).all()
            self.assertEqual(len(user_a_responses), 0)

            unrelated_responses = session.exec(
                select(CardResponse).where(CardResponse.session_id == self.unrelated_session_id)
            ).all()
            self.assertEqual(len(unrelated_responses), 1)

            notifications_with_a = session.exec(
                select(NotificationEvent).where(
                    (NotificationEvent.receiver_user_id == self.user_a_id)
                    | (NotificationEvent.sender_user_id == self.user_a_id)
                )
            ).all()
            self.assertEqual(len(notifications_with_a), 0)

            unrelated_notifications = session.exec(
                select(NotificationEvent).where(NotificationEvent.receiver_user_id == self.user_c_id)
            ).all()
            self.assertEqual(len(unrelated_notifications), 1)

    def test_data_erase_handles_existing_audit_fk_references(self) -> None:
        with Session(self.engine) as session:
            session.add(
                AuditEvent(
                    actor_user_id=self.user_a_id,
                    target_user_id=self.user_b_id,
                    action="PREEXISTING_ACTOR_EVENT",
                    resource_type="user",
                    resource_id=self.user_a_id,
                    outcome=AuditEventOutcome.SUCCESS,
                )
            )
            session.add(
                AuditEvent(
                    actor_user_id=self.user_b_id,
                    target_user_id=self.user_a_id,
                    action="PREEXISTING_TARGET_EVENT",
                    resource_type="user",
                    resource_id=self.user_a_id,
                    outcome=AuditEventOutcome.SUCCESS,
                )
            )
            session.commit()

        response = self.client.delete("/api/users/me/data")
        self.assertEqual(response.status_code, 200)

        with Session(self.engine) as session:
            actor_row = session.exec(
                select(AuditEvent).where(AuditEvent.action == "PREEXISTING_ACTOR_EVENT")
            ).first()
            self.assertIsNotNone(actor_row)
            assert actor_row is not None
            self.assertIsNone(actor_row.actor_user_id)
            self.assertEqual(actor_row.target_user_id, self.user_b_id)

            target_row = session.exec(
                select(AuditEvent).where(AuditEvent.action == "PREEXISTING_TARGET_EVENT")
            ).first()
            self.assertIsNotNone(target_row)
            assert target_row is not None
            self.assertEqual(target_row.actor_user_id, self.user_b_id)
            self.assertIsNone(target_row.target_user_id)

            erase_row = session.exec(
                select(AuditEvent).where(AuditEvent.action == "USER_DATA_ERASE")
            ).first()
            self.assertIsNotNone(erase_row)
            assert erase_row is not None
            self.assertIsNone(erase_row.actor_user_id)
            self.assertEqual(erase_row.resource_id, self.user_a_id)

    def test_data_erase_soft_delete_marks_rows_when_feature_enabled(self) -> None:
        previous_value = settings.DATA_SOFT_DELETE_ENABLED
        settings.DATA_SOFT_DELETE_ENABLED = True
        try:
            response = self.client.delete("/api/users/me/data")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["status"], "soft_deleted")
            self.assertEqual(payload["deleted_user_id"], str(self.user_a_id))

            with Session(self.engine) as session:
                user_a = session.get(User, self.user_a_id)
                self.assertIsNotNone(user_a)
                assert user_a is not None
                self.assertFalse(user_a.is_active)
                self.assertIsNone(user_a.partner_id)
                self.assertIsNotNone(user_a.deleted_at)

                partner = session.get(User, self.user_b_id)
                self.assertIsNotNone(partner)
                assert partner is not None
                self.assertIsNone(partner.partner_id)
                self.assertIsNone(partner.deleted_at)

                user_a_journals = session.exec(
                    select(Journal).where(Journal.user_id == self.user_a_id)
                ).all()
                self.assertEqual(len(user_a_journals), 1)
                self.assertTrue(all(row.deleted_at is not None for row in user_a_journals))

                user_b_journals = session.exec(
                    select(Journal).where(Journal.user_id == self.user_b_id)
                ).all()
                self.assertEqual(len(user_b_journals), 1)
                self.assertTrue(all(row.deleted_at is None for row in user_b_journals))

                user_a_analyses = session.exec(
                    select(Analysis).where(Analysis.journal_id == self.journal_a_id)
                ).all()
                self.assertEqual(len(user_a_analyses), 1)
                self.assertTrue(all(row.deleted_at is not None for row in user_a_analyses))

                shared_session = session.get(CardSession, self.shared_session_id)
                self.assertIsNotNone(shared_session)
                assert shared_session is not None
                self.assertIsNotNone(shared_session.deleted_at)

                unrelated_session = session.get(CardSession, self.unrelated_session_id)
                self.assertIsNotNone(unrelated_session)
                assert unrelated_session is not None
                self.assertIsNone(unrelated_session.deleted_at)

                user_a_responses = session.exec(
                    select(CardResponse).where(CardResponse.user_id == self.user_a_id)
                ).all()
                self.assertEqual(len(user_a_responses), 2)
                self.assertTrue(all(row.deleted_at is not None for row in user_a_responses))

                shared_session_responses = session.exec(
                    select(CardResponse).where(CardResponse.session_id == self.shared_session_id)
                ).all()
                self.assertEqual(len(shared_session_responses), 2)
                self.assertTrue(all(row.deleted_at is not None for row in shared_session_responses))

                unrelated_responses = session.exec(
                    select(CardResponse).where(CardResponse.session_id == self.unrelated_session_id)
                ).all()
                self.assertEqual(len(unrelated_responses), 1)
                self.assertTrue(all(row.deleted_at is None for row in unrelated_responses))

                notifications_with_a = session.exec(
                    select(NotificationEvent).where(
                        (NotificationEvent.receiver_user_id == self.user_a_id)
                        | (NotificationEvent.sender_user_id == self.user_a_id)
                    )
                ).all()
                self.assertEqual(len(notifications_with_a), 2)
                self.assertTrue(all(row.deleted_at is not None for row in notifications_with_a))

                unrelated_notifications = session.exec(
                    select(NotificationEvent).where(NotificationEvent.receiver_user_id == self.user_c_id)
                ).all()
                self.assertEqual(len(unrelated_notifications), 1)
                self.assertTrue(all(row.deleted_at is None for row in unrelated_notifications))

                erase_row = session.exec(
                    select(AuditEvent).where(AuditEvent.action == "USER_DATA_ERASE")
                ).first()
                self.assertIsNotNone(erase_row)
                assert erase_row is not None
                metadata = json.loads(erase_row.metadata_json or "{}")
                self.assertEqual(metadata.get("delete_mode"), "soft_delete")
        finally:
            settings.DATA_SOFT_DELETE_ENABLED = previous_value

    def test_soft_deleted_rows_are_hidden_from_partner_export_and_notification_reads(self) -> None:
        previous_value = settings.DATA_SOFT_DELETE_ENABLED
        settings.DATA_SOFT_DELETE_ENABLED = True
        try:
            erase_response = self.client.delete("/api/users/me/data")
            self.assertEqual(erase_response.status_code, 200)
            self.assertEqual(erase_response.json()["status"], "soft_deleted")

            self.current_user_id = self.user_b_id

            export_response = self.client.get("/api/users/me/data-export")
            self.assertEqual(export_response.status_code, 200)
            export_payload = export_response.json()
            self.assertEqual(export_payload["user"]["id"], str(self.user_b_id))
            self.assertEqual(len(export_payload["journals"]), 1)
            self.assertEqual(len(export_payload["analyses"]), 1)
            self.assertEqual(len(export_payload["card_sessions"]), 1)
            self.assertEqual(
                export_payload["card_sessions"][0]["id"],
                str(self.unrelated_session_id),
            )
            self.assertEqual(len(export_payload["card_responses"]), 1)
            self.assertEqual(
                export_payload["card_responses"][0]["session_id"],
                str(self.unrelated_session_id),
            )
            self.assertEqual(len(export_payload["notification_events"]), 1)
            self.assertEqual(
                export_payload["notification_events"][0]["id"],
                str(self.notification_unrelated_id),
            )
            self.assertIsNone(export_payload["notification_events"][0]["deleted_at"])

            notifications_response = self.client.get("/api/users/notifications")
            self.assertEqual(notifications_response.status_code, 200)
            self.assertEqual(notifications_response.json(), [])

            stats_response = self.client.get("/api/users/notifications/stats")
            self.assertEqual(stats_response.status_code, 200)
            stats_payload = stats_response.json()
            self.assertEqual(stats_payload["total_count"], 0)
            self.assertEqual(stats_payload["unread_count"], 0)

            mark_read_response = self.client.post("/api/users/notifications/mark-read")
            self.assertEqual(mark_read_response.status_code, 200)
            self.assertEqual(mark_read_response.json()["updated"], 0)

            single_read_response = self.client.post(
                f"/api/users/notifications/{self.notification_a_send_id}/read"
            )
            self.assertEqual(single_read_response.status_code, 404)

            retry_response = self.client.post(
                f"/api/users/notifications/{self.notification_a_send_id}/retry"
            )
            self.assertEqual(retry_response.status_code, 404)
        finally:
            settings.DATA_SOFT_DELETE_ENABLED = previous_value
            self.current_user_id = self.user_a_id


if __name__ == "__main__":
    unittest.main()
