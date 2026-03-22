import pytest
from pydantic import ValidationError

from app.schemas.journal import JournalCreate, JournalUpdate
from app.services import ai


def test_split_journal_translation_chunks_prefers_paragraph_boundaries():
    content = "\n\n".join(
        [
            "第一段 " + ("a" * 1200),
            "第二段 " + ("b" * 1200),
            "第三段 " + ("c" * 1200),
        ]
    )

    chunks = ai._split_journal_translation_chunks(content, max_chars=1800)

    assert len(chunks) == 3
    assert chunks[0].startswith("第一段")
    assert chunks[1].startswith("第二段")
    assert chunks[2].startswith("第三段")


def test_journal_content_schema_allows_long_form_up_to_twelve_thousand_chars():
    content = "a" * 12000

    created = JournalCreate.model_validate({"content": content})
    updated = JournalUpdate.model_validate({"content": content})

    assert created.content == content
    assert updated.content == content


def test_journal_content_schema_rejects_content_beyond_twelve_thousand_chars():
    content = "a" * 12001

    with pytest.raises(ValidationError):
        JournalCreate.model_validate({"content": content})


@pytest.mark.anyio
async def test_translate_journal_for_partner_translates_all_chunks(monkeypatch):
    captured_prompts: list[str] = []

    class FakeCompletion:
        def __init__(self, content: str):
            self.choices = [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]

    class FakeCompletions:
        async def create(self, *, model, messages, temperature, max_tokens):
            del model, temperature, max_tokens
            prompt = messages[-1]["content"]
            captured_prompts.append(prompt)
            return FakeCompletion(f"翻譯:{prompt[:8]}")

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(ai, "_get_openai_client", lambda: FakeClient())

    content = "\n\n".join(
        [
            "# 第一段\n" + ("a" * 1600),
            "## 第二段\n" + ("b" * 1600),
            "### 第三段\n" + ("c" * 1600),
        ]
    )

    translated = await ai.translate_journal_for_partner(content)

    assert len(captured_prompts) >= 3
    assert any("# 第一段" in prompt for prompt in captured_prompts)
    assert any("## 第二段" in prompt for prompt in captured_prompts)
    assert any("### 第三段" in prompt for prompt in captured_prompts)
    assert "翻譯:" in translated
    assert translated.count("翻譯:") == len(captured_prompts)
