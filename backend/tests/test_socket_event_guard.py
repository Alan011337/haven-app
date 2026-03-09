import sys
import unittest
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.socket_event_guard import resolve_typing_session_id  # noqa: E402


class SocketEventGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            self.user_a = User(email="a@example.com", full_name="A", hashed_password="hashed")
            self.user_b = User(email="b@example.com", full_name="B", hashed_password="hashed")
            self.user_c = User(email="c@example.com", full_name="C", hashed_password="hashed")
            self.user_a.partner_id = self.user_b.id
            self.user_b.partner_id = self.user_a.id

            self.card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Daily",
                description="desc",
                question="question",
                difficulty_level=1,
                depth_level=1,
                is_ai_generated=False,
            )

            session.add(self.user_a)
            session.add(self.user_b)
            session.add(self.user_c)
            session.add(self.card)
            session.commit()

            session.refresh(self.user_a)
            session.refresh(self.user_b)
            session.refresh(self.user_c)
            session.refresh(self.card)
            self.user_a_id = self.user_a.id
            self.user_b_id = self.user_b.id
            self.user_c_id = self.user_c.id

            self.card_session = CardSession(
                card_id=self.card.id,
                category=self.card.category.value,
                creator_id=self.user_a_id,
                partner_id=self.user_b_id,
                mode=CardSessionMode.DAILY_RITUAL,
                status=CardSessionStatus.PENDING,
            )
            session.add(self.card_session)
            session.commit()
            session.refresh(self.card_session)
            self.card_session_id = self.card_session.id

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_accepts_valid_session_participants(self) -> None:
        with Session(self.engine) as session:
            result = resolve_typing_session_id(
                session=session,
                sender_user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
                raw_session_id=str(self.card_session_id),
            )
        self.assertEqual(result, str(self.card_session_id))

    def test_rejects_invalid_session_id_format(self) -> None:
        with Session(self.engine) as session:
            result = resolve_typing_session_id(
                session=session,
                sender_user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
                raw_session_id="not-a-uuid",
            )
        self.assertIsNone(result)

    def test_rejects_nonexistent_session(self) -> None:
        with Session(self.engine) as session:
            result = resolve_typing_session_id(
                session=session,
                sender_user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
                raw_session_id="00000000-0000-0000-0000-000000000000",
            )
        self.assertIsNone(result)

    def test_rejects_sender_not_in_session(self) -> None:
        with Session(self.engine) as session:
            result = resolve_typing_session_id(
                session=session,
                sender_user_id=self.user_c_id,
                partner_user_id=self.user_b_id,
                raw_session_id=str(self.card_session_id),
            )
        self.assertIsNone(result)

    def test_rejects_partner_not_in_session(self) -> None:
        with Session(self.engine) as session:
            result = resolve_typing_session_id(
                session=session,
                sender_user_id=self.user_a_id,
                partner_user_id=self.user_c_id,
                raw_session_id=str(self.card_session_id),
            )
        self.assertIsNone(result)

    def test_rejects_when_partner_is_missing(self) -> None:
        with Session(self.engine) as session:
            result = resolve_typing_session_id(
                session=session,
                sender_user_id=self.user_a_id,
                partner_user_id=None,
                raw_session_id=str(self.card_session_id),
            )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
