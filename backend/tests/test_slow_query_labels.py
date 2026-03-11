from __future__ import annotations

import unittest

from app.db.slow_query_labels import classify_slow_query_kind, query_fingerprint


class SlowQueryLabelTests(unittest.TestCase):
    def test_classify_card_session_lookup(self) -> None:
        statement = """
        SELECT card_sessions.id
        FROM card_sessions
        WHERE card_sessions.deleted_at IS NULL
        ORDER BY card_sessions.created_at DESC
        """
        self.assertEqual(classify_slow_query_kind(statement), "card_sessions_lookup")

    def test_classify_card_response_session_lookup(self) -> None:
        statement = """
        SELECT card_responses.id
        FROM card_responses
        WHERE card_responses.session_id = ?
        """
        self.assertEqual(classify_slow_query_kind(statement), "card_responses_session_lookup")

    def test_classify_card_response_legacy_lookup(self) -> None:
        statement = """
        SELECT card_responses.id
        FROM card_responses
        WHERE card_responses.session_id IS NULL
        """
        self.assertEqual(classify_slow_query_kind(statement), "card_responses_legacy_lookup")

    def test_classify_known_lookup_tables(self) -> None:
        self.assertEqual(classify_slow_query_kind("SELECT * FROM users WHERE users.id = ?"), "users_lookup")
        self.assertEqual(classify_slow_query_kind("SELECT * FROM cards WHERE cards.id = ?"), "cards_lookup")

    def test_fingerprint_is_stable_for_whitespace_changes(self) -> None:
        first = query_fingerprint("SELECT *   FROM users WHERE id = ?")
        second = query_fingerprint(" select * from users   where id = ? ")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
