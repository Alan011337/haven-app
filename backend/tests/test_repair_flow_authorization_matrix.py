# AUTHZ_MATRIX: POST /api/mediation/repair/start
# AUTHZ_MATRIX: POST /api/mediation/repair/step-complete
# READ_AUTHZ_MATRIX: GET /api/mediation/repair/status

import sys
import unittest
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import mediation  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.user import User  # noqa: E402


class RepairFlowAuthorizationMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(mediation.router, prefix="/api/mediation")

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
            user_a = User(email="repair-a@example.com", full_name="A", hashed_password="hashed")
            user_b = User(email="repair-b@example.com", full_name="B", hashed_password="hashed")
            user_c = User(email="repair-c@example.com", full_name="C", hashed_password="hashed")
            user_d = User(email="repair-d@example.com", full_name="D", hashed_password="hashed")
            session.add(user_a)
            session.add(user_b)
            session.add(user_c)
            session.add(user_d)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(user_c)
            session.refresh(user_d)

            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            user_c.partner_id = user_d.id
            user_d.partner_id = user_c.id
            session.add(user_a)
            session.add(user_b)
            session.add(user_c)
            session.add(user_d)
            session.commit()

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.user_c_id = user_c.id

        self.original_feature_flags = settings.FEATURE_FLAGS_JSON
        self.original_feature_kills = settings.FEATURE_KILL_SWITCHES_JSON
        settings.FEATURE_FLAGS_JSON = '{"repair_flow_v1": true}'
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_repair_flow_v1": false}'
        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        settings.FEATURE_FLAGS_JSON = self.original_feature_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_feature_kills
        self.client.close()
        self.engine.dispose()

    def test_partner_pair_can_start_and_progress_repair_flow(self) -> None:
        start = self.client.post("/api/mediation/repair/start", json={})
        self.assertEqual(start.status_code, 200)
        session_id = start.json()["session_id"]

        step_by_owner = self.client.post(
            "/api/mediation/repair/step-complete",
            json={"session_id": session_id, "step": 2, "i_feel": "受傷", "i_need": "被理解"},
        )
        self.assertEqual(step_by_owner.status_code, 200)
        self.assertTrue(step_by_owner.json()["accepted"])

        self.current_user_id = self.user_b_id
        step_by_partner = self.client.post(
            "/api/mediation/repair/step-complete",
            json={"session_id": session_id, "step": 2, "i_feel": "焦慮", "i_need": "被傾聽"},
        )
        self.assertEqual(step_by_partner.status_code, 200)
        self.assertTrue(step_by_partner.json()["accepted"])

    def test_stranger_pair_cannot_progress_other_session(self) -> None:
        start = self.client.post("/api/mediation/repair/start", json={})
        self.assertEqual(start.status_code, 200)
        session_id = start.json()["session_id"]

        self.current_user_id = self.user_c_id
        denied = self.client.post(
            "/api/mediation/repair/step-complete",
            json={"session_id": session_id, "step": 2, "i_feel": "x", "i_need": "y"},
        )
        self.assertEqual(denied.status_code, 404)

    def test_repair_flow_status_is_pair_scoped(self) -> None:
        start = self.client.post("/api/mediation/repair/start", json={})
        self.assertEqual(start.status_code, 200)
        session_id = start.json()["session_id"]

        self.current_user_id = self.user_b_id
        partner_view = self.client.get(
            "/api/mediation/repair/status",
            params={"session_id": session_id},
        )
        self.assertEqual(partner_view.status_code, 200)
        self.assertEqual(partner_view.json()["session_id"], session_id)

        self.current_user_id = self.user_c_id
        stranger_view = self.client.get(
            "/api/mediation/repair/status",
            params={"session_id": session_id},
        )
        self.assertEqual(stranger_view.status_code, 404)

    def test_repair_flow_disabled_returns_not_found(self) -> None:
        settings.FEATURE_FLAGS_JSON = '{"repair_flow_v1": false}'
        denied = self.client.post("/api/mediation/repair/start", json={})
        self.assertEqual(denied.status_code, 404)


if __name__ == "__main__":
    unittest.main()
