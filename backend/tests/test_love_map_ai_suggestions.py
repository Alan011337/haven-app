# READ_AUTHZ_MATRIX: GET /api/love-map/suggestions/shared-future
# AUTHZ_MATRIX: POST /api/love-map/suggestions/shared-future/generate
# AUTHZ_MATRIX: POST /api/love-map/suggestions/{suggestion_id}/accept
# AUTHZ_MATRIX: POST /api/love-map/suggestions/{suggestion_id}/dismiss
# AUTHZ_DENY_MATRIX: POST /api/love-map/suggestions/{suggestion_id}/accept
# AUTHZ_DENY_MATRIX: POST /api/love-map/suggestions/{suggestion_id}/dismiss

from __future__ import annotations

import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import love_map  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.appreciation import Appreciation  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_response import CardResponse, ResponseStatus  # noqa: E402
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.relationship_knowledge_suggestion import RelationshipKnowledgeSuggestion  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.wishlist_item import WishlistItem  # noqa: E402
from app.services.ai_errors import HavenAIProviderError  # noqa: E402


class LoveMapAISuggestionFlowTests(unittest.TestCase):
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
            alice = User(email="alice-ai-love-map@example.com", full_name="Alice", hashed_password="hashed")
            bob = User(email="bob-ai-love-map@example.com", full_name="Bob", hashed_password="hashed")
            outsider = User(email="outsider-ai-love-map@example.com", full_name="Outsider", hashed_password="hashed")
            session.add(alice)
            session.add(bob)
            session.add(outsider)
            session.commit()
            session.refresh(alice)
            session.refresh(bob)
            session.refresh(outsider)

            alice.partner_id = bob.id
            bob.partner_id = alice.id
            session.add(alice)
            session.add(bob)
            session.commit()

            self.card = Card(
                category=CardCategory.GROWTH_QUEST,
                title="未來節奏",
                description="看看你們想一起長出的生活感。",
                question="如果接下來三個月要一起培養一個新的小習慣，你最想是什麼？",
                difficulty_level=1,
                depth_level=1,
            )
            session.add(self.card)
            session.commit()
            session.refresh(self.card)

            journal = Journal(
                user_id=alice.id,
                content="今天是我們在一起的第 500 天紀念日！我們約好以後每個一百天都要慶祝一下。",
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            appreciation = Appreciation(
                user_id=alice.id,
                partner_id=bob.id,
                body_text="謝謝你每天早上幫我準備咖啡，這個小習慣讓我每天都很期待起床。",
                created_at=utcnow(),
            )
            session.add(journal)
            session.add(appreciation)
            session.commit()
            session.refresh(journal)
            session.refresh(appreciation)

            card_session = CardSession(
                creator_id=alice.id,
                partner_id=bob.id,
                card_id=self.card.id,
                category=self.card.category.value,
                mode=CardSessionMode.DAILY_RITUAL,
                status=CardSessionStatus.COMPLETED,
                created_at=utcnow(),
            )
            session.add(card_session)
            session.commit()
            session.refresh(card_session)

            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=alice.id,
                    session_id=card_session.id,
                    content="我想一起把每個一百天都變成小小慶祝。",
                    status=ResponseStatus.REVEALED,
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=bob.id,
                    session_id=card_session.id,
                    content="我想一起存一筆旅行基金，讓計畫更有形狀。",
                    status=ResponseStatus.REVEALED,
                    is_initiator=False,
                )
            )
            session.commit()

            historical_time = utcnow() - timedelta(days=365)
            time_capsule_journal = Journal(
                user_id=alice.id,
                content="一年前的今天，我們又回到那間咖啡廳，坐在窗邊聊了一個下午。",
                created_at=historical_time,
                updated_at=historical_time,
            )
            time_capsule_appreciation = Appreciation(
                user_id=alice.id,
                partner_id=bob.id,
                body_text="謝謝你那天下午陪我去咖啡廳，讓那個午後一直留在我心裡。",
                created_at=historical_time,
            )
            session.add(time_capsule_journal)
            session.add(time_capsule_appreciation)
            session.commit()
            session.refresh(time_capsule_journal)
            session.refresh(time_capsule_appreciation)

            time_capsule_session = CardSession(
                creator_id=alice.id,
                partner_id=bob.id,
                card_id=self.card.id,
                category=self.card.category.value,
                mode=CardSessionMode.DAILY_RITUAL,
                status=CardSessionStatus.COMPLETED,
                created_at=historical_time,
            )
            session.add(time_capsule_session)
            session.commit()
            session.refresh(time_capsule_session)

            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=alice.id,
                    session_id=time_capsule_session.id,
                    content="我想把這種慢慢聊天的午後留下來，當成我們會回來看的記憶。",
                    status=ResponseStatus.REVEALED,
                    is_initiator=True,
                    created_at=historical_time,
                )
            )
            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=bob.id,
                    session_id=time_capsule_session.id,
                    content="如果可以，我想偶爾再回到這種慢一點的節奏裡。",
                    status=ResponseStatus.REVEALED,
                    is_initiator=False,
                    created_at=historical_time,
                )
            )
            session.commit()

            self.alice_id = alice.id
            self.bob_id = bob.id
            self.outsider_id = outsider.id
            self.journal_id = journal.id
            self.appreciation_id = appreciation.id
            self.card_session_id = card_session.id
            self.time_capsule_journal_id = time_capsule_journal.id
            self.time_capsule_appreciation_id = time_capsule_appreciation.id
            self.time_capsule_session_id = time_capsule_session.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_generate_shared_future_suggestions_persists_personal_pending_queue(self) -> None:
        self.current_user_id = self.alice_id
        calls = {"count": 0}
        original = love_map.generate_shared_future_suggestions

        async def fake_generate_shared_future_suggestions(*, evidence_catalog, existing_titles):
            calls["count"] += 1
            self.assertGreaterEqual(len(evidence_catalog), 3)
            self.assertEqual(existing_titles, [])
            return [
                {
                    "proposed_title": "每一百天留一個小慶祝",
                    "proposed_notes": "把紀念日變成固定的小小儀式，提醒彼此這段關係值得被慶祝。",
                    "dedupe_key": "每一百天留一個小慶祝",
                    "evidence": [
                        {
                            "source_kind": "journal",
                            "source_id": str(self.journal_id),
                            "label": "你的日記 · today",
                            "excerpt": "我們約好以後每個一百天都要慶祝一下。",
                        },
                        {
                            "source_kind": "card",
                            "source_id": str(self.card_session_id),
                            "label": "共同卡片 · 未來節奏",
                            "excerpt": "我想一起把每個一百天都變成小小慶祝。",
                        },
                    ],
                },
                {
                    "proposed_title": "一起存旅行基金",
                    "proposed_notes": "把想一起去的地方變成更真實的共同計畫。",
                    "dedupe_key": "一起存旅行基金",
                    "evidence": [
                        {
                            "source_kind": "card",
                            "source_id": str(self.card_session_id),
                            "label": "共同卡片 · 未來節奏",
                            "excerpt": "我想一起存一筆旅行基金，讓計畫更有形狀。",
                        },
                        {
                            "source_kind": "appreciation",
                            "source_id": str(self.appreciation_id),
                            "label": "感恩 · today",
                            "excerpt": "謝謝你每天早上幫我準備咖啡。",
                        },
                    ],
                },
            ]

        love_map.generate_shared_future_suggestions = fake_generate_shared_future_suggestions
        try:
            response = self.client.post("/api/love-map/suggestions/shared-future/generate")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(len(payload), 2)
            self.assertEqual(payload[0]["status"], "pending")
            self.assertEqual(payload[0]["section"], "shared_future")
            self.assertEqual(payload[0]["proposed_title"], "每一百天留一個小慶祝")

            replay_response = self.client.post("/api/love-map/suggestions/shared-future/generate")
            self.assertEqual(replay_response.status_code, 200)
            self.assertEqual(calls["count"], 1)
            self.assertEqual(len(replay_response.json()), 2)

            with Session(self.engine) as session:
                rows = session.exec(select(RelationshipKnowledgeSuggestion)).all()
                self.assertEqual(len(rows), 2)
                self.assertEqual({row.status for row in rows}, {"pending"})
        finally:
            love_map.generate_shared_future_suggestions = original

    def test_generate_filters_near_duplicate_titles_against_existing_and_handled_ideas(self) -> None:
        self.current_user_id = self.alice_id
        with Session(self.engine) as session:
            session.add(
                WishlistItem(
                    user_id=self.alice_id,
                    partner_id=self.bob_id,
                    title="每百天慶祝一次",
                    notes="已經是一個存在的共同未來片段。",
                    created_at=utcnow(),
                )
            )
            session.add(
                RelationshipKnowledgeSuggestion(
                    user_id=self.alice_id,
                    partner_id=self.bob_id,
                    section="shared_future",
                    status="dismissed",
                    generator_version="shared_future_v1",
                    proposed_title="每週一次感恩分享",
                    proposed_notes="把感謝變成固定的週節奏。",
                    evidence_json=[],
                    dedupe_key="每週一次感恩分享",
                    reviewed_at=utcnow(),
                )
            )
            session.commit()

        original = love_map.generate_shared_future_suggestions

        async def fake_generate_shared_future_suggestions(*, evidence_catalog, existing_titles):
            self.assertIn("每百天慶祝一次", existing_titles)
            return [
                {
                    "proposed_title": "每一百天留一個小慶祝",
                    "proposed_notes": "把重要的節點變成固定的關係儀式。",
                    "dedupe_key": "每一百天留一個小慶祝",
                    "evidence": [
                        {
                            "source_kind": "journal",
                            "source_id": str(self.journal_id),
                            "label": "你的日記 · today",
                            "excerpt": "我們約好以後每個一百天都要慶祝一下。",
                        }
                    ],
                },
                {
                    "proposed_title": "每週留一次感恩分享",
                    "proposed_notes": "把謝謝彼此的話，固定留在一週的一個晚上。",
                    "dedupe_key": "每週留一次感恩分享",
                    "evidence": [
                        {
                            "source_kind": "appreciation",
                            "source_id": str(self.appreciation_id),
                            "label": "感恩 · today",
                            "excerpt": "謝謝你每天早上幫我準備咖啡。",
                        }
                    ],
                },
                {
                    "proposed_title": "一起存旅行基金",
                    "proposed_notes": "把想去的地方變成更具體的共同計畫。",
                    "dedupe_key": "一起存旅行基金",
                    "evidence": [
                        {
                            "source_kind": "card",
                            "source_id": str(self.card_session_id),
                            "label": "共同卡片 · 未來節奏",
                            "excerpt": "我想一起存一筆旅行基金，讓計畫更有形狀。",
                        }
                    ],
                },
            ]

        love_map.generate_shared_future_suggestions = fake_generate_shared_future_suggestions
        try:
            response = self.client.post("/api/love-map/suggestions/shared-future/generate")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual([item["proposed_title"] for item in payload], ["一起存旅行基金"])

            with Session(self.engine) as session:
                pending_rows = session.exec(
                    select(RelationshipKnowledgeSuggestion).where(
                        RelationshipKnowledgeSuggestion.section == "shared_future",
                        RelationshipKnowledgeSuggestion.status == "pending",
                    )
                ).all()
                self.assertEqual(len(pending_rows), 1)
                self.assertEqual(pending_rows[0].proposed_title, "一起存旅行基金")
        finally:
            love_map.generate_shared_future_suggestions = original

    def test_generate_filters_near_duplicate_titles_within_same_generation_batch(self) -> None:
        self.current_user_id = self.alice_id
        original = love_map.generate_shared_future_suggestions

        async def fake_generate_shared_future_suggestions(*, evidence_catalog, existing_titles):
            return [
                {
                    "proposed_title": "每百天慶祝一次",
                    "proposed_notes": "把重要的關係節點留成固定的小小慶祝。",
                    "dedupe_key": "每百天慶祝一次",
                    "evidence": [
                        {
                            "source_kind": "journal",
                            "source_id": str(self.journal_id),
                            "label": "你的日記 · today",
                            "excerpt": "我們約好以後每個一百天都要慶祝一下。",
                        }
                    ],
                },
                {
                    "proposed_title": "每一百天留一個小慶祝",
                    "proposed_notes": "讓一百天一次的紀念，變成會一起回來看的儀式。",
                    "dedupe_key": "每一百天留一個小慶祝",
                    "evidence": [
                        {
                            "source_kind": "card",
                            "source_id": str(self.card_session_id),
                            "label": "共同卡片 · 未來節奏",
                            "excerpt": "我想一起把每個一百天都變成小小慶祝。",
                        }
                    ],
                },
                {
                    "proposed_title": "一起存旅行基金",
                    "proposed_notes": "把想去的地方變成更具體的共同計畫。",
                    "dedupe_key": "一起存旅行基金",
                    "evidence": [
                        {
                            "source_kind": "card",
                            "source_id": str(self.card_session_id),
                            "label": "共同卡片 · 未來節奏",
                            "excerpt": "我想一起存一筆旅行基金，讓計畫更有形狀。",
                        }
                    ],
                },
            ]

        love_map.generate_shared_future_suggestions = fake_generate_shared_future_suggestions
        try:
            response = self.client.post("/api/love-map/suggestions/shared-future/generate")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(
                [item["proposed_title"] for item in payload],
                ["每百天慶祝一次", "一起存旅行基金"],
            )
        finally:
            love_map.generate_shared_future_suggestions = original

    def test_generate_story_ritual_persists_story_grounded_pending_suggestion(self) -> None:
        self.current_user_id = self.alice_id
        calls = {"count": 0}
        original = love_map.generate_shared_future_story_adjacent_ritual

        async def fake_generate_shared_future_story_adjacent_ritual(*, evidence_catalog, existing_titles, handled_titles):
            calls["count"] += 1
            self.assertEqual(existing_titles, [])
            self.assertEqual(handled_titles, [])
            self.assertGreaterEqual(len(evidence_catalog), 2)
            self.assertEqual(evidence_catalog[0]["source_kind"], "story_time_capsule")
            self.assertIn("一年前", evidence_catalog[0]["excerpt"])
            self.assertTrue(any(item["source_kind"] == "time_capsule_item" for item in evidence_catalog[1:]))
            return {
                "proposed_title": "每年一起回到那間咖啡廳",
                "proposed_notes": "在接近這段回憶的日子裡，一起回去坐一個下午，交換現在的感受。",
                "dedupe_key": "每年一起回到那間咖啡廳",
                "evidence": [
                    {
                        "source_kind": "story_time_capsule",
                        "source_id": "2025-03-31:2025-04-06",
                        "label": "Story Time Capsule",
                        "excerpt": "一年前這幾天：1 則日記、1 則共同卡片回憶、1 則感恩。",
                    },
                    {
                        "source_kind": "time_capsule_item",
                        "source_id": str(self.time_capsule_journal_id),
                        "label": "Time Capsule · 日記",
                        "excerpt": "一年前的今天，我們又回到那間咖啡廳，坐在窗邊聊了一個下午。",
                    },
                ],
            }

        love_map.generate_shared_future_story_adjacent_ritual = fake_generate_shared_future_story_adjacent_ritual
        try:
            response = self.client.post("/api/love-map/suggestions/shared-future/generate-story-ritual")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(len(payload), 1)
            self.assertEqual(calls["count"], 1)
            self.assertEqual(payload[0]["generator_version"], "shared_future_story_ritual_v1")
            self.assertEqual(payload[0]["proposed_title"], "每年一起回到那間咖啡廳")
            self.assertEqual(payload[0]["status"], "pending")
            self.assertEqual(payload[0]["section"], "shared_future")
            self.assertEqual(payload[0]["evidence"][0]["source_kind"], "story_time_capsule")

            with Session(self.engine) as session:
                rows = session.exec(
                    select(RelationshipKnowledgeSuggestion).where(
                        RelationshipKnowledgeSuggestion.generator_version == "shared_future_story_ritual_v1",
                    )
                ).all()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].status, "pending")
        finally:
            love_map.generate_shared_future_story_adjacent_ritual = original

    def test_generate_story_ritual_returns_empty_without_time_capsule(self) -> None:
        self.current_user_id = self.alice_id
        original = love_map.get_relationship_story_time_capsule

        def fake_get_relationship_story_time_capsule(*, session, user_id, partner_id):
            return None

        love_map.get_relationship_story_time_capsule = fake_get_relationship_story_time_capsule
        try:
            response = self.client.post("/api/love-map/suggestions/shared-future/generate-story-ritual")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
        finally:
            love_map.get_relationship_story_time_capsule = original

    def test_generate_story_ritual_filters_near_duplicate_titles_against_handled_shared_future_items(self) -> None:
        self.current_user_id = self.alice_id
        with Session(self.engine) as session:
            session.add(
                WishlistItem(
                    user_id=self.alice_id,
                    partner_id=self.bob_id,
                    title="每年一起回到那間咖啡廳",
                    notes="已經被接受成 shared future。",
                    created_at=utcnow(),
                )
            )
            session.add(
                RelationshipKnowledgeSuggestion(
                    user_id=self.alice_id,
                    partner_id=self.bob_id,
                    section="shared_future",
                    status="dismissed",
                    generator_version="shared_future_story_ritual_v1",
                    proposed_title="每逢紀念日回到那間咖啡廳",
                    proposed_notes="把那個午後重新走一遍。",
                    evidence_json=[],
                    dedupe_key="每逢紀念日回到那間咖啡廳",
                    reviewed_at=utcnow(),
                )
            )
            session.commit()

        original = love_map.generate_shared_future_story_adjacent_ritual

        async def fake_generate_shared_future_story_adjacent_ritual(*, evidence_catalog, existing_titles, handled_titles):
            self.assertIn("每年一起回到那間咖啡廳", existing_titles)
            self.assertIn("每逢紀念日回到那間咖啡廳", handled_titles)
            return {
                "proposed_title": "每年一起回到那間咖啡廳",
                "proposed_notes": "在接近這段記憶的日子裡，一起回去坐一個下午。",
                "dedupe_key": "每年一起回到那間咖啡廳",
                "evidence": [
                    {
                        "source_kind": "story_time_capsule",
                        "source_id": "story-capsule",
                        "label": "Story Time Capsule",
                        "excerpt": "一年前這幾天：1 則日記、1 則共同卡片回憶、1 則感恩。",
                    }
                ],
            }

        love_map.generate_shared_future_story_adjacent_ritual = fake_generate_shared_future_story_adjacent_ritual
        try:
            response = self.client.post("/api/love-map/suggestions/shared-future/generate-story-ritual")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
        finally:
            love_map.generate_shared_future_story_adjacent_ritual = original

    def test_generate_story_ritual_returns_503_when_ai_provider_fails(self) -> None:
        self.current_user_id = self.alice_id
        original = love_map.generate_shared_future_story_adjacent_ritual

        async def fake_generate_shared_future_story_adjacent_ritual(*, evidence_catalog, existing_titles, handled_titles):
            raise HavenAIProviderError(
                reason="shared_future_story_ritual_provider_error",
                retryable=True,
                provider="openai",
            )

        love_map.generate_shared_future_story_adjacent_ritual = fake_generate_shared_future_story_adjacent_ritual
        try:
            response = self.client.post("/api/love-map/suggestions/shared-future/generate-story-ritual")
            self.assertEqual(response.status_code, 503)
        finally:
            love_map.generate_shared_future_story_adjacent_ritual = original

    def test_accept_and_dismiss_are_owner_scoped_and_pending_queue_is_personal_only(self) -> None:
        with Session(self.engine) as session:
            accept_row = RelationshipKnowledgeSuggestion(
                user_id=self.alice_id,
                partner_id=self.bob_id,
                section="shared_future",
                status="pending",
                generator_version="shared_future_v1",
                proposed_title="一起存旅行基金",
                proposed_notes="每個月固定存一小筆，讓旅行不只停在想像。",
                evidence_json=[],
                dedupe_key="一起存旅行基金",
            )
            dismiss_row = RelationshipKnowledgeSuggestion(
                user_id=self.alice_id,
                partner_id=self.bob_id,
                section="shared_future",
                status="pending",
                generator_version="shared_future_v1",
                proposed_title="每一百天留一個小慶祝",
                proposed_notes="把重要的日子變成固定的儀式。",
                evidence_json=[],
                dedupe_key="每一百天留一個小慶祝",
            )
            session.add(accept_row)
            session.add(dismiss_row)
            session.commit()
            session.refresh(accept_row)
            session.refresh(dismiss_row)
            accept_id = accept_row.id
            dismiss_id = dismiss_row.id

        self.current_user_id = self.alice_id
        accept_response = self.client.post(f"/api/love-map/suggestions/{accept_id}/accept")
        self.assertEqual(accept_response.status_code, 200)
        self.assertEqual(accept_response.json()["title"], "一起存旅行基金")

        dismiss_response = self.client.post(f"/api/love-map/suggestions/{dismiss_id}/dismiss")
        self.assertEqual(dismiss_response.status_code, 200)
        self.assertEqual(dismiss_response.json()["status"], "dismissed")

        with Session(self.engine) as session:
            accepted_row = session.get(RelationshipKnowledgeSuggestion, accept_id)
            dismissed_row = session.get(RelationshipKnowledgeSuggestion, dismiss_id)
            self.assertIsNotNone(accepted_row)
            self.assertIsNotNone(dismissed_row)
            assert accepted_row is not None
            assert dismissed_row is not None
            self.assertEqual(accepted_row.status, "accepted")
            self.assertEqual(dismissed_row.status, "dismissed")
            self.assertIsNotNone(accepted_row.accepted_wishlist_item_id)
            accepted_item = session.get(WishlistItem, accepted_row.accepted_wishlist_item_id)
            self.assertIsNotNone(accepted_item)
            assert accepted_item is not None
            self.assertEqual(accepted_item.title, "一起存旅行基金")

        self.current_user_id = self.bob_id
        pending_for_bob = self.client.get("/api/love-map/suggestions/shared-future")
        self.assertEqual(pending_for_bob.status_code, 200)
        self.assertEqual(pending_for_bob.json(), [])

        deny_accept = self.client.post(f"/api/love-map/suggestions/{dismiss_id}/accept")
        deny_dismiss = self.client.post(f"/api/love-map/suggestions/{dismiss_id}/dismiss")
        self.assertEqual(deny_accept.status_code, 404)
        self.assertEqual(deny_dismiss.status_code, 404)

        self.current_user_id = self.outsider_id
        outsider_accept = self.client.post(f"/api/love-map/suggestions/{accept_id}/accept")
        outsider_dismiss = self.client.post(f"/api/love-map/suggestions/{dismiss_id}/dismiss")
        self.assertEqual(outsider_accept.status_code, 404)
        self.assertEqual(outsider_dismiss.status_code, 404)

    def test_generate_returns_503_when_ai_provider_fails(self) -> None:
        self.current_user_id = self.alice_id
        original = love_map.generate_shared_future_suggestions

        async def fake_generate_shared_future_suggestions(*, evidence_catalog, existing_titles):
            raise HavenAIProviderError(
                reason="shared_future_suggestions_provider_error",
                retryable=True,
                provider="openai",
            )

        love_map.generate_shared_future_suggestions = fake_generate_shared_future_suggestions
        try:
            response = self.client.post("/api/love-map/suggestions/shared-future/generate")
            self.assertEqual(response.status_code, 503)
        finally:
            love_map.generate_shared_future_suggestions = original


if __name__ == "__main__":
    unittest.main()
