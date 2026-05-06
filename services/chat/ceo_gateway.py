"""CEO Agent gateway for the global HaruQuant chat widget."""

from __future__ import annotations

from collections.abc import Iterator
import time
from uuid import uuid4

from agents.ceo import CEOAgent
from agents.planner import PlannerAgent
from agents.schemas import AgentPlan
from services.context.service import PageContextService
from services.conversation.service import ConversationService
from services.schemas.chat import (
    ChatResponseMetadata,
    ChatToolDefinition,
    ChatTurnRequest,
    ChatTurnResult,
    PageContext,
)
from tools.registry import DEFAULT_TOOL_REGISTRY


READ_ONLY_AGENT_NAME = "ceo_agent"


class CEOChatGateway:
    """Routes chat turns through PlannerAgent and CEOAgent.

    This gateway deliberately uses deterministic agent behavior today. Real LLM
    synthesis can be attached later through the existing CEO/Planner extension
    points without changing the UI contract.
    """

    def __init__(
        self,
        conversation_service: ConversationService,
        *,
        planner: PlannerAgent | None = None,
        ceo: CEOAgent | None = None,
        context_service: PageContextService | None = None,
    ) -> None:
        self.conversations = conversation_service
        self.planner = planner or PlannerAgent()
        self.ceo = ceo or CEOAgent()
        self.context_service = context_service or PageContextService()

    def handle_turn(self, *, thread_id: str, user_id: str, request: ChatTurnRequest) -> ChatTurnResult:
        started = time.perf_counter()
        request_id = request.request_id or f"chat-{uuid4()}"
        page_context = self.context_service.from_chat_request(request)
        self.conversations.update_context(
            thread_id=thread_id,
            user_id=user_id,
            current_route=page_context.route,
            current_page_type=page_context.page_type,
            active_context_revision=page_context.context_revision,
        )
        user_message = self.conversations.add_message(
            thread_id=thread_id,
            user_id=user_id,
            role="user",
            content=request.prompt,
            request_id=request_id,
            context_revision=page_context.context_revision,
        )

        planner_result = self.planner.create_plan(user_request=request.prompt, request_id=request_id)
        agent_outputs = self._build_agent_outputs(plan=planner_result, page_context=page_context)
        memo = self.ceo.create_final_memo(
            request=request.prompt,
            planner_result=planner_result,
            agent_outputs=agent_outputs,
            evidence_refs=self._evidence_refs(planner_result, page_context),
        )
        response_text = format_ceo_memo(memo=memo, plan=planner_result, page_context=page_context)
        latency_ms = int((time.perf_counter() - started) * 1000)
        metadata = self._metadata(
            request_id=request_id,
            plan=planner_result,
            memo=memo,
            page_context=page_context,
            attached_tools=request.attached_tools,
            latency_ms=latency_ms,
        )
        assistant_message = self.conversations.add_message(
            thread_id=thread_id,
            user_id=user_id,
            role="assistant",
            content=response_text,
            request_id=request_id,
            context_revision=page_context.context_revision,
            tool_calls=metadata.tools_used,
            metadata=metadata,
            latency_ms=latency_ms,
        )
        return ChatTurnResult(
            thread=self.conversations.get_thread(thread_id=thread_id, user_id=user_id),
            user_message=user_message,
            assistant_message=assistant_message,
            metadata=metadata,
        )

    def stream_turn(self, *, thread_id: str, user_id: str, request: ChatTurnRequest) -> Iterator[tuple[str, dict[str, object]]]:
        result = self.handle_turn(thread_id=thread_id, user_id=user_id, request=request)
        yield "meta", result.metadata.model_dump()
        for token in _chunk_text(result.assistant_message.content):
            yield "token", {"delta": token}
        yield "done", {
            "message_id": result.assistant_message.message_id,
            "thread": result.thread.model_dump(),
            "metadata": result.metadata.model_dump(),
        }

    def _build_agent_outputs(self, *, plan: AgentPlan, page_context: PageContext) -> dict[str, object]:
        return {
            "planner": plan.model_dump(),
            "page_context": page_context.model_dump(),
        }

    def _evidence_refs(self, plan: AgentPlan, page_context: PageContext) -> list[str]:
        refs = list(plan.evidence_requirements)
        if page_context.route:
            refs.append(f"ui:{page_context.route}")
        return refs

    def _metadata(
        self,
        *,
        request_id: str,
        plan: AgentPlan,
        memo: dict[str, object],
        page_context: PageContext,
        attached_tools: list[str],
        latency_ms: int,
    ) -> ChatResponseMetadata:
        tools = [
            tool.name
            for tool in DEFAULT_TOOL_REGISTRY.list_tools(risk_level="read_only", enabled=True)
            if "*" in (tool.allowed_agents or []) or READ_ONLY_AGENT_NAME in (tool.allowed_agents or [])
        ][:8]
        specialist_agents = [agent for agent in plan.allowed_agents if agent != "ceo"]
        return ChatResponseMetadata(
            request_id=request_id,
            response_mode=_response_mode(plan=plan, memo=memo),
            response_style=plan.response_style,
            task_class=plan.task_class,
            domain_focus=plan.domain_focus,
            answer_mode="ceo_agent_gateway",
            generation_source="deterministic:planner_ceo_gateway",
            provider_name=None,
            model="deterministic",
            tools_used=tools,
            conversation_plan_id=plan.conversation_plan_id,
            clarification_required=plan.needs_clarification,
            active_topic=plan.intent,
            specialist_agents_used=specialist_agents,
            telemetry={
                "latency_ms": latency_ms,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
            },
            cost_policy={
                "request_budget_key": "ceo_chat_deterministic",
                "estimated_cost_usd": 0.0,
                "budget_downgraded": False,
                "workflow_cost_usd": 0.0,
                "within_workflow_budget": True,
            },
            attached_tools=[{"tool_id": tool_id, "display_name": tool_id, "authority_band": "read_only", "side_effect_policy": "none", "capability_type": "operator_hint"} for tool_id in attached_tools],
            ceo_memo=memo,
            planner=plan.model_dump(),
            page_context=page_context.model_dump(),
            audit={
                "event": "ceo_chat_turn",
                "live_execution_enabled": False,
                "risk_governor_bypass_allowed": False,
            },
        )


