import sys
import unittest
from datetime import timedelta
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.datetime_utils import utcnow  # noqa: E402
from app.models.analysis import Analysis  # noqa: E402
from app.models.audit_event import AuditEvent  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_response import CardResponse, ResponseStatus  # noqa: E402
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.notification_event import (  # noqa: E402
    NotificationActionType,
    NotificationDeliveryStatus,
    NotificationEvent,
)
from app.models.user import User  # noqa: E402
from app.services.data_soft_delete_purge import (  # noqa: E402
    SOFT_DELETE_PURGE_COUNT_KEYS,
    purge_soft_deleted_rows,
)


class DataSoftDeletePurgeServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        now = utcnow()
        self.fixed_now = now
        old_deleted_at = now - timedelta(days=120)
        recent_deleted_at = now - timedelta(days=10)

        with Session(self.engine) as session:
            purge_user = User(
                email="purge-user@example.com",
                full_name="Purge User",
                hashed_password="hashed",
                is_active=False,
                deleted_at=old_deleted_at,
            )
            partner_user = User(
                email="partner-user@example.com",
                full_name="Partner User",
                hashed_password="hashed",
                is_active=True,
            )
            card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Purge Card",
                description="desc",
                question="How are you?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            session.add(purge_user)
            session.add(partner_user)
            session.add(card)
            session.commit()
            session.refresh(purge_user)
            session.refresh(partner_user)
            session.refresh(card)

            old_journal = Journal(
                content="old journal",
                user_id=purge_user.id,
                deleted_at=old_deleted_at,
            )
            recent_journal = Journal(
                content="recent journal",
                user_id=partner_user.id,
                deleted_at=recent_deleted_at,
            )
            session.add(old_journal)
            session.add(recent_journal)
            session.commit()
            session.refresh(old_journal)
            session.refresh(recent_journal)

            old_analysis = Analysis(
                journal_id=old_journal.id,
                deleted_at=old_deleted_at,
            )
            recent_analysis = Analysis(
                journal_id=recent_journal.id,
                deleted_at=recent_deleted_at,
            )
            session.add(old_analysis)
            session.add(recent_analysis)

            old_session = CardSession(
                card_id=card.id,
                creator_id=purge_user.id,
                partner_id=partner_user.id,
                category=CardCategory.DAILY_VIBE.value,
                mode=CardSessionMode.DECK,
                status=CardSessionStatus.COMPLETED,
                deleted_at=old_deleted_at,
            )
            recent_session = CardSession(
                card_id=card.id,
                creator_id=partner_user.id,
                partner_id=None,
                category=CardCategory.DAILY_VIBE.value,
                mode=CardSessionMode.DECK,
                status=CardSessionStatus.PENDING,
                deleted_at=recent_deleted_at,
            )
            session.add(old_session)
            session.add(recent_session)
            session.commit()
            session.refresh(old_session)
            session.refresh(recent_session)

            old_response_user = CardResponse(
                card_id=card.id,
                user_id=purge_user.id,
                content="old response user",
                session_id=old_session.id,
                status=ResponseStatus.REVEALED,
                is_initiator=True,
                deleted_at=old_deleted_at,
            )
            old_response_partner = CardResponse(
                card_id=card.id,
                user_id=partner_user.id,
                content="old response partner",
                session_id=old_session.id,
                status=ResponseStatus.REVEALED,
                is_initiator=False,
                deleted_at=old_deleted_at,
            )
            recent_response = CardResponse(
                card_id=card.id,
                user_id=partner_user.id,
                content="recent response",
                session_id=recent_session.id,
                status=ResponseStatus.PENDING,
                is_initiator=True,
                deleted_at=recent_deleted_at,
            )
            session.add(old_response_user)
            session.add(old_response_partner)
            session.add(recent_response)

            old_notification = NotificationEvent(
                action_type=NotificationActionType.CARD,
                status=NotificationDeliveryStatus.SENT,
                receiver_user_id=partner_user.id,
                sender_user_id=purge_user.id,
                receiver_email="partner-user@example.com",
                dedupe_key="old-notif",
                deleted_at=old_deleted_at,
            )
            recent_notification = NotificationEvent(
                action_type=NotificationActionType.CARD,
                status=NotificationDeliveryStatus.SENT,
                receiver_user_id=partner_user.id,
                sender_user_id=partner_user.id,
                receiver_email="partner-user@example.com",
                dedupe_key="recent-notif",
                deleted_at=recent_deleted_at,
            )
            session.add(old_notification)
            session.add(recent_notification)

            audit_actor = AuditEvent(
                actor_user_id=purge_user.id,
                action="PURGE_ACTOR_REF",
                resource_type="user",
                resource_id=purge_user.id,
            )
            audit_target = AuditEvent(
                target_user_id=purge_user.id,
                action="PURGE_TARGET_REF",
                resource_type="user",
                resource_id=purge_user.id,
            )
            session.add(audit_actor)
            session.add(audit_target)
            session.commit()
            session.refresh(old_analysis)
            session.refresh(recent_analysis)
            session.refresh(old_response_user)
            session.refresh(old_response_partner)
            session.refresh(recent_response)
            session.refresh(old_notification)
            session.refresh(recent_notification)
            session.refresh(audit_actor)
            session.refresh(audit_target)

            self.old_ids = {
                "user": purge_user.id,
                "journal": old_journal.id,
                "analysis": old_analysis.id,
                "card_session": old_session.id,
                "card_response_user": old_response_user.id,
                "card_response_partner": old_response_partner.id,
                "notification": old_notification.id,
            }
            self.recent_ids = {
                "user_partner": partner_user.id,
                "journal": recent_journal.id,
                "analysis": recent_analysis.id,
                "card_session": recent_session.id,
                "card_response": recent_response.id,
                "notification": recent_notification.id,
            }

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_purge_soft_deleted_rows_dry_run_keeps_data(self) -> None:
        with Session(self.engine) as session:
            result = purge_soft_deleted_rows(
                session=session,
                purge_retention_days=90,
                dry_run=True,
                now=self.fixed_now,
            )
            session.rollback()

            self.assertEqual(
                result.candidate_counts,
                {
                    "analyses": 1,
                    "journals": 1,
                    "card_responses": 2,
                    "card_sessions": 1,
                    "notification_events": 1,
                    "users": 1,
                },
            )
            self.assertEqual(
                result.purged_counts,
                {key: 0 for key in SOFT_DELETE_PURGE_COUNT_KEYS},
            )

            self.assertIsNotNone(session.get(User, self.old_ids["user"]))
            self.assertIsNotNone(session.get(Journal, self.old_ids["journal"]))
            self.assertIsNotNone(session.get(Analysis, self.old_ids["analysis"]))
            self.assertIsNotNone(session.get(CardSession, self.old_ids["card_session"]))
            self.assertIsNotNone(session.get(CardResponse, self.old_ids["card_response_user"]))
            self.assertIsNotNone(session.get(CardResponse, self.old_ids["card_response_partner"]))
            self.assertIsNotNone(session.get(NotificationEvent, self.old_ids["notification"]))

    def test_purge_soft_deleted_rows_apply_deletes_old_rows_and_nulls_audit_fk(self) -> None:
        with Session(self.engine) as session:
            result = purge_soft_deleted_rows(
                session=session,
                purge_retention_days=90,
                dry_run=False,
                now=self.fixed_now,
            )
            session.commit()

            self.assertEqual(result.candidate_counts, result.purged_counts)

            self.assertIsNone(session.get(User, self.old_ids["user"]))
            self.assertIsNone(session.get(Journal, self.old_ids["journal"]))
            self.assertIsNone(session.get(Analysis, self.old_ids["analysis"]))
            self.assertIsNone(session.get(CardSession, self.old_ids["card_session"]))
            self.assertIsNone(session.get(CardResponse, self.old_ids["card_response_user"]))
            self.assertIsNone(session.get(CardResponse, self.old_ids["card_response_partner"]))
            self.assertIsNone(session.get(NotificationEvent, self.old_ids["notification"]))

            self.assertIsNotNone(session.get(User, self.recent_ids["user_partner"]))
            self.assertIsNotNone(session.get(Journal, self.recent_ids["journal"]))
            self.assertIsNotNone(session.get(Analysis, self.recent_ids["analysis"]))
            self.assertIsNotNone(session.get(CardSession, self.recent_ids["card_session"]))
            self.assertIsNotNone(session.get(CardResponse, self.recent_ids["card_response"]))
            self.assertIsNotNone(session.get(NotificationEvent, self.recent_ids["notification"]))

            audit_actor = session.exec(
                select(AuditEvent).where(AuditEvent.action == "PURGE_ACTOR_REF")
            ).first()
            self.assertIsNotNone(audit_actor)
            assert audit_actor is not None
            self.assertIsNone(audit_actor.actor_user_id)

            audit_target = session.exec(
                select(AuditEvent).where(AuditEvent.action == "PURGE_TARGET_REF")
            ).first()
            self.assertIsNotNone(audit_target)
            assert audit_target is not None
            self.assertIsNone(audit_target.target_user_id)

    def test_purge_soft_deleted_rows_skips_user_when_dependencies_not_yet_eligible(self) -> None:
        recent_deleted_at = self.fixed_now - timedelta(days=7)
        with Session(self.engine) as session:
            card = session.exec(select(Card)).first()
            assert card is not None
            blocked_response = CardResponse(
                card_id=card.id,
                user_id=self.old_ids["user"],
                content="blocked recent response",
                session_id=None,
                status=ResponseStatus.PENDING,
                is_initiator=True,
                deleted_at=recent_deleted_at,
            )
            session.add(blocked_response)
            session.commit()
            session.refresh(blocked_response)
            blocked_response_id = blocked_response.id

        with Session(self.engine) as session:
            result = purge_soft_deleted_rows(
                session=session,
                purge_retention_days=90,
                dry_run=False,
                now=self.fixed_now,
            )
            session.commit()

            self.assertEqual(result.candidate_counts["users"], 0)
            self.assertEqual(result.purged_counts["users"], 0)
            self.assertIsNotNone(session.get(User, self.old_ids["user"]))
            self.assertIsNotNone(session.get(CardResponse, blocked_response_id))


if __name__ == "__main__":
    unittest.main()
