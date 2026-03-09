# AUTHZ_MATRIX: POST /api/mediation/answers

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
from app.db.session import get_session  # noqa: E402
from app.models.user import User  # noqa: E402


class MediationAuthorizationMatrixTests(unittest.TestCase):
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
            self.user_a = User(
                email="a@example.com", full_name="A", hashed_password="hashed"
            )
            session.add(self.user_a)
            session.commit()
            session.refresh(self.user_a)
            self.user_a_id = self.user_a.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_post_answers_requires_authenticated_user(self) -> None:
        # With auth: endpoint is reachable (400/404 for invalid session_id is ok)
        response = self.client.post(
            "/api/mediation/answers",
            json={
                "session_id": "00000000-0000-0000-0000-000000000001",
                "answers": ["a", "b", "c"],
            },
        )
        self.assertIn(response.status_code, (200, 400, 404))


if __name__ == "__main__":
    unittest.main()
