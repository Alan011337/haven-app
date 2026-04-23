# AUTHZ_MATRIX: POST /api/appreciations
# AUTHZ_MATRIX: POST /api/auth/logout
# AUTHZ_MATRIX: POST /api/baseline
# AUTHZ_MATRIX: POST /api/blueprint/
# AUTHZ_MATRIX: POST /api/cooldown/rewrite-message
# AUTHZ_MATRIX: POST /api/cooldown/start
# AUTHZ_MATRIX: POST /api/couple-goal
# AUTHZ_MATRIX: POST /api/daily-sync
# AUTHZ_MATRIX: PUT /api/love-languages/preference
# AUTHZ_MATRIX: POST /api/love-languages/weekly-task/complete
# AUTHZ_MATRIX: PUT /api/love-map/identity/compass
# AUTHZ_MATRIX: PUT /api/love-map/essentials/heart-profile
# AUTHZ_MATRIX: PUT /api/love-map/essentials/repair-agreements
# AUTHZ_MATRIX: POST /api/love-map/essentials/repair-outcome-captures/{capture_id}/dismiss
# AUTHZ_MATRIX: POST /api/love-map/notes
# AUTHZ_MATRIX: POST /api/love-map/suggestions/shared-future/generate
# AUTHZ_MATRIX: POST /api/love-map/suggestions/shared-future/generate-story-ritual
# AUTHZ_MATRIX: POST /api/love-map/suggestions/shared-future/refinements/{wishlist_item_id}/generate
# AUTHZ_MATRIX: POST /api/love-map/suggestions/shared-future/refinements/{wishlist_item_id}/generate-cadence
# AUTHZ_MATRIX: POST /api/love-map/suggestions/{suggestion_id}/accept
# AUTHZ_MATRIX: POST /api/love-map/suggestions/{suggestion_id}/dismiss
# AUTHZ_MATRIX: PUT /api/love-map/notes/{note_id}
# AUTHZ_MATRIX: POST /api/users/me/onboarding-consent
# AUTHZ_DENY_MATRIX: PUT /api/love-map/notes/{note_id}

import sys
import unittest
import uuid
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api import login  # noqa: E402
from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import (  # noqa: E402
    appreciations,
    baseline,
    blueprint,
    cooldown,
    daily_sync,
    love_language,
    love_map,
    users,
)
from app.db.session import get_session  # noqa: E402
from app.models.love_map_note import LoveMapNote  # noqa: E402
from app.models.user import User  # noqa: E402


class PlatformMutatingAuthRequirementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(appreciations.router, prefix="/api/appreciations")
        app.include_router(login.router, prefix="/api/auth")
        app.include_router(baseline.baseline_router, prefix="/api/baseline")
        app.include_router(baseline.couple_goal_router, prefix="/api/couple-goal")
        app.include_router(blueprint.router, prefix="/api/blueprint")
        app.include_router(cooldown.router, prefix="/api/cooldown")
        app.include_router(daily_sync.router, prefix="/api/daily-sync")
        app.include_router(love_language.router, prefix="/api/love-languages")
        app.include_router(love_map.router, prefix="/api/love-map")
        app.include_router(users.router, prefix="/api/users")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_logout_remains_public(self) -> None:
        response = self.client.post("/api/auth/logout")
        self.assertEqual(response.status_code, 200)

    def test_mutating_endpoints_require_authentication(self) -> None:
        cases = [
            ("POST", "/api/appreciations", {"body_text": "thanks"}),
            (
                "POST",
                "/api/baseline",
                {
                    "scores": {
                        "intimacy": 4,
                        "conflict": 2,
                        "trust": 4,
                        "communication": 5,
                        "commitment": 4,
                    }
                },
            ),
            ("POST", "/api/blueprint/", {"title": "Weekend walk", "notes": "River side"}),
            ("POST", "/api/cooldown/rewrite-message", {"message": "I am upset"}),
            ("POST", "/api/cooldown/start", {"duration_minutes": 20}),
            ("POST", "/api/couple-goal", {"goal_slug": "more_trust"}),
            ("POST", "/api/daily-sync", {"mood_score": 3, "question_id": "q0", "answer_text": "check-in"}),
            ("PUT", "/api/love-languages/preference", {"preference": {"primary": "words", "secondary": "time"}}),
            ("POST", "/api/love-languages/weekly-task/complete", None),
            (
                "PUT",
                "/api/love-map/identity/compass",
                {
                    "identity_statement": "我們是在忙裡仍願意回來對話的伴侶。",
                    "story_anchor": "想一起記得那些有走回彼此的時刻。",
                    "future_direction": "接下來一起靠近更穩定的週末節奏。",
                },
            ),
            (
                "PUT",
                "/api/love-map/essentials/heart-profile",
                {
                    "primary": "words",
                    "secondary": "time",
                    "support_me": "先抱我一下。",
                    "avoid_when_stressed": "不要急著解釋。",
                    "small_delights": "帶熱飲給我。",
                },
            ),
            (
                "PUT",
                "/api/love-map/essentials/repair-agreements",
                {
                    "protect_what_matters": "先保護彼此的安全感。",
                    "avoid_in_conflict": "不要翻舊帳。",
                    "repair_reentry": "先停一下，再回來。",
                },
            ),
            ("POST", f"/api/love-map/essentials/repair-outcome-captures/{uuid.uuid4()}/dismiss", None),
            ("POST", "/api/love-map/notes", {"layer": "safe", "content": "note"}),
            ("POST", "/api/love-map/suggestions/shared-future/generate", None),
            ("POST", "/api/love-map/suggestions/shared-future/generate-story-ritual", None),
            ("POST", f"/api/love-map/suggestions/shared-future/refinements/{uuid.uuid4()}/generate", None),
            ("POST", f"/api/love-map/suggestions/shared-future/refinements/{uuid.uuid4()}/generate-cadence", None),
            ("POST", f"/api/love-map/suggestions/{uuid.uuid4()}/accept", None),
            ("POST", f"/api/love-map/suggestions/{uuid.uuid4()}/dismiss", None),
            ("PUT", f"/api/love-map/notes/{uuid.uuid4()}", {"content": "updated"}),
            (
                "POST",
                "/api/users/me/onboarding-consent",
                {
                    "privacy_scope_accepted": True,
                    "notification_frequency": "normal",
                    "ai_intensity": "gentle",
                },
            ),
        ]
        for method, path, payload in cases:
            if method == "POST":
                response = self.client.post(path, json=payload)
            elif method == "PUT":
                response = self.client.put(path, json=payload)
            else:
                raise AssertionError(f"Unsupported method in test case: {method}")
            self.assertEqual(
                response.status_code,
                401,
                msg=f"{method} {path} should require authentication, got {response.status_code}",
            )


class LoveMapNoteMutatingBolaTests(unittest.TestCase):
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
            owner = User(email="love-map-owner@example.com", full_name="Owner", hashed_password="hashed")
            outsider = User(email="love-map-outsider@example.com", full_name="Outsider", hashed_password="hashed")
            session.add(owner)
            session.add(outsider)
            session.commit()
            session.refresh(owner)
            session.refresh(outsider)

            note = LoveMapNote(
                user_id=owner.id,
                partner_id=outsider.id,
                layer="safe",
                content="original",
            )
            session.add(note)
            session.commit()
            session.refresh(note)

            self.owner_id = owner.id
            self.outsider_id = outsider.id
            self.note_id = note.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_owner_can_update_note(self) -> None:
        self.current_user_id = self.owner_id
        response = self.client.put(f"/api/love-map/notes/{self.note_id}", json={"content": "owner-updated"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["content"], "owner-updated")

    def test_non_owner_cannot_update_note(self) -> None:
        self.current_user_id = self.outsider_id
        response = self.client.put(f"/api/love-map/notes/{self.note_id}", json={"content": "tampered"})
        self.assertEqual(response.status_code, 404)

        with Session(self.engine) as session:
            row = session.get(LoveMapNote, self.note_id)
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.content, "original")


if __name__ == "__main__":
    unittest.main()
