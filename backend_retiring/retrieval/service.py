"""Retrieval service using ChromaDB for vector search."""

from __future__ import annotations

import os

import chromadb

from haruquant.utils import logger
from .embeddings import EmbeddingService
from .models import DocumentChunk, RetrievalResult


class RetrievalService:
    """Vector search retrieval using ChromaDB.

    Supports adding document chunks and querying by semantic similarity.
    """

    def __init__(
        self,
        embeddings: EmbeddingService,
        collection_name: str = "haruquant_knowledge",
        persist_dir: str | None = None,
    ) -> None:
        self._embeddings = embeddings
        if persist_dir:
            os.makedirs(persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=persist_dir)
        else:
            # In-memory client for testing
            self._client = chromadb.EphemeralClient()
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def count(self) -> int:
        return self._collection.count()

    def add_chunks(self, chunks: list[DocumentChunk]) -> int:
        """Add document chunks to the vector store. Returns count added."""
        if not chunks:
            return 0
        self._collection.add(
            ids=[c.chunk_id for c in chunks],
            embeddings=[c.embedding for c in chunks],
            documents=[c.content for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )
        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: dict[str, str] | None = None,
    ) -> list[RetrievalResult]:
        """Search for relevant chunks by query embedding."""
        query_embedding = self._embeddings.embed_single(query)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata,
            include=["documents", "metadatas", "distances"],
        )

        if not results["documents"] or not results["documents"][0]:
            return []

        # Get IDs separately (not included in query response)
        all_ids = results.get("ids", [[]])
        result_ids = all_ids[0] if all_ids else [""] * len(results["documents"][0])

        return [
            RetrievalResult(
                content=doc,
                metadata=meta or {},
                score=1.0 - dist,  # Convert distance to similarity
                doc_id=(meta or {}).get("doc_id", ""),
                chunk_id=result_ids[i] if i < len(result_ids) else "",
            )
            for i, (doc, meta, dist) in enumerate(
                zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            )
        ]

    def clear(self) -> None:
        """Remove all chunks from the collection."""
        ids = self._collection.get()["ids"]
        if ids:
            self._collection.delete(ids=ids)
