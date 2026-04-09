from __future__ import annotations

import hashlib
import math
import re

from app.providers.interfaces import EmbeddingProvider

TOKEN_PATTERN = re.compile(r"[A-Za-zА-Яа-я0-9_]+")


class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimensions: int = 8) -> None:
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_single(text) for text in texts]

    def _embed_single(self, text: str) -> list[float]:
        buckets = [0.0] * self.dimensions
        tokens = TOKEN_PATTERN.findall(text.lower())
        if not tokens:
            return buckets

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(self.dimensions):
                buckets[index] += digest[index] / 255.0

        norm = math.sqrt(sum(value * value for value in buckets)) or 1.0
        return [round(value / norm, 6) for value in buckets]
