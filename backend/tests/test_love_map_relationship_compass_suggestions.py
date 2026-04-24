# READ_AUTHZ_MATRIX: GET /api/love-map/suggestions/relationship-compass
# AUTHZ_MATRIX: POST /api/love-map/suggestions/relationship-compass/generate
# AUTHZ_MATRIX: POST /api/love-map/suggestions/relationship-compass/{suggestion_id}/accept
# AUTHZ_MATRIX: POST /api/love-map/suggestions/relationship-compass/{suggestion_id}/dismiss
# AUTHZ_DENY_MATRIX: POST /api/love-map/suggestions/relationship-compass/{suggestion_id}/accept
# AUTHZ_DENY_MATRIX: POST /api/love-map/suggestions/relationship-compass/{suggestion_id}/dismiss

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
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.appreciation import Appreciation  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.relationship_compass import RelationshipCompass  # noqa: E402
from app.models.relationship_compass_change import RelationshipCompassChange  # noqa: E402
from app.models.relationship_knowledge_suggestion import RelationshipKnowledgeSuggestion  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.ai_errors import HavenAIProviderError  # noqa: E402


class LoveMapRelationshipCompassSuggestionTests(unittest.TestCase):
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
            alice = User(email="alice-compass-ai@example.com", full_name="Alice", hashed_password="hashed")
            bob = User(email="bob-compass-ai@example.com", full_name="Bob", hashed_password="hashed")
            carol = User(email="carol-compass-ai@example.com", full_name="Carol", hashed_password="hashed")
            dave = User(email="dave-compass-ai@example.com", full_name="Dave", hashed_password="hashed")
            solo = User(email="solo-compass-ai@example.com", full_name="Solo", hashed_password="hashed")
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
                RelationshipCompass(
                    user_id=min(alice.id, bob.id),
                    partner_id=max(alice.id, bob.id),
                    identity_statement="我們是在忙裡仍願意回來對話的伴侶。",
                    story_anchor="想一起記得咖啡和散步把我們帶回來。",
                    future_direction="接下來一起靠近更穩定的週末節奏。",
                    updated_by_user_id=alice.id,
                )
            )
            session.add(
                Journal(
                    user_id=alice.id,
                    content="今天散步時我們把最近的壓力慢慢說完，最後約好週末不要只剩待辦。",
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
            )
            session.add(
                Appreciation(
                    user_id=alice.id,
                    partner_id=bob.id,
                    body_text="謝謝你在晚餐後願意陪我散步，讓我們又能慢慢回到彼此身邊。",
                    created_at=utcnow(),
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

    def _seed_pending_suggestion(self, *, user_id: uuid.UUID | None = None, partner_id: uuid.UUID | None = None) -> uuid.UUID:
        with Session(self.engine) as session:
            row = RelationshipKnowledgeSuggestion(
                user_id=user_id or self.alice_id,
                partner_id=partner_id or self.bob_id,
                section="relationship_compass",
                status="pending",
                generator_version="relationship_compass_v1",
                proposed_title="Relationship Compass 建議更新",
                proposed_notes="Haven 根據最近留下的片段整理出一版可審核的 Compass 更新。",
                candidate_json={
                    "identity_statement": "我們是在忙裡仍願意慢慢回來對話的伴侶。",
                    "story_anchor": "想一起記得晚餐後散步，讓我們又回到彼此身邊。",
                    "future_direction": "接下來一起把週末留給散步和真正對話。",
                },
                evidence_json=[
                    {
                        "source_kind": "journal",
                        "source_id": "journal-seed",
                        "label": "你的日記",
                        "excerpt": "散步時把壓力慢慢說完。",
                    }
                ],
                dedupe_key="relationship-compass-seed",
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.id

    def test_list_returns_personal_pending_relationship_compass_suggestions(self) -> None:
        suggestion_id = self._seed_pending_suggestion()
        self.current_user_id = self.alice_id

        response = self.client.get("/api/love-map/suggestions/relationship-compass")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual([item["id"] for item in payload], [str(suggestion_id)])
        self.assertEqual(payload[0]["section"], "relationship_compass")
        self.assertEqual(
            payload[0]["relationship_compass_candidate"]["future_direction"],
            "接下來一起把週末留給散步和真正對話。",
        )

        self.current_user_id = self.bob_id
        bob_response = self.client.get("/api/love-map/suggestions/relationship-compass")
        self.assertEqual(bob_response.status_code, 200)
        self.assertEqual(bob_response.json(), [])

    def test_generate_persists_one_bounded_pending_suggestion_and_reuses_queue(self) -> None:
        self.current_user_id = self.alice_id
        calls = {"count": 0}
        original = love_map.generate_relationship_compass_suggestion

        async def fake_generate_relationship_compass_suggestion(*, evidence_catalog, current_compass):
            calls["count"] += 1
            self.assertGreaterEqual(len(evidence_catalog), 2)
            self.assertEqual(current_compass["identity_statement"], "我們是在忙裡仍願意回來對話的伴侶。")
            return {
                "candidate": {
                    "identity_statement": "我們是在忙裡仍願意慢慢回來對話的伴侶。",
                    "story_anchor": "想一起記得晚餐後散步，讓我們又回到彼此身邊。",
                    "future_direction": "接下來一起把週末留給散步和真正對話。",
                },
                "dedupe_key": "compass-generated",
                "evidence": [
                    {
                        "source_kind": "journal",
                        "source_id": "journal-seed",
                        "label": "你的日記",
                        "excerpt": "散步時把壓力慢慢說完。",
                    }
                ],
            }

        love_map.generate_relationship_compass_suggestion = fake_generate_relationship_compass_suggestion
        try:
            response = self.client.post("/api/love-map/suggestions/relationship-compass/generate")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["status"], "pending")
            self.assertEqual(payload[0]["relationship_compass_candidate"]["story_anchor"], "想一起記得晚餐後散步，讓我們又回到彼此身邊。")

            replay = self.client.post("/api/love-map/suggestions/relationship-compass/generate")
            self.assertEqual(replay.status_code, 200)
            self.assertEqual(calls["count"], 1)
            self.assertEqual(len(replay.json()), 1)
        finally:
            love_map.generate_relationship_compass_suggestion = original

    def test_accept_writes_compass_and_marks_suggestion_accepted(self) -> None:
        suggestion_id = self._seed_pending_suggestion()
        self.current_user_id = self.alice_id

        response = self.client.post(f"/api/love-map/suggestions/relationship-compass/{suggestion_id}/accept")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["identity_statement"], "我們是在忙裡仍願意慢慢回來對話的伴侶。")
        self.assertEqual(payload["updated_by_name"], "Alice")

        with Session(self.engine) as session:
            suggestion = session.get(RelationshipKnowledgeSuggestion, suggestion_id)
            self.assertIsNotNone(suggestion)
            assert suggestion is not None
            self.assertEqual(suggestion.status, "accepted")
            self.assertIsNotNone(suggestion.reviewed_at)

            compass = session.exec(
                select(RelationshipCompass).where(
                    RelationshipCompass.user_id == min(self.alice_id, self.bob_id),
                    RelationshipCompass.partner_id == max(self.alice_id, self.bob_id),
                )
            ).first()
            self.assertIsNotNone(compass)
            assert compass is not None
            self.assertEqual(compass.future_direction, "接下來一起把週末留給散步和真正對話。")

            changes = session.exec(
                select(RelationshipCompassChange).where(
                    RelationshipCompassChange.user_id == min(self.alice_id, self.bob_id),
                    RelationshipCompassChange.partner_id == max(self.alice_id, self.bob_id),
                )
            ).all()
            self.assertEqual(len(changes), 1)
            self.assertEqual(changes[0].changed_by_user_id, self.alice_id)
            self.assertIsNone(changes[0].revision_note)
            self.assertEqual(changes[0].origin_kind, "accepted_suggestion")
            self.assertEqual(changes[0].source_suggestion_id, suggestion_id)

    def test_duplicate_accept_is_idempotent_and_does_not_duplicate_history(self) -> None:
        suggestion_id = self._seed_pending_suggestion()
        self.current_user_id = self.alice_id

        first = self.client.post(f"/api/love-map/suggestions/relationship-compass/{suggestion_id}/accept")
        self.assertEqual(first.status_code, 200)

        second = self.client.post(f"/api/love-map/suggestions/relationship-compass/{suggestion_id}/accept")
        self.assertEqual(second.status_code, 200)

        with Session(self.engine) as session:
            changes = session.exec(
                select(RelationshipCompassChange).where(
                    RelationshipCompassChange.user_id == min(self.alice_id, self.bob_id),
                    RelationshipCompassChange.partner_id == max(self.alice_id, self.bob_id),
                )
            ).all()
            self.assertEqual(len(changes), 1)

    def test_dismiss_after_accept_is_rejected(self) -> None:
        suggestion_id = self._seed_pending_suggestion()
        self.current_user_id = self.alice_id

        accept = self.client.post(f"/api/love-map/suggestions/relationship-compass/{suggestion_id}/accept")
        self.assertEqual(accept.status_code, 200)

        dismiss = self.client.post(f"/api/love-map/suggestions/relationship-compass/{suggestion_id}/dismiss")
        self.assertEqual(dismiss.status_code, 409)

    def test_manual_compass_save_keeps_history_manual(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.put(
            "/api/love-map/identity/compass",
            json={
                "identity_statement": "我們是會慢慢回來對話的伴侶。",
                "story_anchor": "想一起記得咖啡和散步把我們帶回來。",
                "future_direction": "接下來一起靠近更穩定的週末節奏。",
                "revision_note": "這次是手動微調一下。",
            },
        )
        self.assertEqual(response.status_code, 200)

        with Session(self.engine) as session:
            changes = session.exec(
                select(RelationshipCompassChange).where(
                    RelationshipCompassChange.user_id == min(self.alice_id, self.bob_id),
                    RelationshipCompassChange.partner_id == max(self.alice_id, self.bob_id),
                )
            ).all()
            self.assertEqual(len(changes), 1)
            self.assertEqual(changes[0].origin_kind, "manual_edit")
            self.assertIsNone(changes[0].source_suggestion_id)

    def test_dismiss_marks_suggestion_without_changing_compass(self) -> None:
        suggestion_id = self._seed_pending_suggestion()
        self.current_user_id = self.alice_id

        response = self.client.post(f"/api/love-map/suggestions/relationship-compass/{suggestion_id}/dismiss")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "dismissed")
        with Session(self.engine) as session:
            compass = session.exec(
                select(RelationshipCompass).where(
                    RelationshipCompass.user_id == min(self.alice_id, self.bob_id),
                    RelationshipCompass.partner_id == max(self.alice_id, self.bob_id),
                )
            ).first()
            self.assertIsNotNone(compass)
            assert compass is not None
            self.assertEqual(compass.identity_statement, "我們是在忙裡仍願意回來對話的伴侶。")
            self.assertEqual(session.exec(select(RelationshipCompassChange)).all(), [])

    def test_unpaired_and_cross_pair_users_cannot_mutate_compass_suggestions(self) -> None:
        suggestion_id = self._seed_pending_suggestion()

        self.current_user_id = self.solo_id
        solo_generate = self.client.post("/api/love-map/suggestions/relationship-compass/generate")
        self.assertEqual(solo_generate.status_code, 403)
        solo_accept = self.client.post(f"/api/love-map/suggestions/relationship-compass/{suggestion_id}/accept")
        self.assertEqual(solo_accept.status_code, 404)

        self.current_user_id = self.carol_id
        carol_accept = self.client.post(f"/api/love-map/suggestions/relationship-compass/{suggestion_id}/accept")
        carol_dismiss = self.client.post(f"/api/love-map/suggestions/relationship-compass/{suggestion_id}/dismiss")
        self.assertEqual(carol_accept.status_code, 404)
        self.assertEqual(carol_dismiss.status_code, 404)

    def test_generate_returns_503_when_ai_provider_fails(self) -> None:
        self.current_user_id = self.alice_id
        original = love_map.generate_relationship_compass_suggestion

        async def fake_generate_relationship_compass_suggestion(*, evidence_catalog, current_compass):
            raise HavenAIProviderError(
                reason="relationship_compass_suggestion_provider_error",
                retryable=True,
                provider="openai",
            )

        love_map.generate_relationship_compass_suggestion = fake_generate_relationship_compass_suggestion
        try:
            response = self.client.post("/api/love-map/suggestions/relationship-compass/generate")
            self.assertEqual(response.status_code, 503)
        finally:
            love_map.generate_relationship_compass_suggestion = original


if __name__ == "__main__":
    unittest.main()
