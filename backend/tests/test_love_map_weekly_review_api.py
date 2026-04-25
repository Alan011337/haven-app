# AUTHZ_MATRIX: GET /api/love-map/weekly-review/current
# AUTHZ_MATRIX: PUT /api/love-map/weekly-review/current
# AUTHZ_DENY_MATRIX: GET /api/love-map/weekly-review/current
# AUTHZ_DENY_MATRIX: PUT /api/love-map/weekly-review/current

import sys
import unittest
import uuid
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
from app.api.routers import love_map  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.relationship_weekly_review import RelationshipWeeklyReview  # noqa: E402
from app.models.user import User  # noqa: E402


class LoveMapWeeklyReviewApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(love_map.router, prefix="/api/love-map")

        self.current_user_id: uuid.UUID | None = None

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        def override_get_current_user() -> User:
            if self.current_user_id is None:
                raise RuntimeError("current_user_id not set")
            with Session(self.engine) as session:
                user = session.get(User, self.current_user_id)
                if not user:
                    raise RuntimeError("user not found")
                return user

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

        with Session(self.engine) as session:
            alice = User(email="alice-weekly@example.com", full_name="Alice", hashed_password="hashed")
            bob = User(email="bob-weekly@example.com", full_name="Bob", hashed_password="hashed")
            carol = User(email="carol-weekly@example.com", full_name="Carol", hashed_password="hashed")
            dave = User(email="dave-weekly@example.com", full_name="Dave", hashed_password="hashed")
            solo = User(email="solo-weekly@example.com", full_name="Solo", hashed_password="hashed")
            session.add(alice)
            session.add(bob)
            session.add(carol)
            session.add(dave)
            session.add(solo)
            session.commit()
            session.refresh(alice)
            session.refresh(bob)
            session.refresh(carol)
            session.refresh(dave)
            session.refresh(solo)

            alice.partner_id = bob.id
            bob.partner_id = alice.id
            carol.partner_id = dave.id
            dave.partner_id = carol.id
            session.add(alice)
            session.add(bob)
            session.add(carol)
            session.add(dave)
            session.commit()

            self.alice_id = alice.id
            self.bob_id = bob.id
            self.carol_id = carol.id
            self.dave_id = dave.id
            self.solo_id = solo.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_unpaired_user_is_denied(self) -> None:
        self.current_user_id = self.solo_id
        res = self.client.get("/api/love-map/weekly-review/current")
        self.assertEqual(res.status_code, 403)
        res2 = self.client.put(
            "/api/love-map/weekly-review/current",
            json={
                "understood_this_week": "x",
                "worth_carrying_forward": "",
                "needs_care": "",
                "next_week_intention": "",
            },
        )
        self.assertEqual(res2.status_code, 403)

    def test_get_returns_empty_shape_when_no_row_exists(self) -> None:
        self.current_user_id = self.alice_id
        res = self.client.get("/api/love-map/weekly-review/current")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertIsInstance(payload.get("week_start"), str)
        self.assertEqual(payload["my_answers"], {
            "understood_this_week": None,
            "worth_carrying_forward": None,
            "needs_care": None,
            "next_week_intention": None,
        })
        self.assertEqual(payload["partner_answers"], {
            "understood_this_week": None,
            "worth_carrying_forward": None,
            "needs_care": None,
            "next_week_intention": None,
        })

    def test_each_partner_can_upsert_only_their_half(self) -> None:
        # Alice writes her half.
        self.current_user_id = self.alice_id
        res = self.client.put(
            "/api/love-map/weekly-review/current",
            json={
                "understood_this_week": "我更理解你需要先慢下來。",
                "worth_carrying_forward": "晚餐後散步。",
                "needs_care": "週三那次語氣太急。",
                "next_week_intention": "下週一起練習先問需要。",
            },
        )
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload["my_answers"]["worth_carrying_forward"], "晚餐後散步。")
        self.assertIsNotNone(payload["my_updated_at"])
        self.assertIsNone(payload["partner_updated_at"])

        # Bob sees Alice in partner half, and his own half still empty.
        self.current_user_id = self.bob_id
        res2 = self.client.get("/api/love-map/weekly-review/current")
        self.assertEqual(res2.status_code, 200)
        payload2 = res2.json()
        self.assertEqual(payload2["partner_answers"]["worth_carrying_forward"], "晚餐後散步。")
        self.assertIsNone(payload2["my_answers"]["worth_carrying_forward"])

        # Bob writes; should not overwrite Alice.
        res3 = self.client.put(
            "/api/love-map/weekly-review/current",
            json={
                "understood_this_week": "我更理解你在忙時會先縮起來。",
                "worth_carrying_forward": "那次你先抱我一下。",
                "needs_care": "週五的誤會要補談。",
                "next_week_intention": "下週固定留一晚散步。",
            },
        )
        self.assertEqual(res3.status_code, 200)
        payload3 = res3.json()
        self.assertEqual(payload3["my_answers"]["worth_carrying_forward"], "那次你先抱我一下。")
        self.assertIsNotNone(payload3["my_updated_at"])
        self.assertIsNotNone(payload3["partner_updated_at"])

        # Alice reads back: her half preserved; partner half present.
        self.current_user_id = self.alice_id
        res4 = self.client.get("/api/love-map/weekly-review/current")
        self.assertEqual(res4.status_code, 200)
        payload4 = res4.json()
        self.assertEqual(payload4["my_answers"]["worth_carrying_forward"], "晚餐後散步。")
        self.assertEqual(payload4["partner_answers"]["worth_carrying_forward"], "那次你先抱我一下。")

        # DB: exactly one row for the pair/week.
        with Session(self.engine) as session:
            rows = session.exec(select(RelationshipWeeklyReview)).all()
            self.assertEqual(len(rows), 1)

    def test_other_pair_cannot_read_or_write_this_pairs_review(self) -> None:
        # Carol/Dave are paired, but should not see Alice/Bob review.
        self.current_user_id = self.alice_id
        self.client.put(
            "/api/love-map/weekly-review/current",
            json={
                "understood_this_week": "a",
                "worth_carrying_forward": "b",
                "needs_care": "c",
                "next_week_intention": "d",
            },
        )

        self.current_user_id = self.carol_id
        res = self.client.get("/api/love-map/weekly-review/current")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        # Carol sees her own pair's empty state, not Alice/Bob content.
        self.assertIsNone(payload["partner_answers"]["worth_carrying_forward"])
        self.assertIsNone(payload["my_answers"]["worth_carrying_forward"])

        res2 = self.client.put(
            "/api/love-map/weekly-review/current",
            json={
                "understood_this_week": "carol",
                "worth_carrying_forward": "",
                "needs_care": "",
                "next_week_intention": "",
            },
        )
        self.assertEqual(res2.status_code, 200)

