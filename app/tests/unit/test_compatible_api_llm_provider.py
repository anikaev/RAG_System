from __future__ import annotations

import json

from app.core.config import Settings
from app.providers.compatible_api_llm_provider import CompatibleAPILLMProvider
from app.providers.interfaces import LLMGenerationRequest


class _FakeHttpResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeHttpResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_compatible_api_provider_uses_json_schema_response_format(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(http_request, timeout):
        captured["url"] = http_request.full_url
        captured["headers"] = dict(http_request.header_items())
        captured["body"] = json.loads(http_request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeHttpResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "response_text": "Подсказка.",
                                    "guiding_question": "Что будет первым шагом?",
                                    "confidence": 0.77,
                                }
                            )
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(
        "app.providers.compatible_api_llm_provider.request.urlopen",
        fake_urlopen,
    )

    provider = CompatibleAPILLMProvider(
        Settings(
            session_backend="memory",
            seed_demo_data_on_startup=False,
            llm_api_base_url="https://router.huggingface.co/v1",
            llm_api_key="hf_test_token",
            llm_model_name="openai/gpt-oss-120b:fireworks-ai",
            llm_response_format_mode="json_schema",
        )
    )

    result = provider.generate(
        LLMGenerationRequest(
            user_message="Объясни цикл for",
            mode="concept_explainer",
            hint_level=1,
        )
    )

    assert result.response_text == "Подсказка."
    assert result.guiding_question == "Что будет первым шагом?"
    assert result.confidence == 0.77

    assert captured["url"] == "https://router.huggingface.co/v1/chat/completions"
    assert captured["timeout"] == 30

    body = captured["body"]
    assert body["model"] == "openai/gpt-oss-120b:fireworks-ai"
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["name"] == "rag_tutor_response"
    assert body["response_format"]["json_schema"]["schema"]["required"] == [
        "response_text",
        "guiding_question",
        "confidence",
    ]


def test_settings_support_hf_token_env_alias(monkeypatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_alias_token")

    settings = Settings(
        session_backend="memory",
        seed_demo_data_on_startup=False,
    )

    assert settings.llm_api_key == "hf_alias_token"
