"""Knowledge retrieval specialist for doc-grounded conversational answers."""

from __future__ import annotations

from backend.services.ai_chat.models import SpecialistAgentArtifact
from backend.services.tool_executor import ToolExecutionResult


class KnowledgeRetrievalAgent:
    agent_name = "knowledge_retrieval_agent"

    def analyze(
        self,
        *,
        task_class: str,
        tool_results: list[ToolExecutionResult],
        page_context,
        tool_context: dict[str, object],
    ) -> SpecialistAgentArtifact | None:
        knowledge = self._result(tool_results, "internal_knowledge")
        if knowledge is None:
            return None

        payload = knowledge.payload
        matches = payload.get("matches") or []
        if not isinstance(matches, list) or not matches:
            return None

        findings: list[str] = []
        evidence: list[str] = []
        sources: list[str] = []

        for match in matches[:3]:
            if not isinstance(match, dict):
                continue
            filename = str(match.get("filename") or match.get("citation") or "Unknown Document")
            score = match.get("relevance_score")
            content = str(match.get("content") or "").strip()
            summary = self._excerpt(content)
            if summary:
                findings.append(summary)
            evidence.append(f"{filename} (score={score})")
            sources.append(filename)

        query = str(payload.get("query") or tool_context.get("query") or "the requested topic")
        page_type = str(page_context.payload.page_type).replace("_", " ")
        summary = (
            f"Internal knowledge retrieval found relevant HaruQuant documentation for {query}. "
            f"Synthesize it as a direct answer and keep the current {page_type} context in view when it matters."
        )

        return SpecialistAgentArtifact(
            agent_name=self.agent_name,
            task_class=task_class,
            summary=summary,
            findings=findings or ["Relevant internal documentation was retrieved for this request."],
            evidence=evidence or [page_context.payload.summary.headline],
            sources=list(dict.fromkeys(sources)),
            recommendation="Answer directly, cite the most relevant document names, and ask a narrower follow-up only if the topic is still too broad.",
            confidence=82,
        )

    @staticmethod
    def _result(tool_results: list[ToolExecutionResult], tool_name: str) -> ToolExecutionResult | None:
        for result in tool_results:
            if result.tool_name == tool_name and result.success:
                return result
        return None

    @staticmethod
    def _excerpt(content: str) -> str:
        normalized = " ".join(content.split())
        if len(normalized) <= 180:
            return normalized
        return f"{normalized[:177]}..."
