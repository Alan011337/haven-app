from __future__ import annotations

import hashlib
import re

_FROM_TABLE_RE = re.compile(r"\bfrom\s+([a-z_][a-z0-9_]*)\b")


def normalize_statement(statement: str) -> str:
    return " ".join((statement or "").strip().lower().split())


def query_fingerprint(statement: str) -> str:
    normalized = normalize_statement(statement)
    if not normalized:
        return "empty"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return digest[:16]


def classify_slow_query_kind(statement: str) -> str:
    normalized = normalize_statement(statement)
    if not normalized:
        return "empty"

    if " from card_responses " in f" {normalized} ":
        if "card_responses.session_id is null" in normalized or " session_id is null" in normalized:
            return "card_responses_legacy_lookup"
        if "card_responses.session_id =" in normalized or " session_id =" in normalized or " session_id= " in normalized:
            return "card_responses_session_lookup"
        return "card_responses_lookup"

    if " from card_sessions " in f" {normalized} ":
        return "card_sessions_lookup"

    if " from users " in f" {normalized} ":
        return "users_lookup"

    if " from cards " in f" {normalized} ":
        return "cards_lookup"

    matched = _FROM_TABLE_RE.search(normalized)
    if matched:
        return f"{matched.group(1)}_lookup"

    return "other"
