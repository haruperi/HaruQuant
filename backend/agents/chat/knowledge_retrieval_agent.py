"""Knowledge retrieval specialist for doc-grounded conversational answers."""

from __future__ import annotations

from typing import Any

from backend.agents.chat.ai_chat.models import SpecialistAgentArtifact
from backend.agents.chat.ai_chat.tool_executor import ToolExecutionResult

from .agent_base import SpecialistAgentBase


class KnowledgeRetrievalAgent(SpecialistAgentBase):
    """LLM-backed documentation synthesis specialist.

    Synthesizes retrieved internal HaruQuant documentation excerpts into a
    direct answer grounded in the matched documents. Falls back to
    deterministic excerpt-building if the LLM is unavailable.
    """

    agent_name = "knowledge_retrieval_agent"

    SYSTEM_PROMPT = """You are HaruQuant's Documentation specialist.
Synthesize the provided retrieved document excerpts into a direct answer.

Output schema (JSON only, no markdown):
{
  "summary": "<instruction for the final composer — what the docs say and how to apply it>",
  "findings": ["<key point from excerpt 1>", "<key point from excerpt 2>", ...],
  "evidence": ["filename (score=N)", ...],
  "sources": ["filename", ...],
  "recommendation": "<ask a narrower follow-up if still unclear, or cite the primary doc>",
  "confidence": <integer 0-100>
}

Rules:
- every finding must be grounded in the retrieved excerpt text provided
- do not claim facts not present in the excerpts
- if two excerpts contradict each other, add a finding that names the contradiction
- sources must list only filenames from the provided excerpts
- confidence reflects how well the excerpts match the user query (0=no match, 100=direct answer)
- maximum 4 findings, maximum 4 evidence items, maximum 4 sources
"""

    def analyze(
        self,
        *,
        task_class: str,
        tool_results: list[ToolExecutionResult],
        page_context: Any,
        tool_context: dict[str, object],
    ) -> SpecialistAgentArtifact | None:
        knowledge = self._get_result(tool_results, "internal_knowledge")
        if knowledge is None:
            return None

        payload = knowledge.payload
        matches = payload.get("matches") or []
        if not isinstance(matches, list) or not matches:
            return None

        deterministic = self._deterministic_artifact(
            task_class=task_class,
            matches=matches,
            payload=payload,
            page_context=page_context,
            tool_context=tool_context,
        )

        user_payload = self._build_user_payload(
            matches=matches,
            query=str(payload.get("query") or tool_context.get("query") or ""),
            task_class=task_class,
        )
        raw = self._call_llm_plan(user_payload=user_payload, max_output_tokens=500)
        return self._validated_artifact(raw=raw, task_class=task_class, fallback=deterministic)

    @staticmethod
    def _build_user_payload(
        *,
        matches: list[Any],
        query: str,
        task_class: str,
    ) -> dict[str, Any]:
        return {
            "task_class": task_class,
            "query": query,
            "excerpts": [
                {
                    "filename": str(m.get("filename") or m.get("citation") or "Unknown"),
                    "relevance_score": m.get("relevance_score"),
                    "content": str(m.get("content") or "")[:400],
                }
                for m in (matches[:4] if isinstance(matches, list) else [])
                if isinstance(m, dict)
            ],
        }

    def _deterministic_artifact(
        self,
        *,
        task_class: str,
        matches: list[Any],
        payload: dict[str, object],
        page_context: Any,
        tool_context: dict[str, object],
    ) -> SpecialistAgentArtifact | None:
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
            f"Synthesize it as a direct answer and keep the current {page_type} context "
            f"in view when it matters."
        )

        return SpecialistAgentArtifact(
            agent_name=self.agent_name,
            task_class=task_class,
            summary=summary,
            findings=findings or ["Relevant internal documentation was retrieved for this request."],
            evidence=evidence or [page_context.payload.summary.headline],
            sources=list(dict.fromkeys(sources)),
            recommendation=(
                "Answer directly, cite the most relevant document names, and ask a "
                "narrower follow-up only if the topic is still too broad."
            ),
            confidence=82,
        )

    @staticmethod
    def _excerpt(content: str) -> str:
        normalized = " ".join(content.split())
        if len(normalized) <= 180:
            return normalized
        return f"{normalized[:177]}..."
