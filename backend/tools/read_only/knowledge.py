"""Internal Knowledge read-only tool for HaruQuant AI Chatbot."""

from __future__ import annotations

from typing import Any

from backend.retrieval.embeddings import EmbeddingService
from backend.retrieval.service import RetrievalService


class InternalKnowledgeTool:
    """Tool to query internal platform documentation and reports via RAG."""

    name = "internal_knowledge"

    def __init__(self, db_dir: str = "backend/data/knowledge_db") -> None:
        self._db_dir = db_dir
        self._embeddings: EmbeddingService | None = None
        self._retrieval: RetrievalService | None = None

    def _get_retrieval(self) -> RetrievalService:
        if self._retrieval is None:
            self._embeddings = EmbeddingService()
            self._retrieval = RetrievalService(
                embeddings=self._embeddings,
                persist_dir=self._db_dir,
                collection_name="haruquant_knowledge",
            )
        return self._retrieval

    def run(self, *, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        """Execute knowledge retrieval.
        
        Args:
            context: Expects a "query" key containing the user's natural language question.
        """
        query = context.get("query", "")
        if not query:
            # Maybe the query is nested inside arguments if the LLM provided it differently
            # Fallback check
            query = context.get("arguments", {}).get("query", "")
            
        if not query:
            return {"error": "A 'query' string is required in the context to search internal knowledge."}

        # Retrieve top 5 most relevant chunks
        results = self._get_retrieval().search(query=query, top_k=5)

        if not results:
            return {
                "query": query,
                "matches": [],
                "message": "No relevant internal documentation found for the given query."
            }

        # Format results with citation provenance
        matches = []
        for res in results:
            matches.append({
                "content": res.content,
                "relevance_score": round(res.score, 4),
                "citation": res.metadata.get("doc_id", "Unknown Document"),
                "chunk": res.metadata.get("chunk_id", "Unknown Chunk"),
                "filename": res.metadata.get("filename", "Unknown File"),
            })

        return {
            "query": query,
            "matches": matches,
            "message": f"Found {len(matches)} relevant excerpts from internal knowledge."
        }
