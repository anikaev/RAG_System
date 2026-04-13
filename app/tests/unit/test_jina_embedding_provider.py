from __future__ import annotations

import json

from app.core.config import Settings
from app.providers.jina_embedding_provider import JinaEmbeddingProvider


class _FakeHttpResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeHttpResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_jina_embedding_provider_uses_task_aware_embeddings(monkeypatch) -> None:
    captured: dict[str, object] = {"tasks": []}

    def fake_urlopen(http_request, timeout, context):
        captured["url"] = http_request.full_url
        body = json.loads(http_request.data.decode("utf-8"))
        captured["body"] = body
        tasks = captured["tasks"]
        assert isinstance(tasks, list)
        tasks.append(body["task"])
        captured["timeout"] = timeout
        captured["has_context"] = context is not None
        return _FakeHttpResponse(
            {
                "data": [
                    {
                        "index": 0,
                        "embedding": [0.1] * 1024,
                    }
                ]
            }
        )

    monkeypatch.setattr(
        "app.providers.jina_embedding_provider.request.urlopen",
        fake_urlopen,
    )

    provider = JinaEmbeddingProvider(
        Settings(
            session_backend="memory",
            seed_demo_data_on_startup=False,
            embedding_provider_mode="jina",
            embedding_api_key="jina_test_key",
        )
    )

    query_vector = provider.embed(["Объясни цикл for"], input_type="query")
    document_vector = provider.embed(["Цикл for удобен для диапазона"], input_type="document")

    assert len(query_vector) == 1
    assert len(query_vector[0]) == 1024
    assert len(document_vector) == 1
    assert captured["url"] == "https://api.jina.ai/v1/embeddings"
    assert captured["timeout"] == 30
    assert captured["has_context"] is True
    assert captured["body"]["model"] == "jina-embeddings-v3"
    assert captured["tasks"] == ["retrieval.query", "retrieval.passage"]


def test_settings_support_jina_api_key_env_alias(monkeypatch) -> None:
    monkeypatch.setenv("JINA_API_KEY", "jina_alias_key")

    settings = Settings(
        session_backend="memory",
        seed_demo_data_on_startup=False,
    )

    assert settings.embedding_api_key == "jina_alias_key"
