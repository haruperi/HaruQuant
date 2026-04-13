"""Data models for the RAG retrieval system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TextChunk:
    """A chunk of text from document splitting."""
    content: str


@dataclass(frozen=True)
class DocumentChunk:
    """A chunk of a document with embedding and metadata."""
    doc_id: str
    chunk_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class RetrievalResult:
    """A single retrieval result with relevance score."""
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0  # 0.0 to 1.0, higher = more relevant
    doc_id: str = ""
    chunk_id: str = ""


@dataclass(frozen=True)
class RetrievalEvalResult:
    """Evaluation result for a retrieval query."""
    query: str
    expected_doc_ids: set[str] = field(default_factory=set)
    retrieved_doc_ids: list[str] = field(default_factory=list)
    mrr: float = 0.0  # Mean Reciprocal Rank
    ndcg: float = 0.0  # Normalized Discounted Cumulative Gain
    recall_at_k: float = 0.0
