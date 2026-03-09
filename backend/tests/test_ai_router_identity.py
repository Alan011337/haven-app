from app.services.ai_router_identity import (
    build_input_fingerprint,
    build_normalized_content_hash,
    build_router_key,
    normalize_idempotency_key,
)


def test_normalize_idempotency_key_preserves_valid_value() -> None:
    key = normalize_idempotency_key(idempotency_key="abc12345", request_id=None)
    assert key == "abc12345"


def test_normalize_idempotency_key_falls_back_to_generated_uuid() -> None:
    key = normalize_idempotency_key(idempotency_key="x", request_id=None)
    assert len(key) >= 32
    assert key != "x"


def test_input_fingerprint_is_stable_for_different_key_order() -> None:
    left = build_input_fingerprint(payload={"b": 2, "a": 1})
    right = build_input_fingerprint(payload={"a": 1, "b": 2})
    assert left == right


def test_build_normalized_content_hash_trims_input() -> None:
    assert build_normalized_content_hash(" hello ") == build_normalized_content_hash("hello")


def test_build_router_key_is_subject_scoped() -> None:
    base = build_router_key(subject_key="u1", request_class="journal_analysis", idempotency_key="idem-1")
    changed = build_router_key(subject_key="u2", request_class="journal_analysis", idempotency_key="idem-1")
    assert base != changed

