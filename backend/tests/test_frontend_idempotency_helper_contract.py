from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

IDEMPOTENCY_HELPER_PATH = REPO_ROOT / "frontend" / "src" / "lib" / "idempotency.ts"
CARD_SERVICE_PATH = REPO_ROOT / "frontend" / "src" / "services" / "cardService.ts"
DECK_SERVICE_PATH = REPO_ROOT / "frontend" / "src" / "services" / "deckService.ts"
JOURNALS_API_PATH = REPO_ROOT / "frontend" / "src" / "services" / "journals-api.ts"


def test_frontend_idempotency_helper_exists() -> None:
    assert IDEMPOTENCY_HELPER_PATH.exists()
    text = IDEMPOTENCY_HELPER_PATH.read_text(encoding="utf-8")
    assert "buildIdempotencyHeaders" in text
    assert "normalizeIdempotencyKey" in text
    assert "MIN_IDEMPOTENCY_KEY_LENGTH" in text


def test_frontend_services_use_shared_idempotency_helper() -> None:
    card_text = CARD_SERVICE_PATH.read_text(encoding="utf-8")
    deck_text = DECK_SERVICE_PATH.read_text(encoding="utf-8")
    journals_text = JOURNALS_API_PATH.read_text(encoding="utf-8")
    for text in (card_text, deck_text, journals_text):
        assert "buildIdempotencyHeaders" in text
