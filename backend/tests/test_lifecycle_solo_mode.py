from __future__ import annotations

import sys
import unittest
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.user import User  # noqa: E402
from app.services.lifecycle_solo_mode import resolve_user_mode, transition_to_solo_mode  # noqa: E402


class LifecycleSoloModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            user_a = User(email="a@example.com", hashed_password="hashed")
            user_b = User(email="b@example.com", hashed_password="hashed")
            user_c = User(email="c@example.com", hashed_password="hashed")
            session.add(user_a)
            session.add(user_b)
            session.add(user_c)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(user_c)

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.user_c_id = user_c.id

            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            session.add(user_a)
            session.add(user_b)
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_resolve_user_mode_returns_paired_for_valid_bidirectional_pair(self) -> None:
        with Session(self.engine) as session:
            mode = resolve_user_mode(session=session, user_id=self.user_a_id)
        self.assertEqual(mode["mode"], "paired")
        self.assertEqual(mode["features"]["ai_prompt_mode"], "couple")

    def test_resolve_user_mode_returns_solo_for_unpaired_user(self) -> None:
        with Session(self.engine) as session:
            mode = resolve_user_mode(session=session, user_id=self.user_c_id)
        self.assertEqual(mode["mode"], "solo")
        self.assertFalse(mode["features"]["partner_ui_visible"])

    def test_transition_to_solo_mode_after_unbind_returns_ok(self) -> None:
        with Session(self.engine) as session:
            a = session.get(User, self.user_a_id)
            b = session.get(User, self.user_b_id)
            assert a is not None
            assert b is not None
            a.partner_id = None
            b.partner_id = None
            session.add(a)
            session.add(b)
            session.commit()

            result = transition_to_solo_mode(session=session, user_id=self.user_a_id)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data_preserved"])
        self.assertEqual(result["mode"], "solo")


if __name__ == "__main__":
    unittest.main()
