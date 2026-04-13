from __future__ import annotations

import json
import ssl
from typing import Any
from urllib import error, request

from app.core.config import Settings
from app.providers.interfaces import EmbeddingInputType, EmbeddingProvider


class JinaEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def embed(
        self,
        texts: list[str],
        *,
        input_type: EmbeddingInputType = "document",
    ) -> list[list[float]]:
        if not texts:
            return []

        api_key = self.settings.embedding_api_key
        if not api_key:
            raise RuntimeError(
                "Jina embedding provider requires JINA_API_KEY or RAG_EMBEDDING_API_KEY."
            )

        body = json.dumps(
            {
                "model": self.settings.embedding_model_name,
                "input": texts,
                "task": (
                    "retrieval.query"
                    if input_type == "query"
                    else "retrieval.passage"
                ),
            }
        ).encode("utf-8")
        http_request = request.Request(
            self.settings.embedding_api_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        try:
            ssl_context = self._build_ssl_context()
            with request.urlopen(
                http_request,
                timeout=self.settings.embedding_api_timeout_seconds,
                context=ssl_context,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (error.URLError, ssl.SSLError) as exc:
            raise RuntimeError(
                "Jina embedding request failed. "
                "If your environment uses a custom corporate CA, set "
                "RAG_EMBEDDING_CA_BUNDLE_PATH to the CA bundle path. "
                "For local debugging only, you can set "
                "RAG_EMBEDDING_SSL_VERIFY=false. "
                f"Original error: {exc}"
            ) from exc

        embeddings = self._parse_embeddings(payload)
        if any(len(vector) != self.settings.pgvector_dimensions for vector in embeddings):
            raise RuntimeError(
                "Jina embedding dimension mismatch: "
                f"expected {self.settings.pgvector_dimensions}, "
                f"got {len(embeddings[0]) if embeddings else 0}."
            )
        return embeddings

    def _build_ssl_context(self) -> ssl.SSLContext:
        if not self.settings.embedding_ssl_verify:
            return ssl._create_unverified_context()

        if self.settings.embedding_ca_bundle_path is not None:
            return ssl.create_default_context(
                cafile=str(self.settings.embedding_ca_bundle_path)
            )

        return ssl.create_default_context()

    @staticmethod
    def _parse_embeddings(payload: dict[str, Any]) -> list[list[float]]:
        data = payload.get("data")
        if not isinstance(data, list) or not data:
            raise RuntimeError("Jina embedding API returned no data.")

        ordered = sorted(
            data,
            key=lambda item: int(item.get("index", 0)) if isinstance(item, dict) else 0,
        )
        embeddings: list[list[float]] = []
        for item in ordered:
            if not isinstance(item, dict):
                raise RuntimeError("Jina embedding API returned malformed item.")
            embedding = item.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                raise RuntimeError("Jina embedding API returned malformed embedding.")
            embeddings.append([float(value) for value in embedding])
        return embeddings
