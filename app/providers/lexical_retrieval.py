from __future__ import annotations

import math
import re

from app.providers.interfaces import RetrievedContext

TOKEN_PATTERN = re.compile(r"[A-Za-zА-Яа-я0-9_]+")


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}


def rank_retrieved_contexts(
    query: str,
    chunks: list[RetrievedContext],
    *,
    subject: str | None = None,
    topic: str | None = None,
    task_id: str | None = None,
    top_k: int = 3,
) -> list[RetrievedContext]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    scored_results: list[RetrievedContext] = []
    for chunk in chunks:
        if subject and chunk.metadata.get("subject") != subject:
            continue
        if topic and chunk.metadata.get("topic") != topic:
            continue
        if task_id and chunk.metadata.get("task_id") != task_id:
            continue

        content_tokens = tokenize(chunk.content)
        overlap = len(query_tokens & content_tokens)
        metadata_tokens = tokenize(" ".join(chunk.metadata.values()))
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
