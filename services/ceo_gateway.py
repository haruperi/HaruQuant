"""Production CEO chat gateway for the global HaruQuant chat widget."""

from __future__ import annotations

from collections.abc import Iterator
import os
import time
from uuid import uuid4

import httpx

from agents.executive.ceo_agent.service import CEOAgent
from agents.executive.planner_agent.service import PlannerAgent
from agents.runtime.tool_executor import AIChatReadOnlyToolExecutor, ChatToolCall, tool_results_as_prompt
from agents._shared.schemas import AgentPlan
from config.agent_model import AGENT_MODEL
from services.context.service import ContextAssembler
from services.conversation.service import ConversationService
from services.prompt_builder import PromptBuilder
from services.schemas.chat import (
    ChatMessage,
    ChatResponseMetadata,
    ChatRouteDecision,
    ChatThreadDetail,
    ChatToolDefinition,
    ChatTurnRequest,
    ChatTurnResult,
    PageContext,
)
from services.stream_manager import (
    ModelConfigurationError,
    ModelRuntimeError,
    OpenAICompatibleStreamClient,
    StreamManager,
)
from tools.read_only import list_read_only_tool_definitions
from tools.read_only.contracts import ReadOnlyToolResult


class CEOChatGateway:
    """Runs chat through the CEO and planner while preserving production streaming."""

    def __init__(
        self,
        conversation_service: ConversationService,
        *,
        planner: PlannerAgent | None = None,
        ceo: CEOAgent | None = None,
        context_assembler: ContextAssembler | None = None,
        prompt_builder: PromptBuilder | None = None,
        stream_manager: StreamManager | None = None,
        model_client: OpenAICompatibleStreamClient | None = None,
        tool_executor: AIChatReadOnlyToolExecutor | None = None,
    ) -> None:
        self.conversations = conversation_service
        self.planner = planner or PlannerAgent()
        self.ceo = ceo or CEOAgent()
        self.context_assembler = context_assembler or ContextAssembler()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.stream_manager = stream_manager or StreamManager()
        self.model_client = model_client or OpenAICompatibleStreamClient()
        self.tool_executor = tool_executor or AIChatReadOnlyToolExecutor()

    def handle_turn(self, *, thread_id: str, user_id: str, request: ChatTurnRequest) -> ChatTurnResult:
        result: ChatTurnResult | None = None
        for event_name, data in self.stream_turn(thread_id=thread_id, user_id=user_id, request=request):
            if event_name != "done":
                continue
            thread_payload = data.get("thread")
            message_payload = data.get("assistant_message")
            user_message_payload = data.get("user_message")
            metadata_payload = data.get("metadata")
            if thread_payload and message_payload and metadata_payload:
                result = ChatTurnResult(
                    thread=ChatThreadDetail(**thread_payload),  # type: ignore[arg-type]
                    user_message=ChatMessage(**user_message_payload) if user_message_payload else None,  # type: ignore[arg-type]
                    assistant_message=ChatMessage(**message_payload),  # type: ignore[arg-type]
                    metadata=ChatResponseMetadata(**metadata_payload),  # type: ignore[arg-type]
                )
        if result is None:
            raise RuntimeError("CEO chat gateway did not complete the turn.")
        return result

    def stream_turn(self, *, thread_id: str, user_id: str, request: ChatTurnRequest) -> Iterator[tuple[str, dict[str, object]]]:
        started = time.perf_counter()
        request_id = request.request_id or f"chat-{uuid4()}"
        page_context = self.context_assembler.from_chat_request(request)
        self.conversations.update_context(
            thread_id=thread_id,
            user_id=user_id,
            current_route=page_context.route,
            current_page_type=page_context.page_type,
            active_context_revision=page_context.context_revision,
        )
        thread = self.conversations.get_thread(thread_id=thread_id, user_id=user_id)
        existing_request_ids = {message.request_id for message in thread.messages if message.request_id}
        should_persist_user_message = request_id not in existing_request_ids

        plan = self.planner.create_plan(user_request=request.prompt, request_id=request_id)
        route = _route_from_plan(plan=plan, request=request, page_context=page_context, ceo=self.ceo)
        tool_results = self.tool_executor.execute(
            _planned_read_only_tool_calls(
                planner=self.planner,
                request=request,
                plan=plan,
                page_context=page_context,
                thread_id=thread_id,
                user_id=user_id,
            )
        )
        agent_outputs = self._build_agent_outputs(plan=plan, page_context=page_context, tool_results=tool_results)
        memo = (
            self.ceo.page_identity_memo(request=request.prompt, page_context=page_context)
            if _is_page_identity_question(request.prompt)
            else self.ceo.create_final_memo(
                request=request.prompt,
                planner_result=plan,
                agent_outputs=agent_outputs,
                evidence_refs=self._evidence_refs(plan, page_context, tool_results),
            )
        )
        route.response_mode = self.ceo.response_mode_for_memo(plan=plan, memo=memo)
        route.structured_schema = route.response_mode
        prompt = self.prompt_builder.build(
            request=request,
            request_id=request_id,
            thread=thread,
            page_context=page_context,
            route=route,
            tool_evidence=tool_results_as_prompt(tool_results) if tool_results else None,
        )
        ceo_state_content = (
            "CEO/planner state for this turn. The user is talking to the CEO. "
            "Use this plan and memo as the executive routing contract.\n"
            f"planner={plan.model_dump()}\nceo_memo={memo}"
        )
        prompt.messages.insert(
            1,
            {
                "role": "system",
                "content": ceo_state_content,
            },
        )
        prompt.composition.message_count = len(prompt.messages)
        prompt.composition.token_estimate += max(1, len(ceo_state_content) // 4)
        model = self._select_model(route)
        use_model = self._should_use_model(model=model)
        metadata = self._metadata(
            request_id=request_id,
            plan=plan,
            route=route,
            memo=memo,
            page_context=page_context,
            model=model or "fallback",
            prompt_composition=prompt.composition.model_dump(),
            generation_source="llm_runtime" if use_model else "fallback",
            provider_name=self.model_client.provider_label_for_model(model or "") if use_model else None,
            attached_tools=request.attached_tools,
            tool_results=[result.model_dump() for result in tool_results],
            started=started,
        )
        if not use_model:
            metadata.audit["degraded_reason"] = (
                "CEO chat model is not configured. Set HARUQUANT_AGENT_MODEL and the matching "
                "GOOGLE_API_KEY, OPENAI_API_KEY, or local Ollama server in config/environments/.env."
            )

        user_message = (
            self.conversations.add_message(
                thread_id=thread_id,
                user_id=user_id,
                role="user",
                content=request.prompt,
                request_id=request_id,
                context_revision=page_context.context_revision,
            )
            if should_persist_user_message
            else next(message for message in reversed(thread.messages) if message.request_id == request_id and message.role == "user")
        )

        yield "meta", metadata.model_dump()

        assistant_parts: list[str] = []
        try:
            if use_model:
                retry_count = 0
                max_retries = int(os.getenv("HARUQUANT_CEO_CHAT_MAX_RETRIES", "1"))
                while True:
                    try:
                        for token in self.model_client.stream_chat(messages=prompt.messages, model=model or ""):
                            assistant_parts.append(token)
                            yield "token", {"delta": token}
                        break
                    except (httpx.HTTPError, ModelConfigurationError, ModelRuntimeError, TimeoutError):
                        if assistant_parts or retry_count >= max_retries:
                            raise
                        retry_count += 1
                        metadata.audit["retry_count"] = retry_count
                        time.sleep(min(0.5 * retry_count, 2.0))
            else:
                fallback = self._fallback_answer(request=request, page_context=page_context, route=route, memo=memo)
                for token in self.stream_manager.text_tokens(fallback):
                    assistant_parts.append(token)
                    yield "token", {"delta": token}
        except (httpx.HTTPError, ModelConfigurationError, ModelRuntimeError, TimeoutError) as exc:
            if assistant_parts:
                raise
            metadata.generation_source = "fallback"
            metadata.provider_name = None
            metadata.model = "fallback"
            metadata.audit["degraded_reason"] = str(exc)
            fallback = self._fallback_answer(request=request, page_context=page_context, route=route, memo=memo, error=exc)
            for token in self.stream_manager.text_tokens(fallback):
                assistant_parts.append(token)
                yield "token", {"delta": token}

        response_text = "".join(assistant_parts).strip()
        latency_ms = int((time.perf_counter() - started) * 1000)
        metadata.telemetry["latency_ms"] = latency_ms
        metadata.telemetry["completion_tokens"] = max(1, len(response_text) // 4) if response_text else 0
        metadata.telemetry["total_tokens"] = int(metadata.telemetry.get("prompt_tokens") or 0) + int(metadata.telemetry.get("completion_tokens") or 0)

        assistant_message = self.conversations.add_message(
            thread_id=thread_id,
            user_id=user_id,
            role="assistant",
            content=response_text or "I could not produce a CEO response for this turn.",
            request_id=request_id,
            context_revision=page_context.context_revision,
            tool_calls=metadata.tools_used,
            metadata=metadata,
            latency_ms=latency_ms,
        )
        yield "done", {
            "message_id": assistant_message.message_id,
            "assistant_message": assistant_message.model_dump(),
            "user_message": user_message.model_dump(),
            "thread": self.conversations.get_thread(thread_id=thread_id, user_id=user_id).model_dump(),
            "metadata": metadata.model_dump(),
        }

    def _build_agent_outputs(
        self,
        *,
        plan: AgentPlan,
        page_context: PageContext,
        tool_results: list[ReadOnlyToolResult],
    ) -> dict[str, object]:
        return {
            "planner": plan.model_dump(),
            "page_context": page_context.model_dump(),
            "read_only_tools": [result.model_dump() for result in tool_results],
        }

    def _evidence_refs(
        self,
        plan: AgentPlan,
        page_context: PageContext,
        tool_results: list[ReadOnlyToolResult],
    ) -> list[str]:
        refs = list(plan.evidence_requirements)
        if page_context.route:
            refs.append(f"ui:{page_context.route}")
        for result in tool_results:
            refs.extend(result.sources or [])
        return list(dict.fromkeys(refs))

    def _select_model(self, route: ChatRouteDecision) -> str | None:
        policy_key = route.model_policy_key or "fast"
        env_by_policy = {
            "fast": "HARUQUANT_AI_MODEL_FAST",
            "plain_answer": "HARUQUANT_AI_MODEL_FAST",
            "analysis": "HARUQUANT_AI_MODEL_ANALYSIS",
            "strong": "HARUQUANT_AI_MODEL_STRONG",
        }
        return os.getenv(env_by_policy.get(policy_key, "HARUQUANT_AI_MODEL_FAST")) or os.getenv("HARUQUANT_CEO_CHAT_MODEL") or AGENT_MODEL

    def _should_use_model(self, *, model: str | None) -> bool:
        disabled = os.getenv("HARUQUANT_CEO_CHAT_ENABLED", "true").lower() in {"0", "false", "no"}
        return bool(model and self.model_client.is_configured_for(model=model) and not disabled)

    def _metadata(
        self,
        *,
        request_id: str,
        plan: AgentPlan,
        route: ChatRouteDecision,
        memo: dict[str, object],
        page_context: PageContext,
        model: str,
        prompt_composition: dict[str, object],
        generation_source: str,
        provider_name: str | None,
        attached_tools: list[str],
        tool_results: list[dict[str, object]],
        started: float,
    ) -> ChatResponseMetadata:
        prompt_tokens = int(prompt_composition.get("token_estimate") or 0)
        tool_attachments = [
            {
                "tool_id": tool_id,
                "display_name": tool_id,
                "authority_band": "read_only",
                "side_effect_policy": "none",
                "capability_type": "operator_hint",
            }
            for tool_id in attached_tools
        ]
        return ChatResponseMetadata(
            request_id=request_id,
            response_mode=route.response_mode,
            response_style=route.response_style,
            task_class=route.task_class,
            domain_focus=route.domain_focus,
            answer_mode="ceo_agent_gateway",
            generation_source=generation_source,
            provider_name=provider_name,
            model=model,
            tools_used=[str(result.get("tool_name")) for result in tool_results if result.get("tool_name")],
            conversation_plan_id=plan.conversation_plan_id,
            clarification_required=plan.needs_clarification,
            active_topic=plan.intent,
            specialist_agents_used=[agent for agent in plan.allowed_agents if agent != "ceo"],
            specialist_artifacts=[
                {
                    "agent_name": "read_only_tool_executor",
                    "summary": str(result.get("summary") or result.get("tool_name")),
                    "findings": [f"status: {result.get('status')}"],
                    "sources": list(result.get("sources") or []),
                }
                for result in tool_results
            ],
            telemetry={
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": 0,
                "total_tokens": prompt_tokens,
                "cost_usd": 0.0,
            },
            cost_policy={
                "request_budget_key": f"ceo_chat_{route.model_policy_key}",
                "estimated_cost_usd": 0.0,
                "budget_downgraded": False,
                "workflow_cost_usd": 0.0,
                "within_workflow_budget": True,
            },
            attached_tools=tool_attachments,
            ceo_memo=memo,
            planner=plan.model_dump(),
            page_context=page_context.model_dump(),
            audit={
                "event": "ceo_chat_turn",
                "prompt_composition": prompt_composition,
                "context_revision_event": "context_revision_changed",
                "context_schema_version": page_context.context_schema_version,
                "context_revision": page_context.context_revision,
                "context_route": page_context.route,
                "context_page_type": page_context.page_type,
                "structured_schema": route.structured_schema,
                "stream_transport": "server_sent_events",
                "assistant_persisted_after_stream_complete": True,
                "regeneration_side_effect_policy": "read_only_no_tool_side_effects",
                "read_only_tool_calls": tool_results,
                "live_execution_enabled": False,
                "risk_governor_bypass_allowed": False,
            },
        )

    def _fallback_answer(
        self,
        *,
        request: ChatTurnRequest,
        page_context: PageContext,
        route: ChatRouteDecision,
        memo: dict[str, object],
        error: BaseException | None = None,
    ) -> str:
        title = str((page_context.summary or {}).get("headline") or page_context.page_title or "Current page")
        route_text = page_context.route or "/"
        if route.intent == "page_identity":
            return f"You are on {title} ({page_context.page_type}) at route {route_text}."
        direct_context_answer = _direct_context_answer(request.prompt, page_context)
        if direct_context_answer:
            return direct_context_answer
        memo_text = self.ceo.format_memo(memo=memo, page_context=page_context)
        if memo_text and memo_text != "CEO Agent prepared a governed firm workflow.":
            return memo_text
        degraded = " The live model is not configured or temporarily unavailable, so this is a safe CEO fallback." if error else ""
        bullets = [str(item) for item in list((page_context.summary or {}).get("bullets") or [])[:3]]
        context_line = f"Current page: {title} ({page_context.page_type}) at {route_text}."
        if bullets:
            context_line += f" Visible context: {'; '.join(bullets)}."
        return (
            f"{context_line}{degraded}\n\n"
            "I can still use current page context, planner output, CEO governance boundaries, and read-only HaruQuant tools."
        )


def list_ceo_chat_tools() -> list[ChatToolDefinition]:
    return [
        ChatToolDefinition(
            tool_id=tool.tool_id,
            display_name=tool.display_name,
            description=tool.description,
            capability_type="haruquant_read_only",
            authority_band="read_only",
            side_effect_policy="none",
            input_schema=tool.input_schema,
            output_schema=tool.output_schema,
            required_context=[],
            allowed_backend_tools=[tool.tool_id],
            allowed_specialist_agents=["read_only_tool_executor", "ceo"],
            artifact_type="state_snapshot",
            required_user_ack=False,
        )
        for tool in list_read_only_tool_definitions()
    ]

def _route_from_plan(*, plan: AgentPlan, request: ChatTurnRequest, page_context: PageContext, ceo: CEOAgent) -> ChatRouteDecision:
    if _is_page_identity_question(request.prompt):
        return ChatRouteDecision(
            intent="page_identity",
            task_class="context_lookup",
            response_mode="page_aware_summary",
            response_style="summary",
            domain_focus=page_context.page_type,
            route_mode="plain_answer",
            model_policy_key="fast",
            structured_schema="page_context_answer",
        )
    response_mode = ceo.response_mode_for_memo(plan=plan)
    model_policy_key = "strong" if plan.risk_level in {"medium", "high", "critical"} else "fast"
    if plan.intent in {"backtest_diagnosis", "optimization_comparison"}:
        model_policy_key = "analysis"
    return ChatRouteDecision(
        intent=plan.intent,
        task_class=plan.task_class,
        response_mode=response_mode,
        response_style=_response_style(plan),
        domain_focus=page_context.page_type if page_context.page_type != "generic" else (plan.domain_focus or "trading"),
        route_mode="ceo_planner",
        requires_tools=bool(plan.backend_tools_to_run or plan.attached_tools),
        model_policy_key=model_policy_key,
        structured_schema=response_mode,
    )


def _response_style(plan: AgentPlan) -> str:
    if plan.needs_clarification:
        return "clarification"
    if plan.intent in {"risk_review", "execution_proposal", "governed_action_draft"}:
        return "warning"
    if plan.intent in {"backtest_diagnosis", "optimization_comparison"}:
        return "diagnostic"
    if plan.intent == "strategy_creation":
        return "recommendation"
    return "summary"


def _planned_read_only_tool_calls(
    *,
    planner: PlannerAgent,
    request: ChatTurnRequest,
    plan: AgentPlan,
    page_context: PageContext,
    thread_id: str,
    user_id: str,
) -> list[ChatToolCall]:
    names = planner.plan_read_only_tools(user_request=request.prompt, plan=plan, attached_tools=request.attached_tools)
    common = {
        "user_id": user_id,
        "thread_id": thread_id,
        "symbol": _entity_ref(page_context, "symbol"),
        "strategy_id": _entity_ref(page_context, "strategy") or _entity_ref(page_context, "strategy_id"),
        "session_id": _session_id(page_context),
        "page_context": page_context.model_dump(),
        "reason": request.prompt[:300],
    }
    return [ChatToolCall(tool_call_id=f"tool-{name}", tool_name=name, parameters=common) for name in names]


def _direct_context_answer(prompt: str, page_context: PageContext) -> str | None:
    lowered = " ".join(prompt.lower().strip().split())
    if "account login" in lowered or "login number" in lowered:
        value = _find_page_metric(page_context, labels=("account login", "login"))
        if value is not None:
            return f"The account login shown on this page is {value}."
    if "account server" in lowered or lowered == "server":
        value = _find_page_metric(page_context, labels=("account server", "server"))
        if value is not None:
            return f"The account server shown on this page is {value}."
    if "account name" in lowered:
        value = _find_page_metric(page_context, labels=("account name", "name"))
        if value is not None:
            return f"The account name shown on this page is {value}."
    return None


def _find_page_metric(page_context: PageContext, *, labels: tuple[str, ...]) -> object | None:
    intelligence = dict((page_context.payload or {}).get("page_intelligence") or {})
    for metric in list(intelligence.get("visibleMetrics") or []):
        if not isinstance(metric, dict):
            continue
        metric_label = str(metric.get("label") or metric.get("id") or "").lower()
        if any(label in metric_label for label in labels):
            return metric.get("value")
    semantic_blocks = list(dict((page_context.payload or {}).get("dom") or {}).get("semantic_blocks") or [])
    for block in semantic_blocks:
        if not isinstance(block, dict):
            continue
        for metric in list(block.get("metrics") or []):
            if not isinstance(metric, dict):
                continue
            metric_label = str(metric.get("label") or metric.get("id") or "").lower()
            if any(label in metric_label for label in labels):
                return metric.get("value")
    return None


def _entity_ref(page_context: PageContext, ref_type: str) -> str | None:
    for ref in page_context.entity_refs:
        if ref.type == ref_type:
            return ref.id
    return None


def _session_id(page_context: PageContext) -> int | None:
    value = _entity_ref(page_context, "session") or _entity_ref(page_context, "live_session")
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _is_page_identity_question(prompt: str) -> bool:
    lowered = " ".join(prompt.lower().strip().split())
    page_terms = (
        "what page am i on",
        "which page am i on",
        "where am i",
        "what screen am i on",
        "which screen am i on",
        "what route am i on",
        "current page",
        "current screen",
    )
    return any(term in lowered for term in page_terms)


__all__ = ["CEOChatGateway", "list_ceo_chat_tools"]
