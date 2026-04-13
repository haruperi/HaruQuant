"""Document ingestion with chunking and embedding."""

from __future__ import annotations

from .embeddings import EmbeddingService
from .models import DocumentChunk, TextChunk


class DocumentIngester:
    """Splits documents into chunks, embeds them, and prepares for storage."""

    def __init__(
        self,
        embeddings: EmbeddingService,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        self._embeddings = embeddings
        self._chunk_size = chunk_size
        self._overlap = chunk_overlap

    def ingest(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, str] | None = None,
    ) -> list[DocumentChunk]:
        """Ingest a document: split into chunks, embed, return DocumentChunks."""
        chunks = self._split_into_chunks(content)
        if not chunks:
            return []

        embeddings = self._embeddings.embed([c.content for c in chunks])
        base_metadata = metadata or {}

        return [
            DocumentChunk(
                doc_id=doc_id,
                chunk_id=f"{doc_id}_{i}",
                content=c.content,
                metadata={
                    **base_metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
                embedding=emb,
            )
            for i, (c, emb) in enumerate(zip(chunks, embeddings))
        ]

    def _split_into_chunks(self, content: str) -> list[TextChunk]:
        """Split content into overlapping chunks by word count."""
        words = content.split()
        if not words:
            return []

        chunks: list[TextChunk] = []
        stride = max(1, self._chunk_size - self._overlap)
        for i in range(0, len(words), stride):
            chunk_words = words[i : i + self._chunk_size]
            chunks.append(TextChunk(content=" ".join(chunk_words)))
        return chunks
