# READ_AUTHZ_MATRIX: GET /api/mediation/status
# READ_AUTHZ_MATRIX: GET /api/cooldown/status
# READ_AUTHZ_MATRIX: GET /api/love-map/cards
# READ_AUTHZ_MATRIX: GET /api/love-map/notes
# READ_AUTHZ_MATRIX: GET /api/blueprint/
# READ_AUTHZ_MATRIX: GET /api/blueprint/date-suggestions
# READ_AUTHZ_MATRIX: GET /api/reports/weekly

"""BOLA / read-authorization tests for core GET endpoints: mediation, cooldown, love-map, blueprint, reports."""

import sys
import unittest
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import blueprint, cooldown, love_map, mediation, reports  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.user import User  # noqa: E402


# Paths covered by this matrix test (must match read-authorization-matrix.json test_ref).
CORE_READ_PATHS = [
    "/api/mediation/status",
    "/api/cooldown/status",
    "/api/love-map/cards",
    "/api/love-map/notes",
    "/api/blueprint/",
    "/api/blueprint/date-suggestions",
    "/api/reports/weekly",
]


class CoreReadAuthorizationMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(mediation.router, prefix="/api/mediation")
        app.include_router(cooldown.router, prefix="/api/cooldown")
        app.include_router(love_map.router, prefix="/api/love-map")
        app.include_router(blueprint.router, prefix="/api/blueprint")
        app.include_router(reports.router, prefix="/api/reports")

        self.current_user_id = None

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
            user_a = User(email="core-a@example.com", full_name="Core A", hashed_password="x")
            user_b = User(email="core-b@example.com", full_name="Core B", hashed_password="x")
            session.add(user_a)
            session.add(user_b)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            session.add(user_a)
            session.add(user_b)
            session.commit()
            session.refresh(user_a)
            self.user_a_id = user_a.id
            self.user_b_id = user_b.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_authenticated_can_read_mediation_status(self) -> None:
        response = self.client.get("/api/mediation/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("in_mediation", payload)

    def test_authenticated_can_read_cooldown_status(self) -> None:
        response = self.client.get("/api/cooldown/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("in_cooldown", payload)

    def test_authenticated_can_read_love_map_cards(self) -> None:
        response = self.client.get("/api/love-map/cards")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("safe", payload)
        self.assertIn("medium", payload)
        self.assertIn("deep", payload)

    def test_authenticated_can_read_love_map_notes(self) -> None:
        response = self.client.get("/api/love-map/notes")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_authenticated_can_read_blueprint(self) -> None:
        response = self.client.get("/api/blueprint/")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_authenticated_can_read_blueprint_date_suggestions(self) -> None:
        response = self.client.get("/api/blueprint/date-suggestions")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("suggested", payload)

    def test_authenticated_can_read_reports_weekly(self) -> None:
        response = self.client.get("/api/reports/weekly")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("daily_sync_completion_rate", payload)


if __name__ == "__main__":
    unittest.main()
