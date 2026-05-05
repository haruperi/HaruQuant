"""Tests for Phase 3: RAG System."""

from __future__ import annotations

import os
import tempfile

import pytest

from backend_retiring.retrieval.embeddings import EmbeddingService
from backend_retiring.retrieval.ingestion import DocumentIngester
from backend_retiring.retrieval.service import RetrievalService
from backend_retiring.retrieval.reformulation import RetrievalReformulator
from backend_retiring.retrieval.evaluation import RetrievalEvaluator
from backend_retiring.retrieval.models import DocumentChunk, RetrievalResult, TextChunk


@pytest.fixture(scope="module")
def embedding_service() -> EmbeddingService:
    return EmbeddingService(model="all-MiniLM-L6-v2")


@pytest.fixture
def retrieval_svc(embedding_service: EmbeddingService) -> RetrievalService:
    import uuid
    return RetrievalService(
        embeddings=embedding_service,
        collection_name=f"test_rag_{uuid.uuid4().hex[:8]}",
        persist_dir=None,  # In-memory for testing
    )


# ──────────────────────────────────────────────────────────────
# Embedding Service Tests
# ──────────────────────────────────────────────────────────────

def test_embedding_service_generates_vectors(embedding_service: EmbeddingService) -> None:
    """Embedding service should generate vectors of correct dimension."""
    vec = embedding_service.embed_single("test sentence")
    assert len(vec) == embedding_service.dimension
    # Normalized embedding should have magnitude ~1.0
    import math
    magnitude = math.sqrt(sum(v ** 2 for v in vec))
    assert abs(magnitude - 1.0) < 0.01


def test_embedding_service_batch(embedding_service: EmbeddingService) -> None:
    """Batch embedding should return correct number of vectors."""
    vecs = embedding_service.embed(["text one", "text two", "text three"])
    assert len(vecs) == 3
    assert all(len(v) == embedding_service.dimension for v in vecs)


def test_embedding_service_similarity(embedding_service: EmbeddingService) -> None:
    """Similar texts should have higher similarity than dissimilar."""
    sim_similar = embedding_service.similarity("stock market rising", "equity prices increasing")
    sim_dissimilar = embedding_service.similarity("stock market rising", "cooking pasta recipe")
    assert sim_similar > sim_dissimilar


# ──────────────────────────────────────────────────────────────
# Document Ingestion Tests
# ──────────────────────────────────────────────────────────────

def test_ingester_splits_into_chunks() -> None:
    """Ingester should split long documents into overlapping chunks."""
    embeddings = EmbeddingService(model="all-MiniLM-L6-v2")
    ingester = DocumentIngester(embeddings, chunk_size=10, chunk_overlap=2)
    content = " ".join([f"word{i}" for i in range(30)])
    chunks = ingester.ingest("doc_001", content, {"source": "test"})

    assert len(chunks) > 1
    assert all(c.doc_id == "doc_001" for c in chunks)
    assert all("source" in c.metadata for c in chunks)


def test_ingester_empty_content() -> None:
    """Empty content should produce no chunks."""
    embeddings = EmbeddingService(model="all-MiniLM-L6-v2")
    ingester = DocumentIngester(embeddings)
    chunks = ingester.ingest("doc_002", "")
    assert len(chunks) == 0


# ──────────────────────────────────────────────────────────────
# Retrieval Service Tests
# ──────────────────────────────────────────────────────────────

def test_retrieval_service_add_and_search(
    retrieval_svc: RetrievalService,
    embedding_service: EmbeddingService,
) -> None:
    """Should add chunks and find them via search."""
    ingester = DocumentIngester(embedding_service, chunk_size=20, chunk_overlap=5)
    chunks = ingester.ingest("doc_003", "EURUSD is a major forex currency pair that trades on the foreign exchange market", {"category": "market"})
    retrieval_svc.add_chunks(chunks)

    results = retrieval_svc.search("forex currency trading")
    assert len(results) >= 1
    assert results[0].score > 0.0


def test_retrieval_service_filter_by_metadata(
    retrieval_svc: RetrievalService,
    embedding_service: EmbeddingService,
) -> None:
    """Search should support metadata filtering."""
    ingester = DocumentIngester(embedding_service, chunk_size=20, chunk_overlap=5)

    chunks_a = ingester.ingest("doc_market", "stock market trading analysis", {"category": "market"})
    chunks_r = ingester.ingest("doc_risk", "risk management portfolio diversification", {"category": "risk"})
    retrieval_svc.add_chunks(chunks_a)
    retrieval_svc.add_chunks(chunks_r)

    # Filter to market category only
    results = retrieval_svc.search("trading analysis", filter_metadata={"category": "market"})
    for r in results:
        assert r.metadata.get("category") == "market"


def test_retrieval_service_empty_search(retrieval_svc: RetrievalService) -> None:
    """Search on empty collection should return empty results."""
    retrieval_svc.clear()
    results = retrieval_svc.search("anything")
    assert len(results) == 0


# ──────────────────────────────────────────────────────────────
# Reformulation Tests
# ──────────────────────────────────────────────────────────────

def test_reformulator_rephrases_on_empty(
    retrieval_svc: RetrievalService,
    embedding_service: EmbeddingService,
) -> None:
    """Reformulator should try reformulating when no results found."""
    reformulator = RetrievalReformulator(retrieval_svc, max_retries=2)
    # Collection is empty, so no results expected, but should not crash
    results = reformulator.search("nonexistent query xyz")
    assert isinstance(results, list)


# ──────────────────────────────────────────────────────────────
# Evaluation Tests
# ──────────────────────────────────────────────────────────────

def test_evaluator_mrr_perfect() -> None:
    """MRR should be 1.0 when first result is relevant."""
    evaluator = RetrievalEvaluator()
    result = evaluator.evaluate(
        query="test",
        expected_doc_ids={"doc_1"},
        retrieved_results=[{"doc_id": "doc_1"}, {"doc_id": "doc_2"}],
    )
    assert result.mrr == 1.0


def test_evaluator_mrr_partial() -> None:
    """MRR should be 1/rank when relevant doc is at position rank."""
    evaluator = RetrievalEvaluator()
    result = evaluator.evaluate(
        query="test",
        expected_doc_ids={"doc_1"},
        retrieved_results=[{"doc_id": "doc_3"}, {"doc_id": "doc_1"}],
    )
    assert abs(result.mrr - 0.5) < 0.01


def test_evaluator_recall_at_k() -> None:
    """Recall@K should measure fraction of expected docs found."""
    evaluator = RetrievalEvaluator()
    result = evaluator.evaluate(
        query="test",
        expected_doc_ids={"doc_1", "doc_2", "doc_3"},
        retrieved_results=[{"doc_id": "doc_1"}, {"doc_id": "doc_2"}],
    )
    assert abs(result.recall_at_k - 2/3) < 0.01  # Found 2 of 3


def test_evaluator_empty_expected() -> None:
    """Evaluation with no expected docs should return defaults."""
    evaluator = RetrievalEvaluator()
    result = evaluator.evaluate(
        query="test",
        expected_doc_ids=set(),
        retrieved_results=[{"doc_id": "doc_1"}],
    )
    assert result.recall_at_k == 1.0
