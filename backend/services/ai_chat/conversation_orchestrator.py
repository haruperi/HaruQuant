"""Conversational turn orchestration for HaruQuant AI chat."""

from __future__ import annotations

from uuid import uuid4

from backend.contracts.page_context_packet.model import PageContextPacket
from backend.services.ai_chat.agent_router import ChatAgentRouter
from backend.services.ai_chat.clarification_policy import ClarificationPolicy
from backend.services.ai_chat.models import ConversationPlan, ConversationState, ConversationThreadRecord


class ConversationOrchestrator:
    """Build a lightweight plan for each incoming chat turn."""

    def __init__(
        self,
        *,
        agent_router: ChatAgentRouter | None = None,
        clarification_policy: ClarificationPolicy | None = None,
    ) -> None:
        self.agent_router = agent_router or ChatAgentRouter()
        self.clarification_policy = clarification_policy or ClarificationPolicy()

    def build_plan(
        self,
        *,
        prompt: str,
        thread: ConversationThreadRecord,
        page_context: PageContextPacket,
        conversation_state: ConversationState | None,
        tool_context: dict[str, object],
    ) -> ConversationPlan:
        route_decision = self.agent_router.route(prompt)
        clarification = self.clarification_policy.evaluate(
            prompt=prompt,
            thread=thread,
            page_context=page_context,
            conversation_state=conversation_state,
            tool_context=tool_context,
            route_decision=route_decision,
        )
        answer_mode = (
            "clarification"
            if clarification.needs_clarification
            else (
                "governed_artifact"
                if route_decision.response_mode.value in {"signal_proposal", "action_draft"}
                else "direct_answer"
            )
        )
        rationale_parts = [str(route_decision.rationale)]
        if clarification.rationale:
            rationale_parts.append(clarification.rationale)
        allowed_tools = getattr(route_decision, "allowed_tools", ()) or ()

        return ConversationPlan(
            conversation_plan_id=f"convplan_{uuid4().hex}",
            user_goal=self._infer_user_goal(prompt=prompt, page_context=page_context),
            answer_mode=answer_mode,
            response_mode=str(route_decision.response_mode.value),
            task_class=str(route_decision.task_class),
            model_tier=str(route_decision.model_tier),
            response_style=str(route_decision.response_style),
            domain_focus=str(route_decision.domain_focus),
            rationale=" ".join(rationale_parts),
            needs_clarification=clarification.needs_clarification,
            clarification_question=clarification.question,
            tools_to_run=[str(tool) for tool in allowed_tools],
            agents_to_consult=[],
        )

    @staticmethod
    def _infer_user_goal(*, prompt: str, page_context: PageContextPacket) -> str:
        prompt_text = " ".join(prompt.strip().split())
        if prompt_text:
            return prompt_text
        return f"Understand the current {page_context.payload.page_type} state."
