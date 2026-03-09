from pathlib import Path


def test_api_response_wrapping_is_guarded_by_json_and_idempotency_flags() -> None:
    main_path = Path(__file__).resolve().parents[1] / "app" / "main.py"
    text = main_path.read_text(encoding="utf-8")
    assert "should_wrap_envelope =" in text
    assert "should_decode_for_idempotency =" in text
    assert "if should_wrap_envelope or should_decode_for_idempotency:" in text
