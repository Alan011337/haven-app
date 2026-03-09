from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path
from typing import Generator
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import main as main_module  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.api_idempotency_record import ApiIdempotencyRecord  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.rate_limit import reset_rate_limit_state_for_tests  # noqa: E402


class ApiIdempotencyPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_rate_limit_state_for_tests()
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        self.engine_patch = patch.object(main_module, "engine", self.engine)
        self.engine_patch.start()
        main_module.app.dependency_overrides[get_session] = override_get_session
        self.client = TestClient(main_module.app)

    def tearDown(self) -> None:
        self.client.close()
        main_module.app.dependency_overrides.pop(get_session, None)
        self.engine_patch.stop()
        self.engine.dispose()
        reset_rate_limit_state_for_tests()

    def _user_payload(self, *, email: str) -> dict:
        return {
            "email": email,
            "full_name": "Idempotency User",
            "password": "VeryStrongPass123!",
            "age_confirmed": True,
            "agreed_to_terms": True,
            "birth_year": 1995,
            "terms_version": "2026-03-01",
            "privacy_version": "2026-03-01",
        }

    def test_replays_same_response_for_same_key_and_payload(self) -> None:
        token = uuid.uuid4().hex[:10]
        email = f"idem-replay-{token}@example.com"
        payload = self._user_payload(email=email)
        headers = {"Idempotency-Key": f"idem-{uuid.uuid4().hex}"}

        first = self.client.post("/api/users/", json=payload, headers=headers)
        self.assertLess(first.status_code, 500)
        second = self.client.post("/api/users/", json=payload, headers=headers)
        self.assertEqual(second.status_code, first.status_code)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(second.headers.get("X-Idempotency-Replayed"), "true")

        with Session(self.engine) as session:
            user_rows = session.exec(select(User).where(User.email == email)).all()
            idem_rows = session.exec(
                select(ApiIdempotencyRecord).where(
                    ApiIdempotencyRecord.idempotency_key == headers["Idempotency-Key"]
                )
            ).all()
        self.assertEqual(len(user_rows), 1)
        self.assertGreaterEqual(len(idem_rows), 1)

    def test_rejects_payload_mismatch_for_same_key(self) -> None:
        key = f"idem-{uuid.uuid4().hex}"
        first_payload = self._user_payload(email=f"idem-mismatch-a-{uuid.uuid4().hex[:8]}@example.com")
        second_payload = self._user_payload(email=f"idem-mismatch-b-{uuid.uuid4().hex[:8]}@example.com")
        headers = {"Idempotency-Key": key}

        first = self.client.post("/api/users/", json=first_payload, headers=headers)
        self.assertLess(first.status_code, 500)
        second = self.client.post("/api/users/", json=second_payload, headers=headers)
        self.assertEqual(second.status_code, 409)
        body = second.json()
        self.assertEqual(body.get("error", {}).get("code"), "idempotency_payload_mismatch")

    def test_skips_idempotency_replay_for_large_payload(self) -> None:
        token = uuid.uuid4().hex[:10]
        email = f"idem-large-{token}@example.com"
        payload = self._user_payload(email=email)
        payload["full_name"] = "x" * 400
        headers = {"Idempotency-Key": f"idem-{uuid.uuid4().hex}"}

        with patch.object(main_module, "max_request_body_bytes", return_value=1):
            first = self.client.post("/api/users/", json=payload, headers=headers)
            self.assertEqual(first.status_code, 200, first.text)
            self.assertEqual(first.headers.get("X-Idempotency-Skipped"), "request_too_large")

            second = self.client.post("/api/users/", json=payload, headers=headers)
            self.assertEqual(second.status_code, 409, second.text)
            self.assertEqual(second.headers.get("X-Idempotency-Replayed"), None)
            self.assertEqual(second.headers.get("X-Idempotency-Skipped"), "request_too_large")


if __name__ == "__main__":
    unittest.main()
