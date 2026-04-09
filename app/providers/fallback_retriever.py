from __future__ import annotations

import math
import re
from pathlib import Path

from app.providers.interfaces import RetrievedContext, RetrieverBackend

TOKEN_PATTERN = re.compile(r"[A-Za-zА-Яа-я0-9_]+")


class FallbackRetriever(RetrieverBackend):
    def __init__(self, seed_path: Path) -> None:
        self.seed_path = seed_path
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
            if task_id and chunk.metadata.get("task_id") == task_id:
                overlap += 3
            if overlap <= 0:
                continue

            score = overlap / math.sqrt(max(len(content_tokens), 1))
            scored_results.append(chunk.model_copy(update={"score": round(score, 4)}))

        return sorted(scored_results, key=lambda item: item.score, reverse=True)[:top_k]

    def _load_chunks(self) -> list[RetrievedContext]:
        chunks: list[RetrievedContext] = []
        for path in sorted(self.seed_path.glob("*.md")):
            raw_text = path.read_text(encoding="utf-8")
            metadata, content = self._parse_document(raw_text)
            if not content.strip():
                continue
            metadata.setdefault("source", path.name)
            metadata.setdefault("subject", "informatics")
            chunks.append(
                RetrievedContext(
                    chunk_id=f"{path.stem}:0",
                    content=content.strip(),
                    score=0.0,
                    metadata=metadata,
                )
            )
        return chunks

    @staticmethod
    def _parse_document(raw_text: str) -> tuple[dict[str, str], str]:
        metadata: dict[str, str] = {}
        lines = raw_text.splitlines()
        content_start = 0

        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                content_start = index + 1
                break
            if ":" not in stripped:
                break
            key, value = stripped.split(":", 1)
            metadata[key.strip()] = value.strip()
            content_start = index + 1

        content = "\n".join(lines[content_start:])
        return metadata, content

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token.lower() for token in TOKEN_PATTERN.findall(text)}
