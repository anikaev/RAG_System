from __future__ import annotations

from pathlib import Path

from app.providers.fallback_retriever import FallbackRetriever
from app.providers.retrieval_cache import MemoryRetrievalCache, build_retrieval_cache_key


def test_retrieval_cache_key_is_stable_for_same_query():
    first = build_retrieval_cache_key(
        "fallback",
        "Как устроен цикл for в Python",
        subject="informatics",
        topic="python_loops",
        top_k=3,
    )
    second = build_retrieval_cache_key(
        "fallback",
        "Как устроен цикл for в Python",
        subject="informatics",
        topic="python_loops",
        top_k=3,
    )

    assert first == second


def test_fallback_retriever_uses_memory_cache():
    seed_path = Path(__file__).resolve().parents[2] / "kb" / "seed"
    retriever = FallbackRetriever(
        seed_path,
        cache_backend=MemoryRetrievalCache(),
    )

    initial = retriever.search("Как устроен цикл for в Python", subject="informatics")
    assert initial

    retriever._chunks = []

    cached = retriever.search("Как устроен цикл for в Python", subject="informatics")

    assert cached
    assert cached[0].chunk_id == initial[0].chunk_id
