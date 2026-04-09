from __future__ import annotations

from app.kb.models import LoadedDocument, PreparedKnowledgeChunk


def chunk_document(
    document: LoadedDocument,
    *,
    target_size_chars: int = 320,
    overlap_paragraphs: int = 1,
) -> list[PreparedKnowledgeChunk]:
    paragraphs = [paragraph.strip() for paragraph in document.content.split("\n\n") if paragraph.strip()]
    if not paragraphs:
        return []

    chunk_texts = _group_paragraphs(
        paragraphs,
        target_size_chars=target_size_chars,
        overlap_paragraphs=overlap_paragraphs,
    )

    chunks: list[PreparedKnowledgeChunk] = []
    total_chunks = len(chunk_texts)
    for index, content in enumerate(chunk_texts):
        metadata = dict(document.metadata)
        metadata["source_id"] = document.source_id
        metadata["chunk_index"] = str(index)
        metadata["chunk_count"] = str(total_chunks)

        chunks.append(
            PreparedKnowledgeChunk(
                chunk_id=f"{document.source_id.rsplit('.', 1)[0]}:{index}",
                source_id=document.source_id,
                subject=document.subject,
                topic=document.topic,
                task_id=document.task_id,
                content=content,
                metadata_json=metadata,
            )
        )
    return chunks


def _group_paragraphs(
    paragraphs: list[str],
    *,
    target_size_chars: int,
    overlap_paragraphs: int,
) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph)

        if paragraph_length > target_size_chars and not current:
            chunks.extend(_split_long_paragraph(paragraph, target_size_chars))
            continue

        projected_length = current_length + paragraph_length + (2 if current else 0)
        if current and projected_length > target_size_chars:
            chunks.append("\n\n".join(current))
            overlap = current[-overlap_paragraphs:] if overlap_paragraphs > 0 else []
            current = list(overlap)
            current_length = sum(len(item) for item in current) + max(len(current) - 1, 0) * 2

        current.append(paragraph)
        current_length += paragraph_length + (2 if len(current) > 1 else 0)

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _split_long_paragraph(paragraph: str, target_size_chars: int) -> list[str]:
    words = paragraph.split()
    chunks: list[str] = []
    current_words: list[str] = []
    current_length = 0

    for word in words:
        projected_length = current_length + len(word) + (1 if current_words else 0)
        if current_words and projected_length > target_size_chars:
            chunks.append(" ".join(current_words))
            current_words = [word]
            current_length = len(word)
            continue

        current_words.append(word)
        current_length = projected_length

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks
