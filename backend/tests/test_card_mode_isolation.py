import sys
import unittest
from pathlib import Path
from typing import Generator
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

# Ensure `import app...` works when running from repository root.
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
from app.models.user import User  # noqa: E402
from app.services.rate_limit import reset_rate_limit_state_for_tests  # noqa: E402


class CardModeIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_rate_limit_state_for_tests()
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
                raise RuntimeError("current_user_id is not set in test setup")
            with Session(self.engine) as session:
                user = session.get(User, self.current_user_id)
                if not user:
                    raise RuntimeError("test user not found")
                return user

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_read_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user

        self.client = TestClient(app)

        with Session(self.engine) as session:
            self.user_a = User(
                email="alpha@example.com",
                full_name="Alpha",
                hashed_password="hashed",
            )
            self.user_b = User(
                email="beta@example.com",
                full_name="Beta",
                hashed_password="hashed",
            )
            self.user_c = User(
                email="gamma@example.com",
                full_name="Gamma",
                hashed_password="hashed",
            )
            self.user_a.partner_id = self.user_b.id
            self.user_b.partner_id = self.user_a.id

            self.card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Daily Card",
                description="desc",
                question="How do you feel today?",
                difficulty_level=1,
                is_ai_generated=False,
            )

            session.add(self.user_a)
            session.add(self.user_b)
            session.add(self.user_c)
            session.add(self.card)
            session.commit()

            session.refresh(self.user_a)
            session.refresh(self.user_b)
            session.refresh(self.user_c)
            session.refresh(self.card)

        self.current_user_id = self.user_a.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()
        reset_rate_limit_state_for_tests()

    def _create_session(
        self,
        *,
        mode: CardSessionMode,
        status: CardSessionStatus,
        card_id,
        creator_id,
        partner_id,
    ) -> CardSession:
        with Session(self.engine) as session:
            card_session = CardSession(
                card_id=card_id,
                creator_id=creator_id,
                partner_id=partner_id,
                category=CardCategory.DAILY_VIBE.value,
                mode=mode,
                status=status,
                created_at=utcnow(),
            )
            session.add(card_session)
            session.commit()
            session.refresh(card_session)
            return card_session

    def test_deck_draw_ignores_daily_sessions(self) -> None:
        daily_session = self._create_session(
            mode=CardSessionMode.DAILY_RITUAL,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        response = self.client.post(
            "/api/card-decks/draw",
            params={"category": "DAILY_VIBE"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotEqual(payload["id"], str(daily_session.id))
        self.assertEqual(payload["mode"], CardSessionMode.DECK.value)

    def test_deck_draw_does_not_exclude_cards_answered_in_daily_mode(self) -> None:
        daily_session = self._create_session(
            mode=CardSessionMode.DAILY_RITUAL,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        with Session(self.engine) as session:
            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=self.user_a.id,
                    content="daily answered",
                    session_id=daily_session.id,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.commit()

        response = self.client.post(
            "/api/card-decks/draw",
            params={"category": "DAILY_VIBE"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], CardSessionMode.DECK.value)
        self.assertEqual(payload["card_id"], str(self.card.id))

    def test_daily_status_ignores_deck_sessions(self) -> None:
        self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        response = self.client.get("/api/cards/daily-status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["state"], "IDLE")
        self.assertIsNone(payload["card"])
        self.assertIsNone(payload["session_id"])

    def test_daily_status_includes_session_id(self) -> None:
        daily_session = self._create_session(
            mode=CardSessionMode.DAILY_RITUAL,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        response = self.client.get("/api/cards/daily-status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["state"], "IDLE")
        self.assertIsNotNone(payload["card"])
        self.assertEqual(payload["session_id"], str(daily_session.id))

    def test_deck_respond_rejects_daily_session(self) -> None:
        daily_session = self._create_session(
            mode=CardSessionMode.DAILY_RITUAL,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        response = self.client.post(
            f"/api/card-decks/respond/{daily_session.id}",
            params={"content": "hello"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("不是牌組模式", response.json()["detail"])

    def test_deck_respond_accepts_json_body(self) -> None:
        deck_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        response = self.client.post(
            f"/api/card-decks/respond/{deck_session.id}",
            json={"content": "body answer"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["session_status"], CardSessionStatus.WAITING_PARTNER.value)

        with Session(self.engine) as session:
            saved = session.exec(
                select(CardResponse).where(
                    CardResponse.session_id == deck_session.id,
                    CardResponse.user_id == self.user_a.id,
                )
            ).first()
            self.assertIsNotNone(saved)
            self.assertEqual(saved.content, "body answer")

    def test_deck_respond_rejects_non_participant(self) -> None:
        deck_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )
        self.current_user_id = self.user_c.id

        response = self.client.post(
            f"/api/card-decks/respond/{deck_session.id}",
            json={"content": "I should not be able to respond"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("沒有權限", response.json()["detail"])

    def test_cards_respond_does_not_mutate_deck_response(self) -> None:
        deck_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )
        daily_session = self._create_session(
            mode=CardSessionMode.DAILY_RITUAL,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        with Session(self.engine) as session:
            deck_response = CardResponse(
                card_id=self.card.id,
                user_id=self.user_a.id,
                content="deck content",
                session_id=deck_session.id,
                status=ResponseStatus.PENDING,
                is_initiator=True,
            )
            session.add(deck_response)
            session.commit()
            session.refresh(deck_response)
            deck_response_id = deck_response.id

        response = self.client.post(
            "/api/cards/respond",
            json={"card_id": str(self.card.id), "content": "daily content"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["session_id"], str(daily_session.id))
        self.assertEqual(payload["content"], "daily content")

        with Session(self.engine) as session:
            original_deck_response = session.get(CardResponse, deck_response_id)
            self.assertIsNotNone(original_deck_response)
            self.assertEqual(original_deck_response.content, "deck content")
            self.assertEqual(original_deck_response.session_id, deck_session.id)

            linked_daily_response = session.exec(
                select(CardResponse).where(
                    CardResponse.user_id == self.user_a.id,
                    CardResponse.session_id == daily_session.id,
                )
            ).first()
            self.assertIsNotNone(linked_daily_response)
            self.assertEqual(linked_daily_response.content, "daily content")

    def test_daily_status_fallback_excludes_deck_responses(self) -> None:
        self._create_session(
            mode=CardSessionMode.DAILY_RITUAL,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )
        deck_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        with Session(self.engine) as session:
            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=self.user_a.id,
                    content="deck-only content",
                    session_id=deck_session.id,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.commit()

        response = self.client.get("/api/cards/daily-status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["state"], "IDLE")
        self.assertIsNotNone(payload["card"])

    def test_response_unique_per_session_user(self) -> None:
        deck_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        with Session(self.engine) as session:
            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=self.user_a.id,
                    content="first",
                    session_id=deck_session.id,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.commit()

            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=self.user_a.id,
                    content="duplicate",
                    session_id=deck_session.id,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()

    def test_draw_rejects_invalid_category(self) -> None:
        response = self.client.get("/api/cards/draw", params={"category": "UNKNOWN_CATEGORY"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("無效的分類", response.json()["detail"])

    def test_read_cards_rejects_invalid_category(self) -> None:
        response = self.client.get("/api/cards/", params={"category": "UNKNOWN_CATEGORY"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("無效的分類", response.json()["detail"])

    def test_draw_rejects_invalid_source_enum(self) -> None:
        response = self.client.get("/api/cards/draw", params={"source": "unsupported_source"})
        self.assertEqual(response.status_code, 422)

    def test_draw_returns_depth_level_and_tags(self) -> None:
        response = self.client.get("/api/cards/draw")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn("depth_level", payload)
        self.assertIn("tags", payload)
        self.assertEqual(payload["depth_level"], 1)
        self.assertEqual(payload["tags"], [])

    def test_library_draw_prefers_low_depth_for_new_user(self) -> None:
        with Session(self.engine) as session:
            deep_card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Deep Library Card",
                description="desc",
                question="Deep question",
                difficulty_level=1,
                depth_level=3,
                is_ai_generated=False,
            )
            session.add(deep_card)
            session.commit()

        response = self.client.get("/api/cards/draw", params={"category": "DAILY_VIBE", "source": "library"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["depth_level"], 1)

    def test_library_draw_fallbacks_to_higher_depth_when_low_depth_exhausted(self) -> None:
        deep_card_id = None
        with Session(self.engine) as session:
            deep_card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Deep Library Card",
                description="desc",
                question="Deep question",
                difficulty_level=1,
                depth_level=3,
                is_ai_generated=False,
            )
            session.add(deep_card)
            session.commit()
            session.refresh(deep_card)
            deep_card_id = deep_card.id

            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=self.user_a.id,
                    content="answered low depth",
                    session_id=None,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.commit()

        response = self.client.get("/api/cards/draw", params={"category": "DAILY_VIBE", "source": "library"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], str(deep_card_id))
        self.assertEqual(payload["depth_level"], 3)

    def test_deck_draw_prefers_low_depth_for_new_user(self) -> None:
        with Session(self.engine) as session:
            deep_card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Deep Deck Card",
                description="desc",
                question="Deep deck question",
                difficulty_level=1,
                depth_level=3,
                is_ai_generated=False,
            )
            session.add(deep_card)
            session.commit()

        response = self.client.post("/api/card-decks/draw", params={"category": "DAILY_VIBE"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["card"]["depth_level"], 1)

    def test_deck_draw_fallbacks_to_higher_depth_when_low_depth_exhausted(self) -> None:
        deep_card_id = None
        with Session(self.engine) as session:
            deep_card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Deep Deck Card",
                description="desc",
                question="Deep deck question",
                difficulty_level=1,
                depth_level=3,
                is_ai_generated=False,
            )
            session.add(deep_card)
            session.commit()
            session.refresh(deep_card)
            deep_card_id = deep_card.id

        completed_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.COMPLETED,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )
        with Session(self.engine) as session:
            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=self.user_a.id,
                    content="answered low depth",
                    session_id=completed_session.id,
                    status=ResponseStatus.REVEALED,
                    is_initiator=True,
                )
            )
            session.commit()

        response = self.client.post("/api/card-decks/draw", params={"category": "DAILY_VIBE"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["card_id"], str(deep_card_id))
        self.assertEqual(payload["card"]["depth_level"], 3)

    def test_deck_history_includes_depth_level(self) -> None:
        with Session(self.engine) as session:
            deep_card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Deep Card",
                description="desc",
                question="A deeper question",
                difficulty_level=1,
                depth_level=3,
                is_ai_generated=False,
            )
            session.add(deep_card)
            session.commit()
            session.refresh(deep_card)

        deck_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.COMPLETED,
            card_id=deep_card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        with Session(self.engine) as session:
            session.add(
                CardResponse(
                    card_id=deep_card.id,
                    user_id=self.user_a.id,
                    content="my answer",
                    session_id=deck_session.id,
                    status=ResponseStatus.REVEALED,
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    card_id=deep_card.id,
                    user_id=self.user_b.id,
                    content="partner answer",
                    session_id=deck_session.id,
                    status=ResponseStatus.REVEALED,
                    is_initiator=False,
                )
            )
            session.commit()

        response = self.client.get("/api/card-decks/history")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload), 1)

        latest = payload[0]
        self.assertEqual(latest["session_id"], str(deck_session.id))
        self.assertIn("depth_level", latest)
        self.assertEqual(latest["depth_level"], 3)

    def test_deck_stats_returns_all_categories(self) -> None:
        response = self.client.get("/api/card-decks/stats")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        categories = {item["category"] for item in payload}
        expected_categories = {category.value for category in CardCategory}
        self.assertSetEqual(categories, expected_categories)

        counts_by_category = {item["category"]: item["total_cards"] for item in payload}
        self.assertGreaterEqual(counts_by_category["DAILY_VIBE"], 1)

    def test_deck_stats_progress_ignores_daily_mode_responses(self) -> None:
        deck_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )
        daily_session = self._create_session(
            mode=CardSessionMode.DAILY_RITUAL,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        with Session(self.engine) as session:
            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=self.user_a.id,
                    content="deck answer",
                    session_id=deck_session.id,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=self.user_a.id,
                    content="daily answer",
                    session_id=daily_session.id,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.commit()

        response = self.client.get("/api/card-decks/stats")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        daily_vibe_stats = next(item for item in payload if item["category"] == CardCategory.DAILY_VIBE.value)
        self.assertEqual(daily_vibe_stats["total_cards"], 1)
        self.assertEqual(daily_vibe_stats["answered_cards"], 1)
        self.assertEqual(daily_vibe_stats["completion_rate"], 100.0)

    def test_cards_reveal_email_notification_sent_once(self) -> None:
        with Session(self.engine) as session:
            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=self.user_b.id,
                    content="partner first",
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.commit()

        with patch("app.api.routers.cards.queue_partner_notification") as mock_queue:
            response = self.client.post(
                "/api/cards/respond",
                json={"card_id": str(self.card.id), "content": "my first answer"},
            )
            self.assertEqual(response.status_code, 200)

            response_update = self.client.post(
                "/api/cards/respond",
                json={"card_id": str(self.card.id), "content": "my edited answer"},
            )
            self.assertEqual(response_update.status_code, 200)

            self.assertEqual(mock_queue.call_count, 1)
            kwargs = mock_queue.call_args.kwargs
            self.assertEqual(kwargs["action_type"], "card")
            self.assertTrue(str(kwargs["dedupe_key"]).startswith("card_revealed:"))

    def test_cards_waiting_email_notification_sent_once(self) -> None:
        with patch("app.api.routers.cards.queue_partner_notification") as mock_queue:
            response = self.client.post(
                "/api/cards/respond",
                json={"card_id": str(self.card.id), "content": "my first answer"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], ResponseStatus.PENDING.value)

            response_update = self.client.post(
                "/api/cards/respond",
                json={"card_id": str(self.card.id), "content": "my edited answer"},
            )
            self.assertEqual(response_update.status_code, 200)

            self.assertEqual(mock_queue.call_count, 1)
            kwargs = mock_queue.call_args.kwargs
            self.assertEqual(kwargs["action_type"], "card")
            self.assertTrue(str(kwargs["dedupe_key"]).startswith("card_waiting:"))

    def test_cards_respond_rate_limited_for_new_responses(self) -> None:
        with Session(self.engine) as session:
            second_card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Second Card",
                description="desc",
                question="Another question?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            session.add(second_card)
            session.commit()
            session.refresh(second_card)

        with patch("app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_COUNT", 1), patch(
            "app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS", 3600
        ):
            first = self.client.post(
                "/api/cards/respond",
                json={"card_id": str(self.card.id), "content": "first answer"},
            )
            second = self.client.post(
                "/api/cards/respond",
                json={"card_id": str(second_card.id), "content": "second answer"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("卡片回答過於頻繁", second.json()["detail"])
        self.assertIn("Retry-After", second.headers)
        self.assertEqual(second.headers.get("X-RateLimit-Scope"), "user")
        self.assertEqual(second.headers.get("X-RateLimit-Action"), "card_response_create")
        self.assertGreaterEqual(int(second.headers["Retry-After"]), 1)

    def test_cards_respond_edit_not_blocked_by_rate_limit(self) -> None:
        with patch("app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_COUNT", 1), patch(
            "app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS", 3600
        ):
            first = self.client.post(
                "/api/cards/respond",
                json={"card_id": str(self.card.id), "content": "first answer"},
            )
            update = self.client.post(
                "/api/cards/respond",
                json={"card_id": str(self.card.id), "content": "edited answer"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["content"], "edited answer")

    def test_cards_respond_rate_limited_by_ip_dimension(self) -> None:
        with Session(self.engine) as session:
            second_card = Card(
                category=CardCategory.DAILY_VIBE,
                title="IP Card",
                description="desc",
                question="IP question?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            session.add(second_card)
            session.commit()
            session.refresh(second_card)

        with patch("app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_COUNT", 100), patch(
            "app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS", 3600
        ), patch("app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_IP_COUNT", 1), patch(
            "app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_DEVICE_COUNT", 100
        ), patch("app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_PARTNER_PAIR_COUNT", 100):
            first = self.client.post(
                "/api/cards/respond",
                json={"card_id": str(self.card.id), "content": "first ip answer"},
                headers={"x-forwarded-for": "203.0.113.41"},
            )
            self.current_user_id = self.user_c.id
            second = self.client.post(
                "/api/cards/respond",
                json={"card_id": str(second_card.id), "content": "second ip answer"},
                headers={"x-forwarded-for": "203.0.113.41"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("卡片回答過於頻繁", second.json()["detail"])
        self.assertEqual(second.headers.get("X-RateLimit-Scope"), "ip")
        self.assertEqual(second.headers.get("X-RateLimit-Action"), "card_response_create")

    def test_cards_respond_rate_limited_by_device_dimension(self) -> None:
        with Session(self.engine) as session:
            second_card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Device Card",
                description="desc",
                question="Device question?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            session.add(second_card)
            session.commit()
            session.refresh(second_card)

        with patch("app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_COUNT", 100), patch(
            "app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS", 3600
        ), patch("app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_IP_COUNT", 100), patch(
            "app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_DEVICE_COUNT", 1
        ), patch("app.api.routers.cards.settings.CARD_RESPONSE_RATE_LIMIT_PARTNER_PAIR_COUNT", 100), patch(
            "app.api.routers.cards.settings.RATE_LIMIT_DEVICE_HEADER", "x-device-id"
        ):
            first = self.client.post(
                "/api/cards/respond",
                json={"card_id": str(self.card.id), "content": "first device answer"},
                headers={"x-forwarded-for": "203.0.113.42", "x-device-id": "shared-device-1"},
            )
            self.current_user_id = self.user_c.id
            second = self.client.post(
                "/api/cards/respond",
                json={"card_id": str(second_card.id), "content": "second device answer"},
                headers={"x-forwarded-for": "203.0.113.43", "x-device-id": "shared-device-1"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("卡片回答過於頻繁", second.json()["detail"])
        self.assertEqual(second.headers.get("X-RateLimit-Scope"), "device")
        self.assertEqual(second.headers.get("X-RateLimit-Action"), "card_response_create")

    def test_deck_reveal_email_notification_sent_once(self) -> None:
        deck_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        with Session(self.engine) as session:
            session.add(
                CardResponse(
                    card_id=self.card.id,
                    user_id=self.user_b.id,
                    content="partner first",
                    session_id=deck_session.id,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.commit()

        with patch("app.api.routers.card_decks.queue_partner_notification") as mock_queue:
            response = self.client.post(
                f"/api/card-decks/respond/{deck_session.id}",
                params={"content": "my first answer"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["session_status"], CardSessionStatus.COMPLETED.value)

            response_update = self.client.post(
                f"/api/card-decks/respond/{deck_session.id}",
                params={"content": "my edited answer"},
            )
            self.assertEqual(response_update.status_code, 200)

            self.assertEqual(mock_queue.call_count, 1)
            kwargs = mock_queue.call_args.kwargs
            self.assertEqual(kwargs["action_type"], "card")
            self.assertTrue(str(kwargs["dedupe_key"]).startswith("card_revealed:"))

    def test_deck_waiting_email_notification_sent_once(self) -> None:
        deck_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        with patch("app.api.routers.card_decks.queue_partner_notification") as mock_queue:
            response = self.client.post(
                f"/api/card-decks/respond/{deck_session.id}",
                json={"content": "my first answer"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["session_status"], CardSessionStatus.WAITING_PARTNER.value)

            response_update = self.client.post(
                f"/api/card-decks/respond/{deck_session.id}",
                json={"content": "my edited answer"},
            )
            self.assertEqual(response_update.status_code, 200)

            self.assertEqual(mock_queue.call_count, 1)
            kwargs = mock_queue.call_args.kwargs
            self.assertEqual(kwargs["action_type"], "card")
            self.assertTrue(str(kwargs["dedupe_key"]).startswith("card_waiting:"))

    def test_deck_respond_rate_limited_for_new_responses(self) -> None:
        with Session(self.engine) as session:
            second_card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Deck Rate Limit Card",
                description="desc",
                question="Deck question 2?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            session.add(second_card)
            session.commit()
            session.refresh(second_card)

        first_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )
        second_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=second_card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        with patch("app.api.routers.card_decks.settings.CARD_RESPONSE_RATE_LIMIT_COUNT", 1), patch(
            "app.api.routers.card_decks.settings.CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS", 3600
        ):
            first = self.client.post(
                f"/api/card-decks/respond/{first_session.id}",
                json={"content": "first deck answer"},
            )
            second = self.client.post(
                f"/api/card-decks/respond/{second_session.id}",
                json={"content": "second deck answer"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("卡片回答過於頻繁", second.json()["detail"])
        self.assertIn("Retry-After", second.headers)
        self.assertEqual(second.headers.get("X-RateLimit-Scope"), "user")
        self.assertEqual(second.headers.get("X-RateLimit-Action"), "card_response_create")
        self.assertGreaterEqual(int(second.headers["Retry-After"]), 1)

    def test_deck_respond_edit_not_blocked_by_rate_limit(self) -> None:
        target_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        with patch("app.api.routers.card_decks.settings.CARD_RESPONSE_RATE_LIMIT_COUNT", 1), patch(
            "app.api.routers.card_decks.settings.CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS", 3600
        ):
            first = self.client.post(
                f"/api/card-decks/respond/{target_session.id}",
                json={"content": "first deck answer"},
            )
            update = self.client.post(
                f"/api/card-decks/respond/{target_session.id}",
                json={"content": "edited deck answer"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["session_status"], CardSessionStatus.WAITING_PARTNER.value)

    def test_deck_respond_rate_limited_by_partner_pair_dimension(self) -> None:
        with Session(self.engine) as session:
            second_card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Pair Card",
                description="desc",
                question="Pair question?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            session.add(second_card)
            session.commit()
            session.refresh(second_card)

        first_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=self.card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )
        second_session = self._create_session(
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
            card_id=second_card.id,
            creator_id=self.user_a.id,
            partner_id=self.user_b.id,
        )

        with patch("app.api.routers.card_decks.settings.CARD_RESPONSE_RATE_LIMIT_COUNT", 100), patch(
            "app.api.routers.card_decks.settings.CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS", 3600
        ), patch("app.api.routers.card_decks.settings.CARD_RESPONSE_RATE_LIMIT_IP_COUNT", 100), patch(
            "app.api.routers.card_decks.settings.CARD_RESPONSE_RATE_LIMIT_DEVICE_COUNT", 100
        ), patch("app.api.routers.card_decks.settings.CARD_RESPONSE_RATE_LIMIT_PARTNER_PAIR_COUNT", 1):
            first = self.client.post(
                f"/api/card-decks/respond/{first_session.id}",
                json={"content": "pair first answer"},
                headers={"x-forwarded-for": "203.0.113.44", "x-device-id": "pair-device-a"},
            )
            self.current_user_id = self.user_b.id
            second = self.client.post(
                f"/api/card-decks/respond/{second_session.id}",
                json={"content": "pair second answer"},
                headers={"x-forwarded-for": "203.0.113.45", "x-device-id": "pair-device-b"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("卡片回答過於頻繁", second.json()["detail"])
        self.assertEqual(second.headers.get("X-RateLimit-Scope"), "partner_pair")
        self.assertEqual(second.headers.get("X-RateLimit-Action"), "card_response_create")


if __name__ == "__main__":
    unittest.main()