def list_ceo_chat_tools() -> list[ChatToolDefinition]:
    tools: list[ChatToolDefinition] = []
    for tool in DEFAULT_TOOL_REGISTRY.list_tools(risk_level="read_only", enabled=True):
        if READ_ONLY_AGENT_NAME not in (tool.allowed_agents or []) and "*" not in (tool.allowed_agents or []):
            continue
        tools.append(
            ChatToolDefinition(
                tool_id=tool.name,
                display_name=tool.name.replace("_", " ").title(),
                description=tool.description,
                capability_type=tool.category,
                authority_band="read_only",
                side_effect_policy="none",
                input_schema=tool.input_schema or {},
                output_schema=tool.output_schema or {},
                required_context=[],
                allowed_backend_tools=[tool.name],
                allowed_specialist_agents=tool.allowed_agents or [],
                artifact_type=tool.domain,
                required_user_ack=False,
            )
        )
    return tools


def format_ceo_memo(*, memo: dict[str, object], plan: AgentPlan, page_context: PageContext) -> str:
    memo_type = str(memo.get("memo_type", "ceo_memo"))
    if memo_type == "ceo_identity":
        return (
            "I am HaruQuant AI, the CEO/CIO-style coordinator for the agentic trading firm. "
            "I can plan work, delegate to specialist agents, explain evidence, draft governed actions, "
            "and prepare recommendations. I cannot place live trades, bypass RiskGovernor, alter audit, "
            "or approve my own deployment."
        )
    if memo_type in {"rejection", "blocked_by_risk"}:
        return str(memo.get("reason") or memo.get("summary") or "This request is blocked by HaruQuant governance.")
    if "answer" in memo:
        return str(memo["answer"])

    decision = str(memo.get("decision", "planned"))
    summary = str(memo.get("summary", "CEO Agent prepared a governed firm workflow."))
    route = page_context.route or "current page"
    agents = ", ".join(agent for agent in plan.allowed_agents if agent != "ceo") or "CEO"
    return (
        f"{summary}\n\n"
        f"Decision: {decision}.\n"
        f"Route: {plan.intent} on {route}.\n"
        f"Delegation path: {agents}.\n"
        "Execution boundary: no live or paper side effect was executed from chat."
    )


def _response_mode(*, plan: AgentPlan, memo: dict[str, object]) -> str:
    memo_type = str(memo.get("memo_type", ""))
    if memo_type in {"rejection", "blocked_by_risk"}:
        return "blocked_by_policy"
    if plan.requires_board_approval:
        return "approval_request"
    if plan.intent == "strategy_creation":
        return "strategy_spec_draft"
    if plan.intent == "risk_review":
        return "risk_memo"
    if plan.intent == "research":
        return "research_memo"
    return plan.response_mode or "direct_ceo_answer"


def _chunk_text(text: str, *, size: int = 48) -> Iterator[str]:
    for index in range(0, len(text), size):
        yield text[index : index + size]


__all__ = ["CEOChatGateway", "format_ceo_memo", "list_ceo_chat_tools"]

