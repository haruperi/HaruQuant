from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend_retiring.tools.read_only.knowledge import InternalKnowledgeTool


def test_internal_knowledge_tool_initializes_retrieval_lazily() -> None:
    with patch("backend_retiring.tools.read_only.knowledge.EmbeddingService") as embedding_cls, patch(
        "backend_retiring.tools.read_only.knowledge.RetrievalService"
    ) as retrieval_cls:
        tool = InternalKnowledgeTool()

        embedding_cls.assert_not_called()
        retrieval_cls.assert_not_called()

        retrieval = MagicMock()
        retrieval.search.return_value = []
        retrieval_cls.return_value = retrieval

        payload = tool.run(user_id=1, context={"query": "chatbot rollout runbook"})

        embedding_cls.assert_called_once()
        retrieval_cls.assert_called_once()
        retrieval.search.assert_called_once_with(query="chatbot rollout runbook", top_k=5)
        assert payload["matches"] == []
