"""Prompt composition for the HaruQuant AI chat gateway."""

from __future__ import annotations

from dataclasses import dataclass

from backend.contracts.page_context_packet.model import PageContextPacket
from backend.services.ai_chat.domain_intelligence import resolve_domain_prompt_spec
from backend.services.ai_chat.models import (
    ConversationState,
    ConversationThreadRecord,
    SpecialistAgentArtifact,
)
from backend.services.ai_chat.page_retrieval import RetrievedPageChunk


@dataclass(frozen=True)
class BuiltPrompt:
    system_prompt: str
    user_prompt: str
    debug: dict[str, object]


class ContextCompactor:
    """Helper to ensure prompt content stays within token/character budget."""

    @staticmethod
    def truncate_text(text: str, max_chars: int = 1000) -> str:
        if len(text) <= max_chars:
            return text
        return f"{text[:max_chars]}... [truncated {len(text) - max_chars} characters]"

    @staticmethod
    def truncate_json(data: str, max_chars: int = 2000) -> str:
        if len(data) <= max_chars:
            return data
        return f"{data[:max_chars]}... [large JSON truncated]"


class ChatPromptBuilder:
    """Compose layered prompts from context, memory, and recent conversation."""

    def __init__(self, compactor: ContextCompactor | None = None) -> None:
        self.compactor = compactor or ContextCompactor()

    def build(
        self,
        *,
        thread: ConversationThreadRecord,
        page_context: PageContextPacket,
        conversation_state: ConversationState | None,
        specialist_artifacts: list[SpecialistAgentArtifact] | None,
        page_chunks: list[RetrievedPageChunk] | None,
        user_prompt: str,
        response_mode: str,
        task_class: str = "performance_summary",
    ) -> BuiltPrompt:
        prompt_spec = resolve_domain_prompt_spec(task_class)
        requires_structured_sections = response_mode in {"signal_proposal", "action_draft"}
        recent_messages = thread.messages[-6:]
        memory_summary = thread.memory_summary.summary_text if thread.memory_summary else "No memory summary yet."
        pinned_facts = [
            f"{fact.key}={fact.value} ({fact.source})"
            for fact in thread.pinned_facts[:6]
        ] or ["none"]
        state = conversation_state or ConversationState(active_topic="unknown")
        active_entities = [
            f"{entity.type}:{entity.id}:{entity.label or ''}".rstrip(":")
            for entity in state.active_entities[:6]
        ] or ["none"]
        resolved_references = [
            f"{key}={value}"
            for key, value in list(state.resolved_references.items())[:8]
        ] or ["none"]
        user_preferences = [
            f"{key}={value}"
            for key, value in list(state.user_preferences.items())[:6]
        ] or ["none"]
        artifacts = specialist_artifacts or []
        specialist_summaries = [
            f"{artifact.agent_name}: {artifact.summary}"
            for artifact in artifacts[:4]
        ] or ["none"]
        retrieved_page_chunks = page_chunks or []
        page_chunk_summaries = [
            f"{chunk.block_type}:{chunk.title}: {self.compactor.truncate_text(chunk.content, 320)}"
            for chunk in retrieved_page_chunks[:4]
        ] or ["none"]
        required_sections = "; ".join(prompt_spec.section_headers) if requires_structured_sections and prompt_spec.section_headers else ""

        system_prompt = "\n".join(
            [
                "You are the HaruQuant AI Copilot.",
                "Prioritize current validated HaruQuant state over earlier chat assumptions.",
                "Stay within read-only assistance. Do not claim any action was executed.",
                "Default to a natural conversational answer.",
                "Use one or two short paragraphs unless the user explicitly asks for structure or the task is a governed artifact.",
                "Do not echo internal metadata such as response mode, response style, task class, request id, context revision, or tool policy labels.",
                "Do not restate the user's request before answering unless the clarification itself depends on it.",
                "If you need a clarification, ask one short direct question and stop there.",
                "If a visible page snapshot is present, treat its headings, tables, and text as first-class context for page-summary questions.",
                "When retrieved current-page chunks are present, answer from those chunks before falling back to generic page summaries.",
                "When summarizing a current page with visible results, cite the visible values rather than defaulting to generic HaruQuant dashboard language.",
                f"Response mode: {response_mode}",
                f"Task class: {task_class}",
                f"Domain focus: {prompt_spec.domain_focus}",
                f"Response style: {prompt_spec.response_style}",
                f"Prompt goal: {prompt_spec.prompt_goal}",
                f"Current page type: {page_context.payload.page_type}",
                f"Current page headline: {page_context.payload.summary.headline}",
                f"Context authority: {page_context.payload.authority.trust_level}",
                f"Memory summary: {memory_summary}",
                f"Pinned facts: {'; '.join(pinned_facts)}",
                f"Conversation topic: {state.active_topic}",
                f"Resolved references: {'; '.join(resolved_references)}",
                f"User preferences: {'; '.join(user_preferences)}",
                f"Specialist agent context: {'; '.join(specialist_summaries)}",
                f"Retrieved current-page chunks: {'; '.join(page_chunk_summaries)}",
                *([f"Required sections: {required_sections}"] if required_sections else []),
                f"Quantitative rules: {'; '.join(prompt_spec.quantitative_rules)}",
            ]
        )

        transcript_lines = [
            f"{message.role.upper()}: {self.compactor.truncate_text(message.content, 500)}"
            for message in recent_messages
        ] or ["No recent messages."]
        page_bullets = page_context.payload.summary.bullets or ["none"]
        entity_refs = [
            f"{entity.type}:{entity.id}:{entity.label or ''}".rstrip(":")
            for entity in page_context.payload.entity_refs[:6]
        ] or ["none"]
        visible_snapshot = page_context.payload.payload.get("dom")
        visible_snapshot_text = (
            self.compactor.truncate_json(str(visible_snapshot), 1800)
            if visible_snapshot
            else "none"
        )
        registered_page_intelligence = page_context.payload.payload.get("page_intelligence")
        registered_page_intelligence_text = (
            self.compactor.truncate_json(str(registered_page_intelligence), 1800)
            if registered_page_intelligence
            else "none"
        )

        composed_user_prompt = "\n".join(
            [
                f"Current route: {page_context.payload.route}",
                f"Context revision: {page_context.payload.context_revision}",
                f"Page entities: {'; '.join(entity_refs)}",
                f"Page bullets: {'; '.join(page_bullets)}",
                f"Visible page snapshot: {visible_snapshot_text}",
                f"Registered page intelligence: {registered_page_intelligence_text}",
                f"Retrieved current-page evidence: {'; '.join(page_chunk_summaries)}",
                f"Conversation state entities: {'; '.join(active_entities)}",
                f"Conversation resolved references: {'; '.join(resolved_references)}",
                f"Specialist summaries: {'; '.join(specialist_summaries)}",
                "Recent conversation:",
                *transcript_lines,
                *([f"Expected response sections: {required_sections}"] if required_sections else []),
                "User request:",
                user_prompt.strip(),
            ]
        )

        return BuiltPrompt(
            system_prompt=system_prompt,
            user_prompt=composed_user_prompt,
            debug={
                "page_type": page_context.payload.page_type,
                "context_revision": page_context.payload.context_revision,
                "response_mode": response_mode,
                "task_class": task_class,
                "response_style": prompt_spec.response_style,
                "active_topic": state.active_topic,
                "resolved_reference_count": len(state.resolved_references),
                "specialist_agent_count": len(artifacts),
                "page_chunk_count": len(retrieved_page_chunks),
                "recent_message_count": len(recent_messages),
            },
        )
