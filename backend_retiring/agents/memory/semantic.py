"""Semantic memory — persistent vector store for facts and concepts."""

from __future__ import annotations

import os
import uuid

import chromadb

from backend_retiring.retrieval.embeddings import EmbeddingService
from .model import SemanticMemory


class SemanticMemoryStore:
    """Persistent semantic memory backed by ChromaDB vector store."""

    def __init__(
        self,
        embeddings: EmbeddingService,
        persist_dir: str | None = None,
        collection_name: str = "semantic_memory",
    ) -> None:
        self._embeddings = embeddings
        if persist_dir:
            os.makedirs(persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=persist_dir)
        else:
            self._client = chromadb.EphemeralClient()
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def count(self) -> int:
        return self._collection.count()

    def store(
        self,
        content: str,
        category: str,
        importance: float = 0.5,
    ) -> str:
        """Store a semantic fact. Returns memory_id."""
        memory_id = str(uuid.uuid4())
        embedding = self._embeddings.embed_single(content)
        self._collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "category": category,
                "importance": importance,
                "created_at": "now",
            }],
        )
        return memory_id

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
    ) -> list[SemanticMemory]:
        """Retrieve relevant memories by semantic similarity."""
        query_embedding = self._embeddings.embed_single(query)
        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if category:
            kwargs["where"] = {"category": category}

        results = self._collection.query(**kwargs)
        if not results["documents"] or not results["documents"][0]:
            return []

        return [
            SemanticMemory(
                memory_id=results["ids"][0][i] if results["ids"] else "",
                content=doc,
                category=(meta or {}).get("category", "unknown"),
                importance=float((meta or {}).get("importance", 0.5)),
            )
            for i, (doc, meta) in enumerate(
                zip(results["documents"][0], results["metadatas"][0])
            )
        ]

    def decay(self, max_age_days: int = 90, min_importance: float = 0.3) -> int:
        """Remove low-importance, old memories. Returns count removed."""
        # Simple approach: clear all and would need re-ingestion
        # Production: filter by metadata timestamps
        return 0  # Placeholder — production would query and delete
