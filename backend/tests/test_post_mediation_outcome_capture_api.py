# AUTHZ_MATRIX: POST /api/love-map/essentials/repair-outcome-captures/{capture_id}/dismiss
# AUTHZ_DENY_MATRIX: POST /api/love-map/essentials/repair-outcome-captures/{capture_id}/dismiss

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
from app.api.routers import love_map, mediation  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.relationship_repair_agreement import RelationshipRepairAgreement  # noqa: E402
from app.models.relationship_repair_agreement_change import RelationshipRepairAgreementChange  # noqa: E402
from app.models.relationship_repair_outcome_capture import (  # noqa: E402
    RelationshipRepairOutcomeCapture,
)
from app.models.user import User  # noqa: E402


class PostMediationOutcomeCaptureApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(mediation.router, prefix="/api/mediation")
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
            alice = User(email="alice-capture@example.com", full_name="Alice", hashed_password="hashed")
            bob = User(email="bob-capture@example.com", full_name="Bob", hashed_password="hashed")
            carol = User(email="carol-capture@example.com", full_name="Carol", hashed_password="hashed")
            dave = User(email="dave-capture@example.com", full_name="Dave", hashed_password="hashed")
            session.add(alice)
            session.add(bob)
            session.add(carol)
            session.add(dave)
            session.commit()
            session.refresh(alice)
            session.refresh(bob)
            session.refresh(carol)
            session.refresh(dave)

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

        self.original_feature_flags = settings.FEATURE_FLAGS_JSON
        self.original_feature_kills = settings.FEATURE_KILL_SWITCHES_JSON
        settings.FEATURE_FLAGS_JSON = '{"repair_flow_v1": true}'
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_repair_flow_v1": false}'

    def tearDown(self) -> None:
        settings.FEATURE_FLAGS_JSON = self.original_feature_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_feature_kills
        self.client.close()
        self.engine.dispose()

    def _start_flow_for_alice(self) -> str:
        self.current_user_id = self.alice_id
        response = self.client.post("/api/mediation/repair/start", json={})
        self.assertEqual(response.status_code, 200)
        return response.json()["session_id"]

    def _complete_step(
        self,
        *,
        user_id: uuid.UUID,
        session_id: str,
        step: int,
        payload: dict[str, str] | None = None,
    ) -> None:
        self.current_user_id = user_id
        body = {
            "session_id": session_id,
            "step": step,
        }
        if payload:
            body.update(payload)
        response = self.client.post("/api/mediation/repair/step-complete", json=body)
        self.assertEqual(response.status_code, 200)

    def _create_pending_capture(self) -> tuple[str, str]:
        session_id = self._start_flow_for_alice()
        self._complete_step(
            user_id=self.alice_id,
            session_id=session_id,
            step=2,
            payload={"i_feel": "我很受傷", "i_need": "先被聽完"},
        )
        self._complete_step(
            user_id=self.bob_id,
            session_id=session_id,
            step=2,
            payload={"i_feel": "我也很挫折", "i_need": "先不要被打斷"},
        )
        self._complete_step(
            user_id=self.alice_id,
            session_id=session_id,
            step=3,
            payload={"mirror_text": "我聽見你是想先被聽完。"},
        )
        self._complete_step(
            user_id=self.bob_id,
            session_id=session_id,
            step=3,
            payload={"mirror_text": "我聽見你需要我先慢下來。"},
        )
        self._complete_step(
            user_id=self.alice_id,
            session_id=session_id,
            step=4,
            payload={"shared_commitment": "今晚先散步十分鐘，再回來把需要說清楚。"},
        )
        self._complete_step(
            user_id=self.bob_id,
            session_id=session_id,
            step=4,
            payload={"shared_commitment": "今晚先散步十分鐘，再回來用比較慢的語氣說清楚。"},
        )
        self._complete_step(
            user_id=self.alice_id,
            session_id=session_id,
            step=5,
            payload={"improvement_note": "我這次有先把你的句子聽完。"},
        )
        self.current_user_id = self.bob_id
        final_step = self.client.post(
            "/api/mediation/repair/step-complete",
            json={
                "session_id": session_id,
                "step": 5,
                "improvement_note": "我們這次有先降溫，再回來把承諾說清楚。",
            },
        )
        self.assertEqual(final_step.status_code, 200)
        self.assertTrue(final_step.json()["completed"])

        system_response = self.client.get("/api/love-map/system")
        self.assertEqual(system_response.status_code, 200)
        capture_id = system_response.json()["essentials"]["pending_repair_outcome_capture"]["id"]
        return session_id, capture_id

    def test_completed_repair_flow_exposes_pending_capture_in_status_and_love_map_system(self) -> None:
        session_id, _capture_id = self._create_pending_capture()

        self.current_user_id = self.bob_id
        status_response = self.client.get(
            "/api/mediation/repair/status",
            params={"session_id": session_id},
        )
        self.assertEqual(status_response.status_code, 200)
        status_payload = status_response.json()
        self.assertTrue(status_payload["completed"])
        self.assertTrue(status_payload["outcome_capture_pending"])

        self.current_user_id = self.alice_id
        system_response = self.client.get("/api/love-map/system")
        self.assertEqual(system_response.status_code, 200)
        pending_capture = system_response.json()["essentials"]["pending_repair_outcome_capture"]
        self.assertIsNotNone(pending_capture)
        self.assertEqual(
            pending_capture["shared_commitment"],
            "今晚先散步十分鐘，再回來用比較慢的語氣說清楚。",
        )
        self.assertEqual(
            pending_capture["improvement_note"],
            "我們這次有先降溫，再回來把承諾說清楚。",
        )
        self.assertEqual(pending_capture["captured_by_name"], "Bob")
        self.assertEqual(pending_capture["status"], "pending")

    def test_saving_repair_agreements_with_source_capture_marks_capture_applied(self) -> None:
        _session_id, capture_id = self._create_pending_capture()

        self.current_user_id = self.alice_id
        response = self.client.put(
            "/api/love-map/essentials/repair-agreements",
            json={
                "protect_what_matters": "先保護彼此仍想站在同一邊這件事。",
                "avoid_in_conflict": "不要在最高張力時逼對方立刻回答。",
                "repair_reentry": "今晚先散步十分鐘，再回來用比較慢的語氣說清楚。",
                "source_outcome_capture_id": capture_id,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["updated_by_name"], "Alice")
        self.assertEqual(
            payload["repair_reentry"],
            "今晚先散步十分鐘，再回來用比較慢的語氣說清楚。",
        )

        system_response = self.client.get("/api/love-map/system")
        self.assertEqual(system_response.status_code, 200)
        essentials = system_response.json()["essentials"]
        self.assertIsNone(essentials["pending_repair_outcome_capture"])
        self.assertIsNotNone(essentials["repair_agreements"])

        with Session(self.engine) as session:
            capture_row = session.get(RelationshipRepairOutcomeCapture, uuid.UUID(capture_id))
            self.assertIsNotNone(capture_row)
            assert capture_row is not None
            self.assertEqual(capture_row.status, "applied")
            self.assertEqual(capture_row.reviewed_by_user_id, self.alice_id)

            agreement_row = session.exec(
                select(RelationshipRepairAgreement).where(
                    RelationshipRepairAgreement.user_id == min(self.alice_id, self.bob_id),
                    RelationshipRepairAgreement.partner_id == max(self.alice_id, self.bob_id),
                )
            ).first()
            self.assertIsNotNone(agreement_row)
            assert agreement_row is not None
            self.assertEqual(agreement_row.updated_by_user_id, self.alice_id)
            history_rows = session.exec(
                select(RelationshipRepairAgreementChange).where(
                    RelationshipRepairAgreementChange.user_id == min(self.alice_id, self.bob_id),
                    RelationshipRepairAgreementChange.partner_id == max(self.alice_id, self.bob_id),
                )
            ).all()
            self.assertEqual(len(history_rows), 1)
            self.assertEqual(history_rows[0].origin_kind, "post_mediation_carry_forward")
            self.assertEqual(history_rows[0].source_outcome_capture_id, uuid.UUID(capture_id))
            self.assertEqual(history_rows[0].source_captured_by_user_id, self.bob_id)
            self.assertEqual(
                history_rows[0].repair_reentry_after,
                "今晚先散步十分鐘，再回來用比較慢的語氣說清楚。",
            )

    def test_pair_user_can_dismiss_pending_capture(self) -> None:
        _session_id, capture_id = self._create_pending_capture()

        self.current_user_id = self.alice_id
        response = self.client.post(
            f"/api/love-map/essentials/repair-outcome-captures/{capture_id}/dismiss"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "dismissed")

        system_response = self.client.get("/api/love-map/system")
        self.assertEqual(system_response.status_code, 200)
        self.assertIsNone(system_response.json()["essentials"]["pending_repair_outcome_capture"])

    def test_other_pair_cannot_apply_or_dismiss_pending_capture(self) -> None:
        _session_id, capture_id = self._create_pending_capture()

        self.current_user_id = self.carol_id
        dismiss_response = self.client.post(
            f"/api/love-map/essentials/repair-outcome-captures/{capture_id}/dismiss"
        )
        self.assertEqual(dismiss_response.status_code, 404)

        apply_response = self.client.put(
            "/api/love-map/essentials/repair-agreements",
            json={
                "protect_what_matters": "我們先停下來。",
                "avoid_in_conflict": "不要一直升高。",
                "repair_reentry": "明天再說。",
                "source_outcome_capture_id": capture_id,
            },
        )
        self.assertEqual(apply_response.status_code, 404)

        with Session(self.engine) as session:
            capture_row = session.get(RelationshipRepairOutcomeCapture, uuid.UUID(capture_id))
            self.assertIsNotNone(capture_row)
            assert capture_row is not None
            self.assertEqual(capture_row.status, "pending")


if __name__ == "__main__":
    unittest.main()
