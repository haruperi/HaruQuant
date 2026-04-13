"""Retrieval quality evaluation — MRR, NDCG, Recall@K."""

from __future__ import annotations

import math

from .models import RetrievalEvalResult


class RetrievalEvaluator:
    """Evaluates retrieval quality using standard IR metrics."""

    def evaluate(
        self,
        query: str,
        expected_doc_ids: set[str],
        retrieved_results: list[dict[str, str]],
    ) -> RetrievalEvalResult:
        """Evaluate retrieval against expected documents.

        Args:
            query: The search query
            expected_doc_ids: Set of doc_ids that should be retrieved
            retrieved_results: List of dicts with 'doc_id' key
        """
        retrieved_ids = [r.get("doc_id", "") for r in retrieved_results]

        return RetrievalEvalResult(
            query=query,
            expected_doc_ids=expected_doc_ids,
            retrieved_doc_ids=retrieved_ids,
            mrr=self._mrr(retrieved_ids, expected_doc_ids),
            ndcg=self._ndcg(retrieved_ids, expected_doc_ids),
            recall_at_k=self._recall_at_k(retrieved_ids, expected_doc_ids),
        )

    @staticmethod
    def _mrr(retrieved: list[str], expected: set[str]) -> float:
        """Mean Reciprocal Rank — 1/rank of first relevant doc."""
        for i, doc_id in enumerate(retrieved):
            if doc_id in expected:
                return 1.0 / (i + 1)
        return 0.0

    @staticmethod
    def _ndcg(retrieved: list[str], expected: set[str], k: int = 5) -> float:
        """Normalized Discounted Cumulative Gain."""
        if not retrieved or not expected:
            return 0.0

        # DCG: sum of rel_i / log2(i+1)
        dcg = 0.0
        for i, doc_id in enumerate(retrieved[:k]):
            if doc_id in expected:
                dcg += 1.0 / math.log2(i + 2)

        # Ideal DCG: all expected docs in top positions
        ideal_count = min(len(expected), k)
        idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_count))

        return dcg / idcg if idcg > 0 else 0.0

    @staticmethod
    def _recall_at_k(retrieved: list[str], expected: set[str], k: int = 5) -> float:
        """Recall@K — fraction of expected docs found in top K."""
        if not expected:
            return 1.0
        retrieved_at_k = set(retrieved[:k])
        found = len(retrieved_at_k & expected)
        return found / len(expected)
