"""Retrieval reformulation loop — rephrases queries when results are poor."""

from __future__ import annotations

from .models import RetrievalResult
from .service import RetrievalService


class RetrievalReformulator:
    """If retrieval returns no or poor results, reformulate the query."""

    def __init__(
        self,
        retrieval: RetrievalService,
        max_retries: int = 2,
        min_relevance: float = 0.3,
    ) -> None:
        self._retrieval = retrieval
        self._max_retries = max_retries
        self._min_relevance = min_relevance

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """Search with automatic query reformulation."""
        current_query = query
        for _ in range(self._max_retries + 1):
            results = self._retrieval.search(current_query, top_k)
            if self._results_are_adequate(results):
                return results
            current_query = self._reformulate_query(current_query)
        return results  # Return best effort after all retries

    def _results_are_adequate(self, results: list[RetrievalResult]) -> bool:
        """Check if any result meets the minimum relevance threshold."""
        if not results:
            return False
        return any(r.score >= self._min_relevance for r in results)

    def _reformulate_query(self, query: str) -> str:
        """Generate a reformulated query using simple heuristics.

        In production, this would use an LLM to rephrase. For now,
        uses keyword expansion heuristics.
        """
        # Simple reformulation: add synonyms/related terms
        # Production: call LLM with "Rephrase this query for better retrieval"
        expansions = {
            "EURUSD": "EURUSD forex currency pair euro dollar",
            "trend": "trend momentum direction",
            "volatility": "volatility variance standard deviation",
            "risk": "risk exposure drawdown",
        }
        for keyword, expansion in expansions.items():
            if keyword.lower() in query.lower():
                return f"{query} {expansion}"
        return query + " related context"
