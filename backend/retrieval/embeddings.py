"""Embedding service using sentence-transformers."""

from __future__ import annotations

import numpy as np

from haruquant.utils import logger

class EmbeddingService:
    """Generates text embeddings using sentence-transformers."""

    def __init__(self, model: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model)
        self._dim = self._model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dim or 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts at once."""
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_single(self, text: str) -> list[float]:
        """Embed a single text."""
        return self.embed([text])[0]

    def similarity(self, text_a: str, text_b: str) -> float:
        """Compute cosine similarity between two texts."""
        emb_a = self.embed_single(text_a)
        emb_b = self.embed_single(text_b)
        return float(np.dot(emb_a, emb_b))
