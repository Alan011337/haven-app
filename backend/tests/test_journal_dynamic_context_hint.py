import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.journals import _resolve_relationship_weather_hint  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402


class JournalDynamicContextHintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.original_dynamic_context_flag = settings.AI_DYNAMIC_CONTEXT_INJECTION_ENABLED
        settings.AI_DYNAMIC_CONTEXT_INJECTION_ENABLED = True

        now = utcnow()
        with Session(self.engine) as session:
            user_a = User(
                email="ctx-a@example.com",
                full_name="Ctx A",
                hashed_password="hashed",
                terms_accepted_at=now - timedelta(days=10),
            )
            user_b = User(
                email="ctx-b@example.com",
                full_name="Ctx B",
                hashed_password="hashed",
                terms_accepted_at=now - timedelta(days=10),
            )
            session.add(user_a)
            session.add(user_b)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            self.user_a_id = user_a.id
            self.user_b_id = user_b.id

    def tearDown(self) -> None:
        settings.AI_DYNAMIC_CONTEXT_INJECTION_ENABLED = self.original_dynamic_context_flag
        self.engine.dispose()

    def _add_journal(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        content: str,
        created_at_offset_hours: int,
    ) -> None:
        session.add(
            Journal(
                user_id=user_id,
                content=content,
                created_at=utcnow() - timedelta(hours=created_at_offset_hours),
            )
        )

    def test_hint_returns_conflict_when_conflict_signals_dominate_recent_window(self) -> None:
        with Session(self.engine) as session:
            self._add_journal(
                session=session,
                user_id=self.user_a_id,
                content="我們昨天吵架，我很生氣。",
                created_at_offset_hours=6,
            )
            self._add_journal(
                session=session,
                user_id=self.user_b_id,
                content="有點冷戰，彼此忽略。",
                created_at_offset_hours=4,
            )
            self._add_journal(
                session=session,
                user_id=self.user_a_id,
                content="今天普通。",
                created_at_offset_hours=2,
            )
            session.commit()

            hint = _resolve_relationship_weather_hint(
                session=session,
                current_user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
            )

        self.assertEqual(hint, "conflict")

    def test_hint_returns_repair_when_repair_signals_dominate_recent_window(self) -> None:
        with Session(self.engine) as session:
            self._add_journal(
                session=session,
                user_id=self.user_a_id,
                content="今天很感謝你，我很開心。",
                created_at_offset_hours=3,
            )
            self._add_journal(
                session=session,
                user_id=self.user_b_id,
                content="被支持，覺得幸福。",
                created_at_offset_hours=1,
            )
            session.commit()

            hint = _resolve_relationship_weather_hint(
                session=session,
                current_user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
            )

        self.assertEqual(hint, "repair")

    def test_hint_ignores_stale_activity_outside_lookback_window(self) -> None:
        with Session(self.engine) as session:
            self._add_journal(
                session=session,
                user_id=self.user_a_id,
                content="昨天吵架，我很崩潰。",
                created_at_offset_hours=72,
            )
            session.commit()

            hint = _resolve_relationship_weather_hint(
                session=session,
                current_user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
            )

        self.assertIsNone(hint)

    def test_hint_returns_none_when_feature_flag_disabled(self) -> None:
        settings.AI_DYNAMIC_CONTEXT_INJECTION_ENABLED = False
        with Session(self.engine) as session:
            self._add_journal(
                session=session,
                user_id=self.user_a_id,
                content="我們昨天吵架。",
                created_at_offset_hours=2,
            )
            session.commit()

            hint = _resolve_relationship_weather_hint(
                session=session,
                current_user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
            )

        self.assertIsNone(hint)


if __name__ == "__main__":
    unittest.main()
