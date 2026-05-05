"""Conversational turn orchestration for HaruQuant AI chat."""

from __future__ import annotations

from uuid import uuid4

from backend.contracts.page_context_packet.model import PageContextPacket
from backend.agents.chat.ai_chat.agent_router import ChatAgentRouter
from backend.agents.chat.ai_chat.clarification_policy import ClarificationPolicy
from backend.agents.chat.ai_chat.conversation_planner import ConversationPlanner
from backend.agents.chat.ai_chat.models import ConversationPlan, ConversationState, ConversationThreadRecord


class ConversationOrchestrator:
    """Build a lightweight plan for each incoming chat turn."""

    def __init__(
        self,
        *,
        agent_router: ChatAgentRouter | None = None,
        clarification_policy: ClarificationPolicy | None = None,
        planner: ConversationPlanner | None = None,
    ) -> None:
        self.agent_router = agent_router or ChatAgentRouter()
        self.clarification_policy = clarification_policy or ClarificationPolicy()
        self.planner = planner or ConversationPlanner()

    def build_plan(
        self,
        *,
        prompt: str,
        thread: ConversationThreadRecord,
        page_context: PageContextPacket,
        conversation_state: ConversationState | None,
        tool_context: dict[str, object],
    ) -> ConversationPlan:
        structured = self.planner.plan(
            prompt=prompt,
            thread=thread,
            page_context=page_context,
            conversation_state=conversation_state,
            tool_context=tool_context,
        )
        route_decision = self.agent_router.route(prompt)
        clarification = self.clarification_policy.evaluate(
            prompt=prompt,
            thread=thread,
            page_context=page_context,
            conversation_state=conversation_state,
            tool_context=tool_context,
            route_decision=route_decision,
        )
        policy_needs_clarification = clarification.needs_clarification and not structured.needs_clarification
        needs_clarification = structured.needs_clarification or policy_needs_clarification
        answer_mode = (
            "clarification"
            if needs_clarification
            else (
                "governed_artifact"
                if structured.response_mode in {"signal_proposal", "action_draft"} or structured.artifact_expected
                else structured.answer_mode
            )
        )
        rationale_parts = [structured.rationale]
        if clarification.rationale:
            rationale_parts.append(clarification.rationale)
        route_allowed_tools = getattr(route_decision, "allowed_tools", ()) or ()
        allowed_tools = tuple(dict.fromkeys((*structured.backend_tools_to_run, *route_allowed_tools)))

        return ConversationPlan(
            conversation_plan_id=f"convplan_{uuid4().hex}",
            user_goal=structured.user_goal,
            answer_mode=answer_mode,
            response_mode=structured.response_mode,
            task_class=structured.task_class,
            model_tier=structured.model_tier,
            response_style=structured.response_style,
            domain_focus=structured.domain_focus,
            rationale=" ".join(rationale_parts),
            needs_clarification=needs_clarification,
            clarification_question=structured.clarification_question or clarification.question,
            intent=structured.intent,
            missing_inputs=list(structured.missing_inputs) or ([] if not clarification.needs_clarification else ["unresolved_reference"]),
            context_needed=list(structured.context_needed),
            backend_tools_to_run=[str(tool) for tool in allowed_tools],
            tools_to_run=[str(tool) for tool in allowed_tools],
            agents_to_consult=list(structured.specialist_agents_to_run),
            attached_tools=list(structured.attached_tools),
            page_actions_to_plan=list(structured.page_actions_to_plan),
            artifact_expected=structured.artifact_expected,
            risk_level=structured.risk_level,
            planner_source=structured.planner_source,
            planner_confidence=structured.confidence,
        )

    @staticmethod
    def _infer_user_goal(*, prompt: str, page_context: PageContextPacket) -> str:
        prompt_text = " ".join(prompt.strip().split())
        if prompt_text:
            return prompt_text
        return f"Understand the current {page_context.payload.page_type} state."
