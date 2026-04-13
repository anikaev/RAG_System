from __future__ import annotations

import hashlib
import math
import re

from app.providers.interfaces import EmbeddingInputType, EmbeddingProvider

TOKEN_PATTERN = re.compile(r"[A-Za-zА-Яа-я0-9_]+")


class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimensions: int = 1024) -> None:
        self.dimensions = dimensions

    def embed(
        self,
        texts: list[str],
        *,
        input_type: EmbeddingInputType = "document",
    ) -> list[list[float]]:
        prefix = "query:" if input_type == "query" else "document:"
        return [self._embed_single(f"{prefix} {text}") for text in texts]

    def _embed_single(self, text: str) -> list[float]:
        buckets = [0.0] * self.dimensions
        tokens = TOKEN_PATTERN.findall(text.lower())
        if not tokens:
            return buckets

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(self.dimensions):
                buckets[index] += digest[index % len(digest)] / 255.0

        norm = math.sqrt(sum(value * value for value in buckets)) or 1.0
        return [round(value / norm, 6) for value in buckets]
