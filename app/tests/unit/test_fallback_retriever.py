from __future__ import annotations

from pathlib import Path

from app.providers.fallback_retriever import FallbackRetriever


def test_fallback_retriever_returns_relevant_seed_chunk():
    seed_path = Path(__file__).resolve().parents[2] / "kb" / "seed"
    retriever = FallbackRetriever(seed_path)

    results = retriever.search("Как устроен цикл for в Python", subject="informatics")

    assert results
    assert results[0].metadata["topic"] == "python_loops"
