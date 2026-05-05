"""Natural response composition for conversational chat answers."""

from __future__ import annotations

from backend.agents.chat.ai_chat.models import SpecialistAgentArtifact
from backend.agents.chat.ai_chat.tool_executor import ToolExecutionResult


class ResponseComposer:
    """Compose concise user-facing answers from structured intermediate results."""

    def compose_knowledge_dialogue(
        self,
        *,
        user_prompt: str,
        page_context,
        tool_results: list[ToolExecutionResult],
        specialist_artifacts: list[SpecialistAgentArtifact],
    ) -> str:
        knowledge_result = self._result(tool_results, "internal_knowledge")
        matches = []
        if knowledge_result is not None:
            payload_matches = knowledge_result.payload.get("matches") or []
            if isinstance(payload_matches, list):
                matches = [match for match in payload_matches if isinstance(match, dict)]

        if not matches:
            return (
                "I could not find a relevant internal HaruQuant document for that request. "
                "Try naming the document area, feature, or workflow more explicitly."
            )

        lead_sources = self._unique(
            str(match.get("filename") or match.get("citation") or "Unknown Document")
            for match in matches[:3]
        )
        lead_source_text = ", ".join(lead_sources)
        top_excerpt = self._excerpt(str(matches[0].get("content") or ""))
        second_excerpt = self._excerpt(str(matches[1].get("content") or "")) if len(matches) > 1 else ""
        page_type = str(page_context.payload.page_type).replace("_", " ")
        specialist_hint = specialist_artifacts[0].summary if specialist_artifacts else ""

        parts = [
            f"I found relevant HaruQuant documentation in {lead_source_text}.",
            top_excerpt and f"The strongest match says {top_excerpt}",
            second_excerpt and f"A second relevant source adds {second_excerpt}",
            page_context.payload.page_type != "generic"
            and f"Given the current {page_type} page, use that guidance against the live page state rather than treating the document as the source of truth for metrics."
            or "",
            specialist_hint,
        ]
        return " ".join(part for part in parts if part)

    @staticmethod
    def _result(tool_results: list[ToolExecutionResult], tool_name: str) -> ToolExecutionResult | None:
        for result in tool_results:
            if result.tool_name == tool_name and result.success:
                return result
        return None

    @staticmethod
    def _excerpt(content: str) -> str:
        normalized = " ".join(content.split())
        if not normalized:
            return ""
        if len(normalized) <= 220:
            return normalized
        return f"{normalized[:217]}..."

    @staticmethod
    def _unique(values) -> list[str]:
        seen: list[str] = []
        for value in values:
            if value and value not in seen:
                seen.append(value)
        return seen
