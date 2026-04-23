# AUTHZ_MATRIX: PUT /api/love-map/identity/compass
# AUTHZ_DENY_MATRIX: PUT /api/love-map/identity/compass

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
from app.db.session import get_session  # noqa: E402
from app.models.relationship_compass import RelationshipCompass  # noqa: E402
from app.models.relationship_compass_change import RelationshipCompassChange  # noqa: E402
from app.models.user import User  # noqa: E402


class LoveMapRelationshipCompassApiTests(unittest.TestCase):
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
            alice = User(email="alice-compass@example.com", full_name="Alice", hashed_password="hashed")
            bob = User(email="bob-compass@example.com", full_name="Bob", hashed_password="hashed")
            carol = User(email="carol-compass@example.com", full_name="Carol", hashed_password="hashed")
            dave = User(email="dave-compass@example.com", full_name="Dave", hashed_password="hashed")
            solo = User(email="solo-compass@example.com", full_name="Solo", hashed_password="hashed")
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
                    user_id=min(carol.id, dave.id),
                    partner_id=max(carol.id, dave.id),
                    identity_statement="Carol and Dave private compass",
                    story_anchor="Carol and Dave private story",
                    future_direction="Carol and Dave private future",
                    updated_by_user_id=carol.id,
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

    def test_paired_user_can_upsert_pair_maintained_compass(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.put(
            "/api/love-map/identity/compass",
            json={
                "identity_statement": "  我們是在忙裡仍願意回來對話的伴侶。  ",
                "story_anchor": "那次一起把困難週末走完的記憶。",
                "future_direction": "接下來一起練習把週日早晨留給彼此。",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["identity_statement"], "我們是在忙裡仍願意回來對話的伴侶。")
        self.assertEqual(payload["story_anchor"], "那次一起把困難週末走完的記憶。")
        self.assertEqual(payload["future_direction"], "接下來一起練習把週日早晨留給彼此。")
        self.assertEqual(payload["updated_by_name"], "Alice")
        self.assertIsNotNone(payload["updated_at"])

        with Session(self.engine) as session:
            row = session.exec(
                select(RelationshipCompass).where(
                    RelationshipCompass.user_id == min(self.alice_id, self.bob_id),
                    RelationshipCompass.partner_id == max(self.alice_id, self.bob_id),
                )
            ).first()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.updated_by_user_id, self.alice_id)

    def test_system_read_returns_only_current_pair_compass(self) -> None:
        self.current_user_id = self.alice_id
        write_response = self.client.put(
            "/api/love-map/identity/compass",
            json={
                "identity_statement": "Alice and Bob compass",
                "story_anchor": "Alice and Bob story",
                "future_direction": "Alice and Bob future",
            },
        )
        self.assertEqual(write_response.status_code, 200)

        response = self.client.get("/api/love-map/system")

        self.assertEqual(response.status_code, 200)
        compass = response.json()["relationship_compass"]
        self.assertEqual(compass["identity_statement"], "Alice and Bob compass")
        self.assertEqual(compass["story_anchor"], "Alice and Bob story")
        self.assertEqual(compass["future_direction"], "Alice and Bob future")
        self.assertEqual(compass["updated_by_name"], "Alice")
        self.assertNotIn("Carol and Dave", str(compass))

    def test_either_partner_updates_the_same_pair_scoped_compass(self) -> None:
        self.current_user_id = self.alice_id
        first_response = self.client.put(
            "/api/love-map/identity/compass",
            json={
                "identity_statement": "First compass",
                "story_anchor": "First story",
                "future_direction": "First future",
            },
        )
        self.assertEqual(first_response.status_code, 200)

        self.current_user_id = self.bob_id
        second_response = self.client.put(
            "/api/love-map/identity/compass",
            json={
                "identity_statement": "Bob refined compass",
                "story_anchor": "",
                "future_direction": "Bob refined future",
            },
        )

        self.assertEqual(second_response.status_code, 200)
        payload = second_response.json()
        self.assertEqual(payload["identity_statement"], "Bob refined compass")
        self.assertIsNone(payload["story_anchor"])
        self.assertEqual(payload["future_direction"], "Bob refined future")
        self.assertEqual(payload["updated_by_name"], "Bob")

        with Session(self.engine) as session:
            rows = session.exec(select(RelationshipCompass)).all()
            alice_bob_rows = [
                row
                for row in rows
                if row.user_id == min(self.alice_id, self.bob_id)
                and row.partner_id == max(self.alice_id, self.bob_id)
            ]
            self.assertEqual(len(alice_bob_rows), 1)
            self.assertEqual(alice_bob_rows[0].updated_by_user_id, self.bob_id)

    def test_unpaired_user_cannot_upsert_compass(self) -> None:
        self.current_user_id = self.solo_id

        response = self.client.put(
            "/api/love-map/identity/compass",
            json={
                "identity_statement": "Solo compass",
                "story_anchor": "Solo story",
                "future_direction": "Solo future",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_over_length_fields_are_rejected(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.put(
            "/api/love-map/identity/compass",
            json={
                "identity_statement": "x" * 501,
                "story_anchor": "",
                "future_direction": "",
            },
        )

        self.assertEqual(response.status_code, 422)

    # ---- Revision-notes evolution layer (Batch: Compass Evolution V1) ----

    def _count_history_rows(self) -> int:
        with Session(self.engine) as session:
            return len(
                session.exec(
                    select(RelationshipCompassChange).where(
                        RelationshipCompassChange.user_id == min(self.alice_id, self.bob_id),
                        RelationshipCompassChange.partner_id == max(self.alice_id, self.bob_id),
                    )
                ).all()
            )

    def test_real_change_creates_history_row_with_before_after_and_note(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.put(
            "/api/love-map/identity/compass",
            json={
                "identity_statement": "我們是願意把重要的事留下來的伴侶。",
                "story_anchor": "那段忙到幾乎散掉的週末，我們還是靠咖啡和散步回來。",
                "future_direction": "一起把週日早晨慢下來。",
                "revision_note": "這次不是重寫，是因為我們開始相信自己可以慢一點。",
            },
        )

        self.assertEqual(response.status_code, 200)

        with Session(self.engine) as session:
            rows = session.exec(
                select(RelationshipCompassChange).where(
                    RelationshipCompassChange.user_id == min(self.alice_id, self.bob_id),
                    RelationshipCompassChange.partner_id == max(self.alice_id, self.bob_id),
                )
            ).all()
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertIsNone(row.identity_statement_before)
            self.assertEqual(row.identity_statement_after, "我們是願意把重要的事留下來的伴侶。")
            self.assertIsNone(row.story_anchor_before)
            self.assertEqual(
                row.story_anchor_after,
                "那段忙到幾乎散掉的週末，我們還是靠咖啡和散步回來。",
            )
            self.assertIsNone(row.future_direction_before)
            self.assertEqual(row.future_direction_after, "一起把週日早晨慢下來。")
            self.assertEqual(row.changed_by_user_id, self.alice_id)
            self.assertEqual(
                row.revision_note,
                "這次不是重寫，是因為我們開始相信自己可以慢一點。",
            )

    def test_no_op_save_creates_no_history_row(self) -> None:
        self.current_user_id = self.alice_id

        payload = {
            "identity_statement": "A stable first version.",
            "story_anchor": "Some story.",
            "future_direction": "Some future.",
        }

        first = self.client.put("/api/love-map/identity/compass", json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self._count_history_rows(), 1)

        with Session(self.engine) as session:
            row_after_first = session.exec(
                select(RelationshipCompass).where(
                    RelationshipCompass.user_id == min(self.alice_id, self.bob_id),
                    RelationshipCompass.partner_id == max(self.alice_id, self.bob_id),
                )
            ).first()
            assert row_after_first is not None
            first_updated_at = row_after_first.updated_at

        second = self.client.put("/api/love-map/identity/compass", json=payload)
        self.assertEqual(second.status_code, 200)
        # A no-op save must not create a new history row.
        self.assertEqual(self._count_history_rows(), 1)

        with Session(self.engine) as session:
            row_after_second = session.exec(
                select(RelationshipCompass).where(
                    RelationshipCompass.user_id == min(self.alice_id, self.bob_id),
                    RelationshipCompass.partner_id == max(self.alice_id, self.bob_id),
                )
            ).first()
            assert row_after_second is not None
            # A no-op save must not advance the compass updated_at either.
            self.assertEqual(row_after_second.updated_at, first_updated_at)

    def test_whitespace_only_revision_note_is_normalized_null(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.put(
            "/api/love-map/identity/compass",
            json={
                "identity_statement": "",
                "story_anchor": "Some story.",
                "future_direction": "",
                "revision_note": "   \n  ",
            },
        )

        self.assertEqual(response.status_code, 200)

        with Session(self.engine) as session:
            row = session.exec(
                select(RelationshipCompassChange).where(
                    RelationshipCompassChange.user_id == min(self.alice_id, self.bob_id),
                    RelationshipCompassChange.partner_id == max(self.alice_id, self.bob_id),
                )
            ).first()
            assert row is not None
            self.assertIsNone(row.revision_note)

    def test_system_read_returns_last_three_history_entries_ordered_desc(self) -> None:
        self.current_user_id = self.alice_id
        for idx in range(1, 5):
            resp = self.client.put(
                "/api/love-map/identity/compass",
                json={
                    "identity_statement": f"version-{idx}",
                    "story_anchor": "",
                    "future_direction": "",
                },
            )
            self.assertEqual(resp.status_code, 200)

        system_response = self.client.get("/api/love-map/system")
        self.assertEqual(system_response.status_code, 200)
        history = system_response.json()["relationship_compass_history"]
        # Limit = 3 surfaces the most recent three changes.
        self.assertEqual(len(history), 3)
        # Each entry carries a resolved changed_by_name.
        for entry in history:
            self.assertEqual(entry["changed_by_name"], "Alice")
        # Ordered most-recent-first: version-4 → version-3 → version-2.
        top_after_texts = [
            next(
                (f["after_text"] for f in entry["fields"] if f["key"] == "identity_statement"),
                None,
            )
            for entry in history
        ]
        self.assertEqual(top_after_texts, ["version-4", "version-3", "version-2"])

    def test_partial_field_change_only_records_changed_field_in_fields_list(self) -> None:
        self.current_user_id = self.alice_id

        first = self.client.put(
            "/api/love-map/identity/compass",
            json={
                "identity_statement": "First identity.",
                "story_anchor": "First story.",
                "future_direction": "First future.",
            },
        )
        self.assertEqual(first.status_code, 200)

        # Change only story_anchor; identity and future stay identical.
        second = self.client.put(
            "/api/love-map/identity/compass",
            json={
                "identity_statement": "First identity.",
                "story_anchor": "Second story.",
                "future_direction": "First future.",
            },
        )
        self.assertEqual(second.status_code, 200)

        system_response = self.client.get("/api/love-map/system")
        self.assertEqual(system_response.status_code, 200)
        history = system_response.json()["relationship_compass_history"]
        self.assertEqual(len(history), 2)
        top_fields = history[0]["fields"]
        self.assertEqual(len(top_fields), 1)
        self.assertEqual(top_fields[0]["key"], "story_anchor")
        self.assertEqual(top_fields[0]["change_kind"], "updated")
        self.assertEqual(top_fields[0]["before_text"], "First story.")
        self.assertEqual(top_fields[0]["after_text"], "Second story.")

    def test_over_length_revision_note_is_rejected(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.put(
            "/api/love-map/identity/compass",
            json={
                "identity_statement": "A valid statement.",
                "story_anchor": "",
                "future_direction": "",
                "revision_note": "x" * 301,
            },
        )

        self.assertEqual(response.status_code, 422)
        # Validation failure must not create either a compass row or history row.
        self.assertEqual(self._count_history_rows(), 0)


if __name__ == "__main__":
    unittest.main()
