# READ_AUTHZ_MATRIX: GET /api/love-map/suggestions/shared-future/refinements
# AUTHZ_MATRIX: POST /api/love-map/suggestions/shared-future/refinements/{wishlist_item_id}/generate
# AUTHZ_MATRIX: POST /api/love-map/suggestions/shared-future/refinements/{wishlist_item_id}/generate-cadence
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
from app.models.relationship_knowledge_suggestion import RelationshipKnowledgeSuggestion  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.wishlist_item import WishlistItem  # noqa: E402
from app.services.ai_errors import HavenAIProviderError  # noqa: E402


class SharedFutureRefinementSuggestionFlowTests(unittest.TestCase):
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
            alice = User(email="alice-refinement@example.com", full_name="Alice", hashed_password="hashed")
            bob = User(email="bob-refinement@example.com", full_name="Bob", hashed_password="hashed")
            outsider = User(email="outsider-refinement@example.com", full_name="Outsider", hashed_password="hashed")
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

            monthly = WishlistItem(
                user_id=alice.id,
                partner_id=bob.id,
                title="每個月留一晚只屬於我們",
                notes="不安排社交，不追進度，只把那晚留給我們兩個人的晚餐和散步。",
                created_at=utcnow(),
            )
            kyoto = WishlistItem(
                user_id=bob.id,
                partner_id=alice.id,
                title="一起去京都看秋天",
                notes="想在有涼意的季節，一起住安靜的小旅館，慢慢走神社和巷子。",
                created_at=utcnow(),
            )
            repair_ritual = WishlistItem(
                user_id=alice.id,
                partner_id=bob.id,
                title="建立我們的衝突後修復儀式",
                notes="希望每次明顯爭執後，都能慢慢回到同一邊。",
                created_at=utcnow(),
            )
            outsider_wish = WishlistItem(
                user_id=outsider.id,
                partner_id=alice.id,
                title="不相關的片段",
                notes="不應被 Alice 看到",
                created_at=utcnow(),
            )
            session.add(monthly)
            session.add(kyoto)
            session.add(repair_ritual)
            session.add(outsider_wish)
            session.commit()
            session.refresh(monthly)
            session.refresh(kyoto)
            session.refresh(repair_ritual)
            session.refresh(outsider_wish)

            self.alice_id = alice.id
            self.bob_id = bob.id
            self.outsider_id = outsider.id
            self.monthly_wish_id = monthly.id
            self.kyoto_wish_id = kyoto.id
            self.repair_wish_id = repair_ritual.id
            self.outsider_wish_id = outsider_wish.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_generate_refinement_persists_pending_queue_and_reuses_existing_pending(self) -> None:
        self.current_user_id = self.alice_id
        calls = {"count": 0}
        original = love_map.generate_shared_future_refinement_next_step

        async def fake_generate_shared_future_refinement_next_step(*, title, notes, created_at):
            calls["count"] += 1
            self.assertEqual(title, "每個月留一晚只屬於我們")
            self.assertIn("晚餐和散步", notes)
            self.assertTrue(created_at.endswith("Z"))
            return {"proposed_notes": "先把每月第二個週五晚上固定留給彼此。"}

        love_map.generate_shared_future_refinement_next_step = fake_generate_shared_future_refinement_next_step
        try:
            response = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.monthly_wish_id}/generate"
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["section"], "shared_future_refinement")
            self.assertEqual(payload[0]["status"], "pending")
            self.assertEqual(payload[0]["target_wishlist_item_id"], str(self.monthly_wish_id))

            replay = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.monthly_wish_id}/generate"
            )
            self.assertEqual(replay.status_code, 200)
            self.assertEqual(len(replay.json()), 1)
            self.assertEqual(calls["count"], 1)

            with Session(self.engine) as session:
                rows = session.exec(
                    select(RelationshipKnowledgeSuggestion).where(
                        RelationshipKnowledgeSuggestion.section == "shared_future_refinement"
                    )
                ).all()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].target_wishlist_item_id, self.monthly_wish_id)
        finally:
            love_map.generate_shared_future_refinement_next_step = original

    def test_generate_refinement_skips_handled_dedupe_keys(self) -> None:
        self.current_user_id = self.alice_id
        with Session(self.engine) as session:
            session.add(
                RelationshipKnowledgeSuggestion(
                    user_id=self.alice_id,
                    partner_id=self.bob_id,
                    section="shared_future_refinement",
                    status="dismissed",
                    generator_version="shared_future_refinement_next_step_v1",
                    proposed_title="",
                    proposed_notes="先查今年京都紅葉預測和機票。",
                    evidence_json=[],
                    dedupe_key=f"wishlist:{self.kyoto_wish_id}:next-step:先查今年京都紅葉預測和機票。",
                    target_wishlist_item_id=self.kyoto_wish_id,
                    reviewed_at=utcnow(),
                )
            )
            session.commit()

        original = love_map.generate_shared_future_refinement_next_step

        async def fake_generate_shared_future_refinement_next_step(*, title, notes, created_at):
            return {"proposed_notes": "先查今年京都紅葉預測和機票。"}

        love_map.generate_shared_future_refinement_next_step = fake_generate_shared_future_refinement_next_step
        try:
            response = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.kyoto_wish_id}/generate"
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
        finally:
            love_map.generate_shared_future_refinement_next_step = original

    def test_generate_refinement_respects_recent_dismissal_cooldown(self) -> None:
        self.current_user_id = self.alice_id
        with Session(self.engine) as session:
            session.add(
                RelationshipKnowledgeSuggestion(
                    user_id=self.alice_id,
                    partner_id=self.bob_id,
                    section="shared_future_refinement",
                    status="dismissed",
                    generator_version="shared_future_refinement_next_step_v1",
                    proposed_title="",
                    proposed_notes="先查找京都的小旅館。",
                    evidence_json=[],
                    dedupe_key=f"wishlist:{self.kyoto_wish_id}:next-step:先查找京都的小旅館。",
                    target_wishlist_item_id=self.kyoto_wish_id,
                    reviewed_at=utcnow(),
                )
            )
            session.commit()

        calls = {"count": 0}
        original = love_map.generate_shared_future_refinement_next_step

        async def fake_generate_shared_future_refinement_next_step(*, title, notes, created_at):
            calls["count"] += 1
            return {"proposed_notes": "先選定日期，再找旅館。"}

        love_map.generate_shared_future_refinement_next_step = fake_generate_shared_future_refinement_next_step
        try:
            response = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.kyoto_wish_id}/generate"
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
            self.assertEqual(calls["count"], 0)
        finally:
            love_map.generate_shared_future_refinement_next_step = original

    def test_generate_refinement_filters_near_duplicate_of_existing_next_step_line(self) -> None:
        self.current_user_id = self.alice_id
        with Session(self.engine) as session:
            wishlist = session.get(WishlistItem, self.monthly_wish_id)
            assert wishlist is not None
            wishlist.notes = (
                f"{wishlist.notes}\n\n"
                "下一步：先把每月第二個週五晚上固定留給彼此。"
            )
            session.add(wishlist)
            session.commit()

        original = love_map.generate_shared_future_refinement_next_step

        async def fake_generate_shared_future_refinement_next_step(*, title, notes, created_at):
            return {"proposed_notes": "先固定每月第二個週五晚上留給彼此。"}

        love_map.generate_shared_future_refinement_next_step = fake_generate_shared_future_refinement_next_step
        try:
            response = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.monthly_wish_id}/generate"
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
        finally:
            love_map.generate_shared_future_refinement_next_step = original

    def test_generate_refinement_filters_near_duplicate_of_dismissed_refinement_after_cooldown(self) -> None:
        self.current_user_id = self.alice_id
        with Session(self.engine) as session:
            session.add(
                RelationshipKnowledgeSuggestion(
                    user_id=self.alice_id,
                    partner_id=self.bob_id,
                    section="shared_future_refinement",
                    status="dismissed",
                    generator_version="shared_future_refinement_next_step_v1",
                    proposed_title="",
                    proposed_notes="先查京都紅葉預測和機票。",
                    evidence_json=[],
                    dedupe_key=f"wishlist:{self.kyoto_wish_id}:next-step:先查京都紅葉預測和機票。",
                    target_wishlist_item_id=self.kyoto_wish_id,
                    reviewed_at=utcnow() - timedelta(days=2),
                )
            )
            session.commit()

        calls = {"count": 0}
        original = love_map.generate_shared_future_refinement_next_step

        async def fake_generate_shared_future_refinement_next_step(*, title, notes, created_at):
            calls["count"] += 1
            return {"proposed_notes": "先查京都紅葉預測，再看機票。"}

        love_map.generate_shared_future_refinement_next_step = fake_generate_shared_future_refinement_next_step
        try:
            response = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.kyoto_wish_id}/generate"
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
            self.assertEqual(calls["count"], 1)
        finally:
            love_map.generate_shared_future_refinement_next_step = original

    def test_generate_refinement_filters_near_duplicate_of_accepted_refinement_for_same_item(self) -> None:
        self.current_user_id = self.alice_id
        with Session(self.engine) as session:
            session.add(
                RelationshipKnowledgeSuggestion(
                    user_id=self.alice_id,
                    partner_id=self.bob_id,
                    section="shared_future_refinement",
                    status="accepted",
                    generator_version="shared_future_refinement_next_step_v1",
                    proposed_title="",
                    proposed_notes="先把每月第二個週五晚上固定留給彼此。",
                    evidence_json=[],
                    dedupe_key=f"wishlist:{self.monthly_wish_id}:next-step:先把每月第二個週五晚上固定留給彼此。",
                    target_wishlist_item_id=self.monthly_wish_id,
                    accepted_wishlist_item_id=self.monthly_wish_id,
                    reviewed_at=utcnow(),
                )
            )
            session.commit()

        original = love_map.generate_shared_future_refinement_next_step

        async def fake_generate_shared_future_refinement_next_step(*, title, notes, created_at):
            return {"proposed_notes": "先固定每月第二個週五晚上留給彼此。"}

        love_map.generate_shared_future_refinement_next_step = fake_generate_shared_future_refinement_next_step
        try:
            response = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.monthly_wish_id}/generate"
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
        finally:
            love_map.generate_shared_future_refinement_next_step = original

    def test_generate_cadence_refinement_persists_pending_for_monthly_item(self) -> None:
        self.current_user_id = self.alice_id
        calls = {"count": 0}
        original = love_map.generate_shared_future_refinement_cadence

        async def fake_generate_shared_future_refinement_cadence(*, title, notes, created_at):
            calls["count"] += 1
            self.assertEqual(title, "每個月留一晚只屬於我們")
            self.assertIn("晚餐和散步", notes)
            self.assertTrue(created_at.endswith("Z"))
            return {"proposed_notes": "每月第二個週五晚上留給彼此。"}

        love_map.generate_shared_future_refinement_cadence = fake_generate_shared_future_refinement_cadence
        try:
            response = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.monthly_wish_id}/generate-cadence"
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["generator_version"], "shared_future_refinement_cadence_v1")
            self.assertEqual(payload[0]["target_wishlist_item_id"], str(self.monthly_wish_id))
            self.assertEqual(calls["count"], 1)
        finally:
            love_map.generate_shared_future_refinement_cadence = original

    def test_generate_cadence_refinement_supports_ritual_item(self) -> None:
        self.current_user_id = self.alice_id
        original = love_map.generate_shared_future_refinement_cadence

        async def fake_generate_shared_future_refinement_cadence(*, title, notes, created_at):
            self.assertEqual(title, "建立我們的衝突後修復儀式")
            self.assertIn("回到同一邊", notes)
            return {"proposed_notes": "每次明顯爭執後 24 小時內安排一次短暫復盤。"}

        love_map.generate_shared_future_refinement_cadence = fake_generate_shared_future_refinement_cadence
        try:
            response = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.repair_wish_id}/generate-cadence"
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["generator_version"], "shared_future_refinement_cadence_v1")
            self.assertEqual(payload[0]["target_wishlist_item_id"], str(self.repair_wish_id))
        finally:
            love_map.generate_shared_future_refinement_cadence = original

    def test_generate_cadence_refinement_returns_empty_for_one_off_item(self) -> None:
        self.current_user_id = self.alice_id
        calls = {"count": 0}
        original = love_map.generate_shared_future_refinement_cadence

        async def fake_generate_shared_future_refinement_cadence(*, title, notes, created_at):
            calls["count"] += 1
            return {"proposed_notes": "提前一週一起決定這次要怎麼過。"}

        love_map.generate_shared_future_refinement_cadence = fake_generate_shared_future_refinement_cadence
        try:
            response = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.kyoto_wish_id}/generate-cadence"
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
            self.assertEqual(calls["count"], 0)
        finally:
            love_map.generate_shared_future_refinement_cadence = original

    def test_generate_cadence_refinement_respects_recent_same_subtype_dismissal(self) -> None:
        self.current_user_id = self.alice_id
        with Session(self.engine) as session:
            session.add(
                RelationshipKnowledgeSuggestion(
                    user_id=self.alice_id,
                    partner_id=self.bob_id,
                    section="shared_future_refinement",
                    status="dismissed",
                    generator_version="shared_future_refinement_cadence_v1",
                    proposed_title="",
                    proposed_notes="每月第二個週五晚上留給彼此。",
                    evidence_json=[],
                    dedupe_key=f"wishlist:{self.monthly_wish_id}:cadence:每月第二個週五晚上留給彼此。",
                    target_wishlist_item_id=self.monthly_wish_id,
                    reviewed_at=utcnow(),
                )
            )
            session.commit()

        calls = {"count": 0}
        original = love_map.generate_shared_future_refinement_cadence

        async def fake_generate_shared_future_refinement_cadence(*, title, notes, created_at):
            calls["count"] += 1
            return {"proposed_notes": "每月第一個週末先確認那一晚。"}

        love_map.generate_shared_future_refinement_cadence = fake_generate_shared_future_refinement_cadence
        try:
            response = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.monthly_wish_id}/generate-cadence"
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
            self.assertEqual(calls["count"], 0)
        finally:
            love_map.generate_shared_future_refinement_cadence = original

    def test_generate_cadence_refinement_does_not_block_next_step_generation(self) -> None:
        self.current_user_id = self.alice_id
        with Session(self.engine) as session:
            session.add(
                RelationshipKnowledgeSuggestion(
                    user_id=self.alice_id,
                    partner_id=self.bob_id,
                    section="shared_future_refinement",
                    status="dismissed",
                    generator_version="shared_future_refinement_cadence_v1",
                    proposed_title="",
                    proposed_notes="每月第二個週五晚上留給彼此。",
                    evidence_json=[],
                    dedupe_key=f"wishlist:{self.monthly_wish_id}:cadence:每月第二個週五晚上留給彼此。",
                    target_wishlist_item_id=self.monthly_wish_id,
                    reviewed_at=utcnow(),
                )
            )
            session.commit()

        calls = {"count": 0}
        original = love_map.generate_shared_future_refinement_next_step

        async def fake_generate_shared_future_refinement_next_step(*, title, notes, created_at):
            calls["count"] += 1
            return {"proposed_notes": "先把每月第二個週五晚上固定留給彼此。"}

        love_map.generate_shared_future_refinement_next_step = fake_generate_shared_future_refinement_next_step
        try:
            response = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.monthly_wish_id}/generate"
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()), 1)
            self.assertEqual(calls["count"], 1)
        finally:
            love_map.generate_shared_future_refinement_next_step = original

    def test_accept_refinement_appends_next_step_to_target_notes(self) -> None:
        with Session(self.engine) as session:
            row = RelationshipKnowledgeSuggestion(
                user_id=self.alice_id,
                partner_id=self.bob_id,
                section="shared_future_refinement",
                status="pending",
                generator_version="shared_future_refinement_next_step_v1",
                proposed_title="",
                proposed_notes="先把每月第二個週五晚上固定留給彼此。",
                evidence_json=[],
                dedupe_key=f"wishlist:{self.monthly_wish_id}:next-step:先把每月第二個週五晚上固定留給彼此。",
                target_wishlist_item_id=self.monthly_wish_id,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            suggestion_id = row.id

        self.current_user_id = self.alice_id
        response = self.client.post(f"/api/love-map/suggestions/{suggestion_id}/accept")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], str(self.monthly_wish_id))
        self.assertIn("下一步：先把每月第二個週五晚上固定留給彼此。", payload["notes"])

        with Session(self.engine) as session:
            suggestion = session.get(RelationshipKnowledgeSuggestion, suggestion_id)
            wishlist = session.get(WishlistItem, self.monthly_wish_id)
            self.assertIsNotNone(suggestion)
            self.assertIsNotNone(wishlist)
            assert suggestion is not None
            assert wishlist is not None
            self.assertEqual(suggestion.status, "accepted")
            self.assertEqual(suggestion.accepted_wishlist_item_id, self.monthly_wish_id)
            self.assertIn("下一步：先把每月第二個週五晚上固定留給彼此。", wishlist.notes)

    def test_accept_refinement_does_not_duplicate_existing_next_step_line(self) -> None:
        existing_line = "下一步：先把每月第二個週五晚上固定留給彼此。"
        with Session(self.engine) as session:
            wishlist = session.get(WishlistItem, self.monthly_wish_id)
            assert wishlist is not None
            wishlist.notes = f"{wishlist.notes}\n\n{existing_line}"
            session.add(wishlist)
            session.add(
                RelationshipKnowledgeSuggestion(
                    user_id=self.alice_id,
                    partner_id=self.bob_id,
                    section="shared_future_refinement",
                    status="pending",
                    generator_version="shared_future_refinement_next_step_v1",
                    proposed_title="",
                    proposed_notes="先把每月第二個週五晚上固定留給彼此。",
                    evidence_json=[],
                    dedupe_key=f"wishlist:{self.monthly_wish_id}:next-step:先把每月第二個週五晚上固定留給彼此。",
                    target_wishlist_item_id=self.monthly_wish_id,
                )
            )
            session.commit()
            suggestion_id = session.exec(
                select(RelationshipKnowledgeSuggestion.id).where(
                    RelationshipKnowledgeSuggestion.target_wishlist_item_id == self.monthly_wish_id,
                    RelationshipKnowledgeSuggestion.status == "pending",
                )
            ).first()
            self.assertIsNotNone(suggestion_id)

        self.current_user_id = self.alice_id
        response = self.client.post(f"/api/love-map/suggestions/{suggestion_id}/accept")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["notes"].count(existing_line), 1)

    def test_accept_cadence_refinement_appends_cadence_to_target_notes(self) -> None:
        with Session(self.engine) as session:
            row = RelationshipKnowledgeSuggestion(
                user_id=self.alice_id,
                partner_id=self.bob_id,
                section="shared_future_refinement",
                status="pending",
                generator_version="shared_future_refinement_cadence_v1",
                proposed_title="",
                proposed_notes="每月第二個週五晚上留給彼此。",
                evidence_json=[],
                dedupe_key=f"wishlist:{self.monthly_wish_id}:cadence:每月第二個週五晚上留給彼此。",
                target_wishlist_item_id=self.monthly_wish_id,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            suggestion_id = row.id

        self.current_user_id = self.alice_id
        response = self.client.post(f"/api/love-map/suggestions/{suggestion_id}/accept")
        self.assertEqual(response.status_code, 200)
        self.assertIn("節奏：每月第二個週五晚上留給彼此。", response.json()["notes"])

    def test_accept_cadence_refinement_does_not_duplicate_existing_line(self) -> None:
        existing_line = "節奏：每月第二個週五晚上留給彼此。"
        with Session(self.engine) as session:
            wishlist = session.get(WishlistItem, self.monthly_wish_id)
            assert wishlist is not None
            wishlist.notes = f"{wishlist.notes}\n\n{existing_line}"
            session.add(wishlist)
            session.add(
                RelationshipKnowledgeSuggestion(
                    user_id=self.alice_id,
                    partner_id=self.bob_id,
                    section="shared_future_refinement",
                    status="pending",
                    generator_version="shared_future_refinement_cadence_v1",
                    proposed_title="",
                    proposed_notes="每月第二個週五晚上留給彼此。",
                    evidence_json=[],
                    dedupe_key=f"wishlist:{self.monthly_wish_id}:cadence:每月第二個週五晚上留給彼此。",
                    target_wishlist_item_id=self.monthly_wish_id,
                )
            )
            session.commit()
            suggestion_id = session.exec(
                select(RelationshipKnowledgeSuggestion.id).where(
                    RelationshipKnowledgeSuggestion.target_wishlist_item_id == self.monthly_wish_id,
                    RelationshipKnowledgeSuggestion.status == "pending",
                    RelationshipKnowledgeSuggestion.generator_version == "shared_future_refinement_cadence_v1",
                )
            ).first()
            self.assertIsNotNone(suggestion_id)

        self.current_user_id = self.alice_id
        response = self.client.post(f"/api/love-map/suggestions/{suggestion_id}/accept")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["notes"].count(existing_line), 1)

    def test_dismiss_is_owner_scoped_and_pending_queue_is_personal_only(self) -> None:
        with Session(self.engine) as session:
            dismiss_row = RelationshipKnowledgeSuggestion(
                user_id=self.alice_id,
                partner_id=self.bob_id,
                section="shared_future_refinement",
                status="pending",
                generator_version="shared_future_refinement_next_step_v1",
                proposed_title="",
                proposed_notes="先查今年京都紅葉預測和機票。",
                evidence_json=[],
                dedupe_key=f"wishlist:{self.kyoto_wish_id}:next-step:先查今年京都紅葉預測和機票。",
                target_wishlist_item_id=self.kyoto_wish_id,
            )
            protected_row = RelationshipKnowledgeSuggestion(
                user_id=self.alice_id,
                partner_id=self.bob_id,
                section="shared_future_refinement",
                status="pending",
                generator_version="shared_future_refinement_next_step_v1",
                proposed_title="",
                proposed_notes="先把每月第二個週五晚上固定留給彼此。",
                evidence_json=[],
                dedupe_key=f"wishlist:{self.monthly_wish_id}:next-step:先把每月第二個週五晚上固定留給彼此。",
                target_wishlist_item_id=self.monthly_wish_id,
            )
            session.add(dismiss_row)
            session.add(protected_row)
            session.commit()
            session.refresh(dismiss_row)
            session.refresh(protected_row)

        self.current_user_id = self.alice_id
        pending_response = self.client.get("/api/love-map/suggestions/shared-future/refinements")
        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual(len(pending_response.json()), 2)

        dismiss_response = self.client.post(f"/api/love-map/suggestions/{dismiss_row.id}/dismiss")
        self.assertEqual(dismiss_response.status_code, 200)
        self.assertEqual(dismiss_response.json()["status"], "dismissed")

        self.current_user_id = self.bob_id
        pending_for_bob = self.client.get("/api/love-map/suggestions/shared-future/refinements")
        self.assertEqual(pending_for_bob.status_code, 200)
        self.assertEqual(pending_for_bob.json(), [])

        deny_accept = self.client.post(f"/api/love-map/suggestions/{protected_row.id}/accept")
        deny_dismiss = self.client.post(f"/api/love-map/suggestions/{protected_row.id}/dismiss")
        self.assertEqual(deny_accept.status_code, 404)
        self.assertEqual(deny_dismiss.status_code, 404)

        self.current_user_id = self.outsider_id
        outsider_generate = self.client.post(
            f"/api/love-map/suggestions/shared-future/refinements/{self.outsider_wish_id}/generate"
        )
        self.assertEqual(outsider_generate.status_code, 403)

    def test_generate_refinement_returns_503_when_ai_provider_fails(self) -> None:
        self.current_user_id = self.alice_id
        original = love_map.generate_shared_future_refinement_next_step

        async def fake_generate_shared_future_refinement_next_step(*, title, notes, created_at):
            raise HavenAIProviderError(
                reason="shared_future_refinement_provider_error",
                retryable=True,
                provider="openai",
            )

        love_map.generate_shared_future_refinement_next_step = fake_generate_shared_future_refinement_next_step
        try:
            response = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.monthly_wish_id}/generate"
            )
            self.assertEqual(response.status_code, 503)
        finally:
            love_map.generate_shared_future_refinement_next_step = original

    def test_generate_cadence_refinement_returns_503_when_ai_provider_fails(self) -> None:
        self.current_user_id = self.alice_id
        original = love_map.generate_shared_future_refinement_cadence

        async def fake_generate_shared_future_refinement_cadence(*, title, notes, created_at):
            raise HavenAIProviderError(
                reason="shared_future_refinement_cadence_provider_error",
                retryable=True,
                provider="openai",
            )

        love_map.generate_shared_future_refinement_cadence = fake_generate_shared_future_refinement_cadence
        try:
            response = self.client.post(
                f"/api/love-map/suggestions/shared-future/refinements/{self.monthly_wish_id}/generate-cadence"
            )
            self.assertEqual(response.status_code, 503)
        finally:
            love_map.generate_shared_future_refinement_cadence = original


if __name__ == "__main__":
    unittest.main()
