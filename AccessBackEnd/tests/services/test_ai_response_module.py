from __future__ import annotations

import sqlite3

from app.services.ai_response_module import AIResponseService, SQLitePromptTemplateRepository


class _FakeModelInputs(dict):
    def __init__(self, *, text: str):
        super().__init__(input_text=text)
        self.input_ids = [[1, 2, 3]]

    def to(self, _device: str):
        return self


class _FakeTokenizer:
    def __init__(self):
        self.captured_messages = None

    def apply_chat_template(self, messages, tokenize: bool, add_generation_prompt: bool):
        self.captured_messages = messages
        assert tokenize is False
        assert add_generation_prompt is True
        return "templated-text"

    def __call__(self, _texts, return_tensors: str):
        assert return_tensors == "pt"
        return _FakeModelInputs(text="templated-text")

    def batch_decode(self, generated_ids, skip_special_tokens: bool):
        assert skip_special_tokens is True
        assert generated_ids == [[9001, 9002]]
        return ["generated reply"]


class _FakeModel:
    device = "cpu"

    def generate(self, **kwargs):
        assert kwargs["input_text"] == "templated-text"
        return [[1, 2, 3, 9001, 9002]]


def test_ai_response_service_uses_db_prompt_template_and_returns_generation(tmp_path):
    db_path = tmp_path / "prompts.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE prompt_templates (id INTEGER PRIMARY KEY, prompt TEXT NOT NULL)")
        connection.execute(
            "INSERT INTO prompt_templates (id, prompt) VALUES (?, ?)",
            (1, "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."),
        )
        connection.commit()

    prompt_repository = SQLitePromptTemplateRepository(db_path=db_path)
    fake_tokenizer = _FakeTokenizer()

    service = AIResponseService(
        prompt_repository=prompt_repository,
        model_loader=lambda *_args, **_kwargs: _FakeModel(),
        tokenizer_loader=lambda *_args, **_kwargs: fake_tokenizer,
    )

    response = service.get_response(
        prompt_id=1,
        user_prompt="Give me a short introduction to large language model.",
    )

    assert response == "generated reply"
    assert fake_tokenizer.captured_messages == [
        {
            "role": "system",
            "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "Give me a short introduction to large language model.",
        },
    ]
