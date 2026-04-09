from __future__ import annotations

import math
import re
from pathlib import Path

from app.kb.ingest import build_seed_chunks
from app.providers.interfaces import RetrievedContext, RetrieverBackend

TOKEN_PATTERN = re.compile(r"[A-Za-zА-Яа-я0-9_]+")


class FallbackRetriever(RetrieverBackend):
    def __init__(
        self,
        seed_path: Path,
        *,
        chunk_size_chars: int = 320,
        overlap_paragraphs: int = 1,
    ) -> None:
        self.seed_path = seed_path
        self.chunk_size_chars = chunk_size_chars
        self.overlap_paragraphs = overlap_paragraphs
        self._chunks = self._load_chunks()

    def search(
        self,
        query: str,
        *,
        subject: str | None = None,
        topic: str | None = None,
        task_id: str | None = None,
        top_k: int = 3,
    ) -> list[RetrievedContext]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scored_results: list[RetrievedContext] = []
        for chunk in self._chunks:
            if subject and chunk.metadata.get("subject") != subject:
                continue
            if topic and chunk.metadata.get("topic") != topic:
                continue
            if task_id and chunk.metadata.get("task_id") != task_id:
                continue

            content_tokens = self._tokenize(chunk.content)
            overlap = len(query_tokens & content_tokens)
            metadata_tokens = self._tokenize(" ".join(chunk.metadata.values()))
            overlap += len(query_tokens & metadata_tokens)
            if task_id and chunk.metadata.get("task_id") == task_id:
                overlap += 3
            if topic and chunk.metadata.get("topic") == topic:
                overlap += 2
            if overlap <= 0:
                continue

            score = overlap / math.sqrt(max(len(content_tokens), 1))
            scored_results.append(chunk.model_copy(update={"score": round(score, 4)}))

        return sorted(scored_results, key=lambda item: item.score, reverse=True)[:top_k]

    def _load_chunks(self) -> list[RetrievedContext]:
        return [
            RetrievedContext(
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                score=0.0,
                metadata=chunk.metadata_json,
            )
            for chunk in build_seed_chunks(
                self.seed_path,
                target_size_chars=self.chunk_size_chars,
                overlap_paragraphs=self.overlap_paragraphs,
            )
        ]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token.lower() for token in TOKEN_PATTERN.findall(text)}
