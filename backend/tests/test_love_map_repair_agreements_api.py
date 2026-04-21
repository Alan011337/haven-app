# AUTHZ_MATRIX: PUT /api/love-map/essentials/repair-agreements
# AUTHZ_DENY_MATRIX: PUT /api/love-map/essentials/repair-agreements

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
from app.models.relationship_repair_agreement import RelationshipRepairAgreement  # noqa: E402
from app.models.relationship_repair_agreement_change import RelationshipRepairAgreementChange  # noqa: E402
from app.models.user import User  # noqa: E402


class LoveMapRepairAgreementsApiTests(unittest.TestCase):
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
            alice = User(email="alice-repair@example.com", full_name="Alice", hashed_password="hashed")
            bob = User(email="bob-repair@example.com", full_name="Bob", hashed_password="hashed")
            carol = User(email="carol-repair@example.com", full_name="Carol", hashed_password="hashed")
            dave = User(email="dave-repair@example.com", full_name="Dave", hashed_password="hashed")
            solo = User(email="solo-repair@example.com", full_name="Solo", hashed_password="hashed")
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
            session.add(
                RelationshipRepairAgreement(
                    user_id=min(alice.id, bob.id),
                    partner_id=max(alice.id, bob.id),
                    protect_what_matters="stale pair guidance",
                    avoid_in_conflict="stale avoid",
                    repair_reentry="stale reentry",
                    updated_by_user_id=bob.id,
                )
            )
            session.commit()

            self.alice_id = alice.id
            self.bob_id = bob.id
            self.carol_id = carol.id
            self.dave_id = dave.id
            self.solo_id = solo.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_paired_user_can_upsert_pair_repair_agreements(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.put(
            "/api/love-map/essentials/repair-agreements",
            json={
                "protect_what_matters": "先保護彼此的安全感。",
                "avoid_in_conflict": "不要在最高張力時翻舊帳。",
                "repair_reentry": "先留一點空氣，再在 24 小時內回來。",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["protect_what_matters"], "先保護彼此的安全感。")
        self.assertEqual(payload["avoid_in_conflict"], "不要在最高張力時翻舊帳。")
        self.assertEqual(payload["repair_reentry"], "先留一點空氣，再在 24 小時內回來。")
        self.assertEqual(payload["updated_by_name"], "Alice")
        self.assertIsNotNone(payload["updated_at"])

        with Session(self.engine) as session:
            row = session.exec(
                select(RelationshipRepairAgreement).where(
                    RelationshipRepairAgreement.user_id == min(self.alice_id, self.bob_id),
                    RelationshipRepairAgreement.partner_id == max(self.alice_id, self.bob_id),
                )
            ).first()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.updated_by_user_id, self.alice_id)
            self.assertEqual(row.protect_what_matters, "先保護彼此的安全感。")
            history_rows = session.exec(
                select(RelationshipRepairAgreementChange).where(
                    RelationshipRepairAgreementChange.user_id == min(self.alice_id, self.bob_id),
                    RelationshipRepairAgreementChange.partner_id == max(self.alice_id, self.bob_id),
                )
            ).all()
            self.assertEqual(len(history_rows), 1)
            self.assertEqual(history_rows[0].origin_kind, "manual_edit")
            self.assertEqual(history_rows[0].changed_by_user_id, self.alice_id)
            self.assertEqual(history_rows[0].protect_what_matters_before, "stale pair guidance")
            self.assertEqual(history_rows[0].protect_what_matters_after, "先保護彼此的安全感。")

    def test_no_op_save_does_not_create_history_or_mutate_updated_by(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.put(
            "/api/love-map/essentials/repair-agreements",
            json={
                "protect_what_matters": "stale pair guidance",
                "avoid_in_conflict": "stale avoid",
                "repair_reentry": "stale reentry",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["updated_by_name"], "Bob")

        with Session(self.engine) as session:
            row = session.exec(
                select(RelationshipRepairAgreement).where(
                    RelationshipRepairAgreement.user_id == min(self.alice_id, self.bob_id),
                    RelationshipRepairAgreement.partner_id == max(self.alice_id, self.bob_id),
                )
            ).first()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.updated_by_user_id, self.bob_id)
            history_rows = session.exec(select(RelationshipRepairAgreementChange)).all()
            self.assertEqual(history_rows, [])

    def test_unpaired_user_cannot_upsert_repair_agreements(self) -> None:
        self.current_user_id = self.solo_id

        response = self.client.put(
            "/api/love-map/essentials/repair-agreements",
            json={
                "protect_what_matters": "先保護關係。",
                "avoid_in_conflict": "",
                "repair_reentry": "",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_other_pair_write_does_not_touch_existing_pair_scope(self) -> None:
        self.current_user_id = self.carol_id

        response = self.client.put(
            "/api/love-map/essentials/repair-agreements",
            json={
                "protect_what_matters": "我們先保護彼此在外人面前的體面。",
                "avoid_in_conflict": "不要在半夜繼續升高。",
                "repair_reentry": "隔天早上再回來整理。",
            },
        )

        self.assertEqual(response.status_code, 200)

        with Session(self.engine) as session:
            alice_bob_row = session.exec(
                select(RelationshipRepairAgreement).where(
                    RelationshipRepairAgreement.user_id == min(self.alice_id, self.bob_id),
                    RelationshipRepairAgreement.partner_id == max(self.alice_id, self.bob_id),
                )
            ).first()
            self.assertIsNotNone(alice_bob_row)
            assert alice_bob_row is not None
            self.assertEqual(alice_bob_row.protect_what_matters, "stale pair guidance")

            carol_dave_row = session.exec(
                select(RelationshipRepairAgreement).where(
                    RelationshipRepairAgreement.user_id == min(self.carol_id, self.dave_id),
                    RelationshipRepairAgreement.partner_id == max(self.carol_id, self.dave_id),
                )
            ).first()
            self.assertIsNotNone(carol_dave_row)
            assert carol_dave_row is not None
            self.assertEqual(carol_dave_row.updated_by_user_id, self.carol_id)
            self.assertEqual(
                carol_dave_row.protect_what_matters,
                "我們先保護彼此在外人面前的體面。",
            )


    def test_upsert_repair_agreements_persists_revision_note(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.put(
            "/api/love-map/essentials/repair-agreements",
            json={
                "protect_what_matters": "stale pair guidance",
                "avoid_in_conflict": "stale avoid",
                "repair_reentry": "先留一點空氣，再在 24 小時內回來。",
                "revision_note": "我們在週二散步後聊出的版本。",
            },
        )

        self.assertEqual(response.status_code, 200)

        with Session(self.engine) as session:
            history_rows = session.exec(
                select(RelationshipRepairAgreementChange).where(
                    RelationshipRepairAgreementChange.user_id == min(self.alice_id, self.bob_id),
                    RelationshipRepairAgreementChange.partner_id == max(self.alice_id, self.bob_id),
                )
            ).all()
            self.assertEqual(len(history_rows), 1)
            self.assertEqual(history_rows[0].revision_note, "我們在週二散步後聊出的版本。")

        system_response = self.client.get("/api/love-map/system")
        self.assertEqual(system_response.status_code, 200)
        essentials = system_response.json()["essentials"]
        history = essentials["repair_agreement_history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["revision_note"], "我們在週二散步後聊出的版本。")

    def test_upsert_repair_agreements_without_note_stores_null(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.put(
            "/api/love-map/essentials/repair-agreements",
            json={
                "protect_what_matters": "stale pair guidance",
                "avoid_in_conflict": "stale avoid",
                "repair_reentry": "只改 reentry，但不留註記。",
            },
        )

        self.assertEqual(response.status_code, 200)

        with Session(self.engine) as session:
            history_rows = session.exec(
                select(RelationshipRepairAgreementChange).where(
                    RelationshipRepairAgreementChange.user_id == min(self.alice_id, self.bob_id),
                    RelationshipRepairAgreementChange.partner_id == max(self.alice_id, self.bob_id),
                )
            ).all()
            self.assertEqual(len(history_rows), 1)
            self.assertIsNone(history_rows[0].revision_note)

        system_response = self.client.get("/api/love-map/system")
        self.assertEqual(system_response.status_code, 200)
        history = system_response.json()["essentials"]["repair_agreement_history"]
        self.assertEqual(len(history), 1)
        self.assertIsNone(history[0]["revision_note"])

    def test_upsert_repair_agreements_whitespace_note_is_normalized_null(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.put(
            "/api/love-map/essentials/repair-agreements",
            json={
                "protect_what_matters": "stale pair guidance",
                "avoid_in_conflict": "stale avoid",
                "repair_reentry": "只想試試空白註記。",
                "revision_note": "   \u3000\n  ",
            },
        )

        self.assertEqual(response.status_code, 200)

        with Session(self.engine) as session:
            history_rows = session.exec(
                select(RelationshipRepairAgreementChange).where(
                    RelationshipRepairAgreementChange.user_id == min(self.alice_id, self.bob_id),
                    RelationshipRepairAgreementChange.partner_id == max(self.alice_id, self.bob_id),
                )
            ).all()
            self.assertEqual(len(history_rows), 1)
            self.assertIsNone(history_rows[0].revision_note)


if __name__ == "__main__":
    unittest.main()
