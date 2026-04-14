# READ_AUTHZ_MATRIX: GET /api/card-decks/history
# READ_AUTHZ_MATRIX: GET /api/card-decks/history/{session_id}
# READ_AUTHZ_MATRIX: GET /api/card-decks/{deck_id}/draw
# READ_AUTHZ_MATRIX: GET /api/card-decks/history/summary
# READ_AUTHZ_MATRIX: GET /api/card-decks/stats
# READ_AUTHZ_MATRIX: GET /api/cards/
# READ_AUTHZ_MATRIX: GET /api/cards/backlog
# READ_AUTHZ_MATRIX: GET /api/cards/daily-status
# READ_AUTHZ_MATRIX: GET /api/cards/draw
# READ_AUTHZ_MATRIX: GET /api/cards/{card_id}/conversation

import sys
import unittest
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
from app.api.routers import card_decks, cards  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import get_read_session, get_session  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_response import CardResponse, ResponseStatus  # noqa: E402
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402


class CardReadAuthorizationMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(cards.router, prefix="/api/cards")
        app.include_router(card_decks.router, prefix="/api/card-decks")

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
        app.dependency_overrides[get_read_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

        with Session(self.engine) as session:
            user_a = User(email="read-a@example.com", full_name="Read A", hashed_password="hashed")
            user_b = User(email="read-b@example.com", full_name="Read B", hashed_password="hashed")
            user_c = User(email="read-c@example.com", full_name="Read C", hashed_password="hashed")
            user_d = User(email="read-d@example.com", full_name="Read D", hashed_password="hashed")
            user_e = User(email="read-e@example.com", full_name="Read E", hashed_password="hashed")
            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            user_c.partner_id = user_d.id
            user_d.partner_id = user_c.id

            card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Read Matrix Card",
                description="desc",
                question="What happened today?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            card_ab_only = Card(
                category=CardCategory.DAILY_VIBE,
                title="AB Card",
                description="desc",
                question="AB-only prompt?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            card_cd_only = Card(
                category=CardCategory.DAILY_VIBE,
                title="CD Card",
                description="desc",
                question="CD-only prompt?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            deck_draw_id = 777
            card_ab_deck_draw = Card(
                category=CardCategory.DAILY_VIBE,
                title="AB Deck Draw Card",
                description="desc",
                question="AB deck draw prompt?",
                difficulty_level=1,
                deck_id=deck_draw_id,
                is_ai_generated=False,
            )
            card_cd_deck_draw = Card(
                category=CardCategory.DAILY_VIBE,
                title="CD Deck Draw Card",
                description="desc",
                question="CD deck draw prompt?",
                difficulty_level=1,
                deck_id=deck_draw_id,
                is_ai_generated=False,
            )
            session.add(user_a)
            session.add(user_b)
            session.add(user_c)
            session.add(user_d)
            session.add(user_e)
            session.add(card)
            session.add(card_ab_only)
            session.add(card_cd_only)
            session.add(card_ab_deck_draw)
            session.add(card_cd_deck_draw)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(user_c)
            session.refresh(user_d)
            session.refresh(user_e)
            session.refresh(card)
            session.refresh(card_ab_only)
            session.refresh(card_cd_only)
            session.refresh(card_ab_deck_draw)
            session.refresh(card_cd_deck_draw)

            session.add(
                Journal(
                    content="ab deck draw partner journal",
                    user_id=user_b.id,
                    deck_id=deck_draw_id,
                    card_id=card_ab_deck_draw.id,
                )
            )
            session.add(
                Journal(
                    content="cd deck draw partner journal",
                    user_id=user_d.id,
                    deck_id=deck_draw_id,
                    card_id=card_cd_deck_draw.id,
                )
            )
            session.commit()

            session_ab = CardSession(
                card_id=card.id,
                creator_id=user_a.id,
                partner_id=user_b.id,
                category=card.category.value,
                mode=CardSessionMode.DECK,
                status=CardSessionStatus.COMPLETED,
            )
            session_cd = CardSession(
                card_id=card.id,
                creator_id=user_c.id,
                partner_id=user_d.id,
                category=card.category.value,
                mode=CardSessionMode.DECK,
                status=CardSessionStatus.COMPLETED,
            )
            session_ab_extra = CardSession(
                card_id=card_ab_only.id,
                creator_id=user_a.id,
                partner_id=user_b.id,
                category=card_ab_only.category.value,
                mode=CardSessionMode.DECK,
                status=CardSessionStatus.COMPLETED,
            )
            session.add(session_ab)
            session.add(session_cd)
            session.add(session_ab_extra)
            session.commit()
            session.refresh(session_ab)
            session.refresh(session_cd)
            session.refresh(session_ab_extra)

            session.add(
                CardResponse(
                    card_id=card.id,
                    user_id=user_a.id,
                    content="a-answer",
                    session_id=session_ab.id,
                    status=ResponseStatus.REVEALED,
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    card_id=card.id,
                    user_id=user_b.id,
                    content="b-answer",
                    session_id=session_ab.id,
                    status=ResponseStatus.REVEALED,
                    is_initiator=False,
                )
            )
            session.add(
                CardResponse(
                    card_id=card.id,
                    user_id=user_c.id,
                    content="c-answer",
                    session_id=session_cd.id,
                    status=ResponseStatus.REVEALED,
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    card_id=card.id,
                    user_id=user_d.id,
                    content="d-answer",
                    session_id=session_cd.id,
                    status=ResponseStatus.REVEALED,
                    is_initiator=False,
                )
            )
            session.add(
                CardResponse(
                    card_id=card_ab_only.id,
                    user_id=user_a.id,
                    content="a-answer-2",
                    session_id=session_ab_extra.id,
                    status=ResponseStatus.REVEALED,
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    card_id=card_ab_only.id,
                    user_id=user_b.id,
                    content="b-answer-2",
                    session_id=session_ab_extra.id,
                    status=ResponseStatus.REVEALED,
                    is_initiator=False,
                )
            )
            session.add(
                CardResponse(
                    card_id=card_ab_only.id,
                    user_id=user_b.id,
                    content="b-backlog",
                    session_id=None,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    card_id=card_cd_only.id,
                    user_id=user_d.id,
                    content="d-backlog",
                    session_id=None,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.commit()

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.user_c_id = user_c.id
            self.user_d_id = user_d.id
            self.user_e_id = user_e.id
            self.card_id = card.id
            self.card_ab_only_id = card_ab_only.id
            self.card_cd_only_id = card_cd_only.id
            self.deck_draw_id = deck_draw_id
            self.card_ab_deck_draw_id = card_ab_deck_draw.id
            self.card_cd_deck_draw_id = card_cd_deck_draw.id
            self.session_ab_id = session_ab.id
            self.session_cd_id = session_cd.id
            self.session_ab_extra_id = session_ab_extra.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_conversation_allows_pair_member_for_owned_session(self) -> None:
        response = self.client.get(
            f"/api/cards/{self.card_id}/conversation",
            params={"session_id": str(self.session_ab_id)},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertEqual({item["user_id"] for item in payload}, {str(self.user_a_id), str(self.user_b_id)})
        self.assertEqual({item["session_id"] for item in payload}, {str(self.session_ab_id)})

    def test_conversation_rejects_foreign_session_data_leak(self) -> None:
        self.current_user_id = self.user_c_id
        response = self.client.get(
            f"/api/cards/{self.card_id}/conversation",
            params={"session_id": str(self.session_ab_id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_conversation_without_session_id_isolated_to_current_pair(self) -> None:
        self.current_user_id = self.user_c_id
        response = self.client.get(f"/api/cards/{self.card_id}/conversation")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertEqual({item["user_id"] for item in payload}, {str(self.user_c_id), str(self.user_d_id)})
        self.assertEqual({item["session_id"] for item in payload}, {str(self.session_cd_id)})

    def test_deck_history_isolated_to_current_pair(self) -> None:
        self.current_user_id = self.user_c_id
        response = self.client.get("/api/card-decks/history")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["session_id"], str(self.session_cd_id))
        self.assertNotEqual(payload[0]["session_id"], str(self.session_ab_id))

    def test_deck_history_detail_allows_pair_member_for_owned_session(self) -> None:
        response = self.client.get(f"/api/card-decks/history/{self.session_ab_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["session_id"], str(self.session_ab_id))
        self.assertEqual(payload["my_answer"], "a-answer")
        self.assertEqual(payload["partner_answer"], "b-answer")

    def test_deck_history_detail_rejects_foreign_session(self) -> None:
        self.current_user_id = self.user_c_id
        response = self.client.get(f"/api/card-decks/history/{self.session_ab_id}")
        self.assertEqual(response.status_code, 404)

    def test_deck_history_detail_returns_not_found_for_unpaired_user(self) -> None:
        self.current_user_id = self.user_e_id
        response = self.client.get(f"/api/card-decks/history/{self.session_ab_id}")
        self.assertEqual(response.status_code, 404)

    def test_draw_card_from_deck_isolated_to_current_pair_partner_journal(self) -> None:
        response_a = self.client.get(f"/api/card-decks/{self.deck_draw_id}/draw")
        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_a.json()["id"], str(self.card_ab_deck_draw_id))

        self.current_user_id = self.user_c_id
        response_c = self.client.get(f"/api/card-decks/{self.deck_draw_id}/draw")
        self.assertEqual(response_c.status_code, 200)
        self.assertEqual(response_c.json()["id"], str(self.card_cd_deck_draw_id))

    def test_deck_history_summary_isolated_to_current_pair(self) -> None:
        self.current_user_id = self.user_c_id
        response = self.client.get("/api/card-decks/history/summary")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_records"], 1)
        self.assertEqual(payload["top_category_count"], 1)

    def test_deck_history_returns_empty_for_unrelated_unpaired_user(self) -> None:
        self.current_user_id = self.user_e_id
        history_response = self.client.get("/api/card-decks/history")
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_response.json(), [])

        summary_response = self.client.get("/api/card-decks/history/summary")
        self.assertEqual(summary_response.status_code, 200)
        summary_payload = summary_response.json()
        self.assertEqual(summary_payload["total_records"], 0)
        self.assertEqual(summary_payload["top_category_count"], 0)
        self.assertIsNone(summary_payload["top_category"])

    def test_read_cards_requires_authenticated_context_and_supports_filter(self) -> None:
        response_all = self.client.get("/api/cards/")
        self.assertEqual(response_all.status_code, 200)
        all_ids = {item["id"] for item in response_all.json()}
        self.assertIn(str(self.card_id), all_ids)
        self.assertIn(str(self.card_ab_only_id), all_ids)
        self.assertIn(str(self.card_cd_only_id), all_ids)

        filtered = self.client.get("/api/cards/", params={"category": CardCategory.DAILY_VIBE.value})
        self.assertEqual(filtered.status_code, 200)
        filtered_payload = filtered.json()
        self.assertGreaterEqual(len(filtered_payload), 3)
        self.assertTrue(all(item["category"] == CardCategory.DAILY_VIBE.value for item in filtered_payload))

    def test_backlog_isolated_to_current_pair(self) -> None:
        response = self.client.get("/api/cards/backlog")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        ids = {item["id"] for item in payload}
        self.assertIn(str(self.card_ab_only_id), ids)
        self.assertNotIn(str(self.card_cd_only_id), ids)

    def test_backlog_for_other_pair_excludes_foreign_cards(self) -> None:
        self.current_user_id = self.user_c_id
        response = self.client.get("/api/cards/backlog")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        ids = {item["id"] for item in payload}
        self.assertIn(str(self.card_cd_only_id), ids)
        self.assertNotIn(str(self.card_ab_only_id), ids)

    def test_backlog_for_unpaired_user_returns_empty(self) -> None:
        self.current_user_id = self.user_e_id
        response = self.client.get("/api/cards/backlog")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_daily_status_ignores_foreign_pair_daily_session(self) -> None:
        with Session(self.engine) as session:
            foreign_daily_session = CardSession(
                card_id=self.card_ab_only_id,
                creator_id=self.user_a_id,
                partner_id=self.user_b_id,
                category=CardCategory.DAILY_VIBE.value,
                mode=CardSessionMode.DAILY_RITUAL,
                status=CardSessionStatus.PENDING,
            )
            session.add(foreign_daily_session)
            session.commit()

        self.current_user_id = self.user_c_id
        response = self.client.get("/api/cards/daily-status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["state"], "IDLE")
        self.assertIsNone(payload["card"])
        self.assertIsNone(payload["session_id"])

    def test_daily_status_returns_current_pair_daily_session(self) -> None:
        with Session(self.engine) as session:
            foreign_daily_session = CardSession(
                card_id=self.card_ab_only_id,
                creator_id=self.user_a_id,
                partner_id=self.user_b_id,
                category=CardCategory.DAILY_VIBE.value,
                mode=CardSessionMode.DAILY_RITUAL,
                status=CardSessionStatus.PENDING,
            )
            current_pair_daily_session = CardSession(
                card_id=self.card_cd_only_id,
                creator_id=self.user_c_id,
                partner_id=self.user_d_id,
                category=CardCategory.DAILY_VIBE.value,
                mode=CardSessionMode.DAILY_RITUAL,
                status=CardSessionStatus.PENDING,
            )
            session.add(foreign_daily_session)
            session.add(current_pair_daily_session)
            session.commit()
            session.refresh(current_pair_daily_session)
            expected_session_id = current_pair_daily_session.id

        self.current_user_id = self.user_c_id
        response = self.client.get("/api/cards/daily-status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["session_id"], str(expected_session_id))
        self.assertEqual(payload["card"]["id"], str(self.card_cd_only_id))

    def test_draw_library_backlog_isolated_to_current_pair(self) -> None:
        response_a = self.client.get(
            "/api/cards/draw",
            params={"source": "library"},
        )
        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_a.json()["id"], str(self.card_ab_only_id))

        self.current_user_id = self.user_c_id
        response_c = self.client.get(
            "/api/cards/draw",
            params={"source": "library"},
        )
        self.assertEqual(response_c.status_code, 200)
        self.assertEqual(response_c.json()["id"], str(self.card_cd_only_id))

    def test_deck_stats_isolated_by_current_user(self) -> None:
        response_a = self.client.get("/api/card-decks/stats")
        self.assertEqual(response_a.status_code, 200)
        stats_a = next(item for item in response_a.json() if item["category"] == CardCategory.DAILY_VIBE.value)
        self.assertEqual(stats_a["answered_cards"], 2)

        self.current_user_id = self.user_c_id
        response_c = self.client.get("/api/card-decks/stats")
        self.assertEqual(response_c.status_code, 200)
        stats_c = next(item for item in response_c.json() if item["category"] == CardCategory.DAILY_VIBE.value)
        self.assertEqual(stats_c["answered_cards"], 1)

    def test_conversation_excludes_soft_deleted_responses(self) -> None:
        with Session(self.engine) as session:
            target = session.exec(
                select(CardResponse).where(
                    CardResponse.session_id == self.session_ab_id,
                    CardResponse.user_id == self.user_b_id,
                )
            ).first()
            self.assertIsNotNone(target)
            assert target is not None
            target.deleted_at = utcnow()
            session.add(target)
            session.commit()

        response = self.client.get(
            f"/api/cards/{self.card_id}/conversation",
            params={"session_id": str(self.session_ab_id)},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["user_id"], str(self.user_a_id))

    def test_backlog_excludes_soft_deleted_partner_pending_response(self) -> None:
        with Session(self.engine) as session:
            target = session.exec(
                select(CardResponse).where(
                    CardResponse.card_id == self.card_ab_only_id,
                    CardResponse.user_id == self.user_b_id,
                    CardResponse.session_id.is_(None),
                    CardResponse.status == ResponseStatus.PENDING,
                )
            ).first()
            self.assertIsNotNone(target)
            assert target is not None
            target.deleted_at = utcnow()
            session.add(target)
            session.commit()

        response = self.client.get("/api/cards/backlog")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        ids = {item["id"] for item in payload}
        self.assertNotIn(str(self.card_ab_only_id), ids)

    def test_history_summary_and_stats_exclude_soft_deleted_sessions(self) -> None:
        with Session(self.engine) as session:
            target_session = session.get(CardSession, self.session_ab_extra_id)
            self.assertIsNotNone(target_session)
            assert target_session is not None
            target_session.deleted_at = utcnow()
            session.add(target_session)
            session.commit()

        history_response = self.client.get("/api/card-decks/history")
        self.assertEqual(history_response.status_code, 200)
        history_payload = history_response.json()
        self.assertEqual(len(history_payload), 1)
        self.assertEqual(history_payload[0]["session_id"], str(self.session_ab_id))

        summary_response = self.client.get("/api/card-decks/history/summary")
        self.assertEqual(summary_response.status_code, 200)
        summary_payload = summary_response.json()
        self.assertEqual(summary_payload["total_records"], 1)
        self.assertEqual(summary_payload["top_category_count"], 1)

        stats_response = self.client.get("/api/card-decks/stats")
        self.assertEqual(stats_response.status_code, 200)
        stats_payload = next(
            item for item in stats_response.json() if item["category"] == CardCategory.DAILY_VIBE.value
        )
        self.assertEqual(stats_payload["answered_cards"], 1)


if __name__ == "__main__":
    unittest.main()
