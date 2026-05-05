"""Phase 4 AI gateway and streaming orchestration for HaruQuant chat."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
import time
from typing import Iterable
from uuid import uuid4

from backend.agents.strategy_creator_agent import StrategyCreatorAgent, StrategyCreatorResult
from backend.agents.runtime import LLMRuntimeError, create_llm_runtime
from backend.config.agent_model import get_model_for_tier
from backend.observability.cost_tracker import calculate_cost
from backend.agents.chat.ai_chat.agent_router import ChatAgentRouter
from backend.agents.chat.ai_chat.agent_consultation_service import AgentConsultationService
from backend.agents.chat.ai_chat.ceo_chat_orchestrator import CEOChatOrchestrator
from backend.agents.chat.ai_chat.conversation_orchestrator import ConversationOrchestrator
from backend.agents.chat.ai_chat.conversation_planner import ConversationPlanner, RuntimeLLMPlannerClient
from backend.agents.chat.ai_chat.conversation_state_service import ConversationStateService
from backend.agents.chat.ai_chat.context_service import PageContextAssembler
from backend.agents.chat.ai_chat.conversation_service import ConversationService
from backend.agents.chat.ai_chat.models import ConversationPlan, SpecialistAgentArtifact
from backend.agents.chat.ai_chat.prompt_builder import ChatPromptBuilder, ContextCompactor
from backend.agents.chat.ai_chat.response_composer import ResponseComposer
from backend.agents.chat.ai_chat.rate_limiter import ChatRateLimiter
from backend.agents.chat.ai_chat.policy import AuthorityBand
from backend.agents.chat.ai_chat.page_retrieval import PageSemanticRetrievalService, RetrievedPageChunk
from backend.agents.chat.ai_chat.tool_attachment_runtime import ChatToolAttachmentRuntime
from haruquant.execution import CostEnforcer
from backend.agents.chat.ai_chat.tool_executor import ToolExecutionResult, ToolExecutor


@dataclass(frozen=True)
class GenerationResult:
    text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    generation_source: str = "fallback"
    provider_name: str | None = None


@dataclass(frozen=True)
class ChatStreamRequest:
    user_id: int
    thread_id: str
    prompt: str
    request_id: str | None = None
    include_debug: bool = False
    persist_user_message: bool = True
    context_route: str | None = None
    context_page_title: str | None = None
    context_session_id: int | None = None
    context_symbol: str | None = None
    context_timeframe: str | None = None
    context_dom: dict[str, object] | None = None
    context_page_intelligence: dict[str, object] | None = None
    attached_tools: list[str] | None = None


class ChatRateLimitError(Exception):
    """Raised when a chat request is rate-limited or exceeds concurrency."""


class AIGatewayService:
    """Own the Phase 4 chat request lifecycle and streaming response path."""

    def __init__(
        self,
        *,
        conversation_service: ConversationService,
        context_assembler: PageContextAssembler,
        prompt_builder: ChatPromptBuilder | None = None,
        agent_router: ChatAgentRouter | None = None,
        conversation_orchestrator: ConversationOrchestrator | None = None,
        conversation_state_service: ConversationStateService | None = None,
        agent_consultation_service: AgentConsultationService | None = None,
        tool_executor: ToolExecutor | None = None,
        response_composer: ResponseComposer | None = None,
        rate_limiter: ChatRateLimiter | None = None,
        compactor: ContextCompactor | None = None,
        cost_enforcer: CostEnforcer | None = None,
        page_retrieval_service: PageSemanticRetrievalService | None = None,
        tool_attachment_runtime: ChatToolAttachmentRuntime | None = None,
        strategy_creator_agent: StrategyCreatorAgent | None = None,
        ceo_chat_orchestrator: CEOChatOrchestrator | None = None,
        agentic_firm_chat_enabled: bool | None = None,
    ) -> None:
        self.conversation_service = conversation_service
        self.context_assembler = context_assembler
        self.prompt_builder = prompt_builder or ChatPromptBuilder()
        self.agent_router = agent_router or ChatAgentRouter()
        self.conversation_orchestrator = conversation_orchestrator or ConversationOrchestrator(
            agent_router=self.agent_router,
            planner=ConversationPlanner(llm_planner=RuntimeLLMPlannerClient()),
        )
        self.conversation_state_service = conversation_state_service or ConversationStateService()
        self.agent_consultation_service = agent_consultation_service or AgentConsultationService()
        self.tool_executor = tool_executor or ToolExecutor(db_manager=context_assembler.db_manager)
        self.response_composer = response_composer or ResponseComposer()
        self.rate_limiter = rate_limiter or ChatRateLimiter()
        self.compactor = compactor or ContextCompactor()
        self.cost_enforcer = cost_enforcer or CostEnforcer()
        self.page_retrieval_service = page_retrieval_service or PageSemanticRetrievalService()
        self.tool_attachment_runtime = tool_attachment_runtime or ChatToolAttachmentRuntime()
        self.strategy_creator_agent = strategy_creator_agent or StrategyCreatorAgent(
            db_manager=context_assembler.db_manager,
        )
        self.ceo_chat_orchestrator = ceo_chat_orchestrator or CEOChatOrchestrator(
            conversation_service=conversation_service,
        )
        self.agentic_firm_chat_enabled = (
            self._env_flag_enabled("HARUQUANT_AGENTIC_FIRM_CHAT", default=True)
            if agentic_firm_chat_enabled is None
            else agentic_firm_chat_enabled
        )

    def stream_response(self, request: ChatStreamRequest) -> tuple[dict[str, object], Iterable[str], str]:
        if not self.rate_limiter.acquire(request.user_id, wait=True, timeout=15.0):
            raise ChatRateLimitError(f"Rate limit or concurrency limit exceeded for user {request.user_id}")

        try:
            start_time = time.perf_counter()
            request_id = request.request_id or f"chatreq_{uuid4().hex}"
            thread = self.conversation_service.get_thread(user_id=request.user_id, thread_id=request.thread_id)
            context_route = request.context_route or thread.current_route or "/dashboard"
            page_context = self.context_assembler.assemble_context(
                route=context_route,
                user_id=request.user_id,
                page_title=request.context_page_title,
                page_state={
                    "session_id": request.context_session_id,
                    "symbol": request.context_symbol,
                    "timeframe": request.context_timeframe,
                    "dom": request.context_dom,
                    "page_intelligence": request.context_page_intelligence,
                },
            )
            if isinstance(request.context_dom, dict):
                payload = page_context.payload.payload
                if not isinstance(payload.get("dom"), dict):
                    payload["dom"] = request.context_dom
            conversation_state = self.conversation_state_service.build_state(
                thread=thread,
                page_context=page_context,
                latest_prompt=request.prompt,
            )
            page_chunks = self.page_retrieval_service.retrieve(
                dom_snapshot=page_context.payload.payload.get("dom") if isinstance(page_context.payload.payload.get("dom"), dict) else None,
                query=request.prompt,
            )
            prioritize_page_evidence = self._should_prioritize_page_evidence(
                prompt=request.prompt,
                page_chunks=page_chunks,
            )
            tool_context = self._build_tool_context(page_context=page_context, prompt=request.prompt)
            tool_context = self.conversation_state_service.enrich_tool_context(
                context=tool_context,
                prompt=request.prompt,
                state=conversation_state,
            )
            recent_messages = [
                {
                    "role": str(getattr(message, "role", "") or ""),
                    "content": str(getattr(message, "content", "") or ""),
                }
                for message in thread.messages[-8:]
            ]
            tool_context["strategy_creator_recent_messages"] = recent_messages
            tool_context["recent_messages"] = recent_messages
            requested_attached_tool_ids = tuple(dict.fromkeys(request.attached_tools or []))
            tool_context["attached_tool_ids"] = requested_attached_tool_ids
            if self.agentic_firm_chat_enabled:
                ceo_result = self.ceo_chat_orchestrator.handle_chat_turn(
                    user_id=request.user_id,
                    thread=thread,
                    prompt=request.prompt,
                    request_id=request_id,
                    page_context=page_context,
                    conversation_state=conversation_state,
                    tool_context=tool_context,
                    attached_tool_ids=requested_attached_tool_ids,
                    persist_user_message=request.persist_user_message,
                    include_debug=request.include_debug,
                )

                def ceo_chunk_generator():
                    try:
                        for chunk in self._chunk_text(ceo_result.text):
                            yield chunk
                    finally:
                        self.rate_limiter.release(request.user_id)

                return ceo_result.metadata, ceo_chunk_generator(), ceo_result.assistant_message.message_id

            plan = self.conversation_orchestrator.build_plan(
                prompt=request.prompt,
                thread=thread,
                page_context=page_context,
                conversation_state=conversation_state,
                tool_context=tool_context,
            )
            final_attached_tool_ids = tuple(dict.fromkeys((*requested_attached_tool_ids, *plan.attached_tools)))
            tool_context["attached_tool_ids"] = final_attached_tool_ids
            attached_tools = self.tool_attachment_runtime.resolve_attachments(
                selected_tool_ids=list(final_attached_tool_ids),
                page_context=page_context,
                tool_context=tool_context,
            )
            attached_tool_ids = {tool.tool_id for tool in attached_tools}
            plan.attached_tools = [tool.tool_id for tool in attached_tools]
            strategy_creator_result = None
            if "strategy_creator" in attached_tool_ids:
                strategy_creator_result = self.strategy_creator_agent.create_from_idea(
                    user_id=request.user_id,
                    idea=request.prompt,
                    context=tool_context,
                    full_permissions="full_permissions" in attached_tool_ids,
                )
            if plan.needs_clarification:
                return self._stream_clarification_response(
                    request=request,
                    request_id=request_id,
                    page_context=page_context,
                    plan=plan,
                )
            requested_tools = () if prioritize_page_evidence else tuple(plan.tools_to_run)
            requested_tools = tuple(
                dict.fromkeys(
                    [
                        *requested_tools,
                        *self.tool_attachment_runtime.collect_backend_tools(attached_tools),
                    ]
                )
            )
            tool_results, denied_tools = self.tool_executor.execute(
                user_id=request.user_id,
                requested_tools=requested_tools,
                context=tool_context,
                authority_band=AuthorityBand.READ_ONLY,
            )
            specialist_artifacts = self.agent_consultation_service.consult(
                plan=plan,
                page_context=page_context,
                conversation_state=conversation_state,
                tool_context=tool_context,
                tool_results=tool_results,
            )
            plan.agents_to_consult = [artifact.agent_name for artifact in specialist_artifacts]
            signal_proposal = None
            action_draft = None
            if plan.response_mode == "signal_proposal":
                signal_proposal = self._build_signal_proposal(
                    user_id=request.user_id,
                    thread_id=request.thread_id,
                    request_id=request_id,
                    prompt=request.prompt,
                    context=tool_context,
                    tool_results=tool_results,
                )
            elif plan.response_mode == "action_draft":
                action_draft = self._build_action_draft(
                    user_id=request.user_id,
                    thread_id=request.thread_id,
                    request_id=request_id,
                    prompt=request.prompt,
                    context=tool_context,
                    tool_results=tool_results,
                )
            built_prompt = self.prompt_builder.build(
                thread=thread,
                page_context=page_context,
                conversation_state=conversation_state,
                specialist_artifacts=specialist_artifacts,
                page_chunks=page_chunks,
                user_prompt=self._compose_grounded_user_prompt(
                    prompt=request.prompt,
                    tool_results=tool_results,
                    denied_tools=denied_tools,
                ),
                response_mode=(
                    "signal_proposal"
                    if signal_proposal is not None
                    else (
                    "action_draft"
                        if action_draft is not None
                        else ("tool_assisted" if tool_results else plan.response_mode)
                    )
                ),
                task_class=plan.task_class,
                attached_tools=attached_tools,
                attached_tool_prompt=self.tool_attachment_runtime.system_prompt_fragment(attached_tools),
            )

            if request.persist_user_message:
                self.conversation_service.add_message(
                    user_id=request.user_id,
                    thread_id=request.thread_id,
                    role="user",
                    content=request.prompt,
                    request_id=request_id,
                    context_revision=page_context.payload.context_revision,
                )

            model = get_model_for_tier(plan.model_tier)
            estimated_cost = self._estimate_request_cost(
                model=model,
                system_prompt=built_prompt.system_prompt,
                user_prompt=built_prompt.user_prompt,
                response_mode=(
                    "signal_proposal"
                    if signal_proposal is not None
                    else (
                        "action_draft"
                        if action_draft is not None
                        else ("tool_assisted" if tool_results else plan.response_mode)
                    )
                ),
            )
            request_budget_key = self._cost_budget_key_for_tier(plan.model_tier)
            budget_downgraded = False
            if not self.cost_enforcer.check_request_budget(request_budget_key, estimated_cost):
                fallback_model = self.cost_enforcer.get_fallback_model()
                fallback_estimated_cost = self._estimate_request_cost(
                    model=fallback_model,
                    system_prompt=built_prompt.system_prompt,
                    user_prompt=built_prompt.user_prompt,
                    response_mode=(
                        "signal_proposal"
                        if signal_proposal is not None
                        else (
                            "action_draft"
                            if action_draft is not None
                            else ("tool_assisted" if tool_results else plan.response_mode)
                        )
                    ),
                )
                if not self.cost_enforcer.check_request_budget(request_budget_key, fallback_estimated_cost):
                    raise ChatRateLimitError("Estimated request cost exceeds configured budget.")
                model = fallback_model
                estimated_cost = fallback_estimated_cost
                budget_downgraded = True
            gen_result = self._generate_text(
                system_prompt=built_prompt.system_prompt,
                user_prompt=built_prompt.user_prompt,
                model=model,
                page_context=page_context,
                response_mode=(
                    "signal_proposal"
                    if signal_proposal is not None
                    else (
                        "action_draft"
                        if action_draft is not None
                        else ("tool_assisted" if tool_results else plan.response_mode)
                    )
                ),
                tool_results=tool_results,
                task_class=plan.task_class,
                response_style=plan.response_style,
                page_chunks=page_chunks,
                prioritize_page_evidence=prioritize_page_evidence,
                signal_proposal=signal_proposal,
                action_draft=action_draft,
                specialist_artifacts=specialist_artifacts,
                strategy_creator_result=strategy_creator_result,
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            cost = self._calculate_cost(
                model=model,
                prompt_tokens=gen_result.prompt_tokens,
                completion_tokens=gen_result.completion_tokens,
            )
            if gen_result.prompt_tokens is not None or gen_result.completion_tokens is not None:
                self.cost_enforcer.record_cost(
                    trace_id=request.thread_id,
                    span_id=request_id,
                    model=model,
                    input_tokens=gen_result.prompt_tokens or 0,
                    output_tokens=gen_result.completion_tokens or 0,
                )
            cumulative_workflow_cost = self.cost_enforcer.get_current_cost(request.thread_id)
            within_workflow_budget = self.cost_enforcer.check_workflow_budget(cumulative_workflow_cost)

            metadata = {
                "request_id": request_id,
                "thread_id": request.thread_id,
                "response_mode": (
                    "signal_proposal"
                    if signal_proposal is not None
                    else (
                        "action_draft"
                        if action_draft is not None
                        else ("tool_assisted" if tool_results else plan.response_mode)
                    )
                ),
                "task_class": plan.task_class,
                "response_style": plan.response_style,
                "domain_focus": plan.domain_focus,
                "answer_mode": plan.answer_mode,
                "conversation_plan_id": plan.conversation_plan_id,
                "clarification_required": plan.needs_clarification,
                "planner": {
                    "source": plan.planner_source,
                    "confidence": plan.planner_confidence,
                    "intent": plan.intent,
                    "risk_level": plan.risk_level,
                    "artifact_expected": plan.artifact_expected,
                    "backend_tools_to_run": plan.backend_tools_to_run,
                    "attached_tools": plan.attached_tools,
                    "page_actions_to_plan": plan.page_actions_to_plan,
                },
                "model": model,
                "generation_source": gen_result.generation_source,
                "provider_name": gen_result.provider_name,
                "context_revision": page_context.payload.context_revision,
                "tools_used": [result.tool_name for result in tool_results if result.success],
                "tools_denied": list(denied_tools),
                "page_evidence_prioritized": prioritize_page_evidence,
                "active_topic": conversation_state.active_topic,
                "specialist_agents_used": [artifact.agent_name for artifact in specialist_artifacts],
                "specialist_artifacts": [artifact.model_dump(mode="json") for artifact in specialist_artifacts],
                "attached_tools": [tool.model_dump(mode="json") for tool in attached_tools],
                "telemetry": {
                    "latency_ms": latency_ms,
                    "prompt_tokens": gen_result.prompt_tokens,
                    "completion_tokens": gen_result.completion_tokens,
                    "total_tokens": gen_result.total_tokens,
                    "cost_usd": cost,
                },
                "cost_policy": {
                    "request_budget_key": request_budget_key,
                    "estimated_cost_usd": estimated_cost,
                    "budget_downgraded": budget_downgraded,
                    "workflow_cost_usd": cumulative_workflow_cost,
                    "within_workflow_budget": within_workflow_budget,
                },
            }
            if signal_proposal is not None:
                metadata["signal_proposal"] = signal_proposal.model_dump(mode="json")
                metadata["signal_proposal_id"] = signal_proposal.proposal_id
            if action_draft is not None:
                metadata["action_draft"] = action_draft.model_dump(mode="json")
                metadata["action_draft_id"] = action_draft.draft_id
            if strategy_creator_result is not None:
                metadata["strategy_creator"] = strategy_creator_result.to_metadata()
                if strategy_creator_result.needs_clarification:
                    metadata["clarification_required"] = True
                    metadata["response_style"] = "clarification"
                if strategy_creator_result.needs_confirmation:
                    metadata["clarification_required"] = True
                    metadata["response_style"] = "clarification"
                if strategy_creator_result.materialized and strategy_creator_result.strategy is not None:
                    metadata["strategy_id"] = strategy_creator_result.strategy.get("id")

            # Extract strategy_artifact from specialist agents (new LLM path)
            for artifact in specialist_artifacts:
                if artifact.agent_name == "strategy_creator_agent" and artifact.strategy_artifact:
                    if "strategy_creator" not in metadata:
                        metadata["strategy_creator"] = {}
                    metadata["strategy_creator"]["artifact"] = artifact.strategy_artifact
                    metadata["strategy_creator"]["blueprint"] = artifact.strategy_artifact.get("blueprint") # For consistency

            self.conversation_service.add_message(
                user_id=request.user_id,
                thread_id=request.thread_id,
                role="assistant",
                content=gen_result.text,
                request_id=request_id,
                context_revision=page_context.payload.context_revision,
                tool_calls=[result.tool_name for result in tool_results if result.success],
                signal_proposal_id=signal_proposal.proposal_id if signal_proposal is not None else None,
                action_draft_id=action_draft.draft_id if action_draft is not None else None,
                prompt_tokens=gen_result.prompt_tokens,
                completion_tokens=gen_result.completion_tokens,
                total_tokens=gen_result.total_tokens,
                cost=cost,
                latency_ms=latency_ms,
                metadata=metadata,
            )
            refreshed_thread = self.conversation_service.get_thread(
                user_id=request.user_id,
                thread_id=request.thread_id,
            )
            if request.include_debug:
                metadata["debug"] = {
                    "router_rationale": plan.rationale,
                    "conversation_plan": plan.model_dump(mode="json"),
                    "conversation_state": conversation_state.model_dump(mode="json"),
                    "specialist_artifacts": [artifact.model_dump(mode="json") for artifact in specialist_artifacts],
                    "page_chunks": [chunk.__dict__ for chunk in page_chunks],
                    "prompt": built_prompt.debug,
                }

            # Wrap chunks to release slot on completion
            def chunk_generator():
                try:
                    for chunk in self._chunk_text(gen_result.text):
                        yield chunk
                finally:
                    self.rate_limiter.release(request.user_id)

            return metadata, chunk_generator(), refreshed_thread.messages[-1].message_id
        except Exception:
            self.rate_limiter.release(request.user_id)
            raise

    @staticmethod
    def _calculate_cost(*, model: str, prompt_tokens: int | None, completion_tokens: int | None) -> float | None:
        if prompt_tokens is None or completion_tokens is None:
            return None
        normalized_model = model.split("/", 1)[-1]
        return round(calculate_cost(normalized_model, prompt_tokens, completion_tokens), 6)

    @staticmethod
    def _env_flag_enabled(name: str, *, default: bool = False) -> bool:
        value = os.environ.get(name)
        if value is None:
            return default
        normalized = value.strip().lower()
        if normalized in {"0", "false", "no", "off"}:
            return False
        if normalized in {"1", "true", "yes", "on"}:
            return True
        return default

    def _stream_clarification_response(
        self,
        *,
        request: ChatStreamRequest,
        request_id: str,
        page_context,
        plan: ConversationPlan,
    ) -> tuple[dict[str, object], Iterable[str], str]:
        text = plan.clarification_question or "What do you want me to focus on?"

        if request.persist_user_message:
            self.conversation_service.add_message(
                user_id=request.user_id,
                thread_id=request.thread_id,
                role="user",
                content=request.prompt,
                request_id=request_id,
                context_revision=page_context.payload.context_revision,
            )

        assistant_message = self.conversation_service.add_message(
            user_id=request.user_id,
            thread_id=request.thread_id,
            role="assistant",
            content=text,
            request_id=request_id,
            context_revision=page_context.payload.context_revision,
            tool_calls=[],
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            cost=None,
            latency_ms=0,
        )
        metadata = {
            "request_id": request_id,
            "thread_id": request.thread_id,
            "response_mode": "answer",
            "task_class": plan.task_class,
            "response_style": "clarification",
            "domain_focus": plan.domain_focus,
            "answer_mode": plan.answer_mode,
            "conversation_plan_id": plan.conversation_plan_id,
            "clarification_required": True,
            "model": None,
            "generation_source": "clarification_policy",
            "provider_name": None,
            "context_revision": page_context.payload.context_revision,
            "tools_used": [],
            "tools_denied": [],
            "specialist_agents_used": [],
            "specialist_artifacts": [],
            "telemetry": {
                "latency_ms": 0,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "cost_usd": None,
            },
            "cost_policy": {
                "request_budget_key": None,
                "estimated_cost_usd": 0.0,
                "budget_downgraded": False,
                "workflow_cost_usd": self.cost_enforcer.get_current_cost(request.thread_id),
                "within_workflow_budget": self.cost_enforcer.check_workflow_budget(
                    self.cost_enforcer.get_current_cost(request.thread_id)
                ),
            },
        }
        if request.include_debug:
            metadata["debug"] = {"conversation_plan": plan.model_dump(mode="json")}

        def chunk_generator():
            try:
                for chunk in self._chunk_text(text):
                    yield chunk
            finally:
                self.rate_limiter.release(request.user_id)

        return metadata, chunk_generator(), assistant_message.message_id

    @classmethod
    def _estimate_request_cost(
        cls,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_mode: str,
    ) -> float:
        estimated_prompt_tokens = max(1, (len(system_prompt) + len(user_prompt)) // 4)
        estimated_completion_tokens = {
            "action_draft": 700,
            "signal_proposal": 650,
            "tool_assisted": 550,
        }.get(response_mode, 450)
        estimated = cls._calculate_cost(
            model=model,
            prompt_tokens=estimated_prompt_tokens,
            completion_tokens=estimated_completion_tokens,
        )
        return float(estimated or 0.0)

    @staticmethod
    def _cost_budget_key_for_tier(model_tier: str) -> str:
        return {
            "fast": "simple_classification",
            "standard": "structured_extraction",
            "premium": "complex_planning",
        }.get(model_tier, "complex_planning")

    def _generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        page_context,
        response_mode: str,
        tool_results: list[ToolExecutionResult],
        task_class: str,
        response_style: str,
        page_chunks: list[RetrievedPageChunk],
        prioritize_page_evidence: bool,
        signal_proposal=None,
        action_draft=None,
        specialist_artifacts: list[SpecialistAgentArtifact] | None = None,
        strategy_creator_result: StrategyCreatorResult | None = None,
    ) -> GenerationResult:
        if strategy_creator_result is not None:
            return GenerationResult(
                text=self._build_strategy_creator_response(strategy_creator_result),
                generation_source="strategy_creator_agent",
                provider_name=None,
            )
        try:
            runtime = create_llm_runtime(
                model=model,
                temperature=0.2,
                max_output_tokens=2048,
                json_mode=False,
            )
            result = runtime._call_llm(system_prompt, user_prompt)
            text = str(result.get("content") or "").strip()
            if text:
                text = self._polish_runtime_text(
                    text=text,
                    response_mode=response_mode,
                    task_class=task_class,
                )
                return GenerationResult(
                    text=text,
                    prompt_tokens=result.get("prompt_tokens"),
                    completion_tokens=result.get("completion_tokens"),
                    total_tokens=result.get("total_tokens"),
                    generation_source="llm_runtime",
                    provider_name=runtime.provider_name,
                )
        except LLMRuntimeError:
            pass
        except Exception:
            pass
        fallback_text = self._generate_fallback_text(
            user_prompt=user_prompt,
            page_context=page_context,
            response_mode=response_mode,
            tool_results=tool_results,
            task_class=task_class,
            response_style=response_style,
            page_chunks=page_chunks,
            prioritize_page_evidence=prioritize_page_evidence,
            signal_proposal=signal_proposal,
            action_draft=action_draft,
            specialist_artifacts=specialist_artifacts or [],
            strategy_creator_result=strategy_creator_result,
        )
        return GenerationResult(text=fallback_text, generation_source="fallback", provider_name=None)

    @staticmethod
    def _polish_runtime_text(*, text: str, response_mode: str, task_class: str) -> str:
        if response_mode in {"signal_proposal", "action_draft"} or task_class in {"signal_proposal", "action_draft"}:
            return text.strip()

        lines = [line.rstrip() for line in text.splitlines()]
        filtered_lines: list[str] = []
        skip_prefixes = (
            "mode:",
            "style:",
            "task:",
            "task class:",
            "request id:",
            "user request received:",
            "context revision:",
            "response mode:",
            "answer mode:",
            "generation source:",
        )

        for line in lines:
            normalized = line.strip().lower()
            if normalized.startswith(skip_prefixes):
                continue
            if re.match(
                r"^\s{0,3}#{1,6}\s*(summary|metrics|implications|observed state|likely drivers|next checks|comparison|tradeoffs|recommendation|risk state|primary exposures|operator warning|assessment|evidence needed)\s*:?\s*$",
                normalized,
            ):
                continue
            if normalized in {
                "summary:",
                "metrics:",
                "implications:",
                "observed state:",
                "likely drivers:",
                "next checks:",
                "comparison:",
                "tradeoffs:",
                "recommendation:",
                "risk state:",
                "primary exposures:",
                "operator warning:",
                "assessment:",
                "evidence needed:",
            }:
                continue
            filtered_lines.append(line)

        cleaned = "\n".join(filtered_lines).strip()
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        if cleaned.lower().startswith("summary\n"):
            cleaned = cleaned[8:].lstrip()
        elif cleaned.lower().startswith("summary:"):
            cleaned = cleaned[8:].lstrip()

        return cleaned or text.strip()

    def _generate_fallback_text(
        self,
        *,
        user_prompt: str,
        page_context,
        response_mode: str,
        tool_results: list[ToolExecutionResult],
        task_class: str,
        response_style: str,
        page_chunks: list[RetrievedPageChunk],
        prioritize_page_evidence: bool,
        signal_proposal=None,
        action_draft=None,
        specialist_artifacts: list[SpecialistAgentArtifact],
        strategy_creator_result: StrategyCreatorResult | None = None,
    ) -> str:
        if strategy_creator_result is not None:
            return self._build_strategy_creator_response(strategy_creator_result)
        if signal_proposal is not None:
            return "\n".join(
                [
                    f"{signal_proposal.title}",
                    "Signal Thesis:",
                    f"- Hypothesis: {signal_proposal.hypothesis}",
                    f"- Symbol: {signal_proposal.symbol} {signal_proposal.direction} {signal_proposal.timeframe}",
                    "Signal Structure:",
                    f"- Entry logic: {signal_proposal.entry_logic}",
                    f"- Exit logic: {signal_proposal.exit_logic}",
                    f"- Confidence: {signal_proposal.confidence}",
                    "Risk Controls:",
                    f"- Risk note: {signal_proposal.risk_note}",
                    f"- Rationale: {signal_proposal.rationale}",
                    f"- Status: {signal_proposal.status}",
                    f"- Label: {signal_proposal.non_executed_label}",
                ]
            )
        if action_draft is not None:
            payload_lines = [
                f"- {key}: {value}"
                for key, value in list(action_draft.payload.items())[:6]
            ]
            return "\n".join(
                [
                    f"{action_draft.title}",
                    "Action Draft:",
                    f"- Type: {action_draft.draft_type}",
                    f"- Description: {action_draft.description}",
                    *(payload_lines or ["- Payload: no structured payload"]),
                    "Approval Requirements:",
                    f"- Requires human approval: {action_draft.requires_human_approval}",
                    f"- Status: {action_draft.status}",
                    f"- Approval ID: {action_draft.approval_id or 'not_requested'}",
                    "Risk Precheck:",
                    f"- Risk status: {action_draft.risk_precheck_status}",
                    f"- Risk notes: {action_draft.risk_precheck_notes}",
                    f"- Side effect status: {action_draft.side_effect_status}",
                    "- Execution: not executed from chat",
                ]
            )
        if prioritize_page_evidence and page_chunks:
            return self._build_page_chunk_fallback(prompt=user_prompt, page_chunks=page_chunks)
        if page_context.payload.page_type == "generic" and not tool_results:
            dom_snapshot = page_context.payload.payload.get("dom")
            if page_chunks:
                return self._build_page_chunk_fallback(prompt=user_prompt, page_chunks=page_chunks)
            if isinstance(dom_snapshot, dict) and self._has_visible_table(dom_snapshot):
                return self._build_dom_page_summary(prompt=user_prompt, dom_snapshot=dom_snapshot)
            return "\n".join(
                [
                    "I only have generic context for this page right now, so I can't summarize HaruQuant-specific metrics yet.",
                    "Open a dashboard, strategy, backtest, optimization, portfolio, or live-trading page and I can answer against that page state.",
                ]
            )
        latest_candle_result = next(
            (result for result in tool_results if result.tool_name == "latest_candle" and result.success),
            None,
        )
        normalized_prompt = user_prompt.lower()
        if latest_candle_result is not None and any(
            phrase in normalized_prompt
            for phrase in ("last candle", "latest candle", "current candle", "bullish", "bearish", "ohlc", "candlestick", "chart")
        ):
            return self._build_latest_candle_fallback(prompt=user_prompt, payload=latest_candle_result.payload)
        return self._build_conversational_fallback(
            user_prompt=user_prompt,
            page_context=page_context,
            tool_results=tool_results,
            task_class=task_class,
            response_style=response_style,
            specialist_artifacts=specialist_artifacts,
        )

    @staticmethod
    def _build_strategy_creator_response(result: StrategyCreatorResult) -> str:
        if result.needs_clarification:
            lines = [
                "I cannot generate the strategy yet because key design inputs are missing.",
                "",
                "Missing inputs:",
                *[f"- {item}" for item in result.missing_inputs],
                "",
                result.clarification_question or "Please provide the missing inputs.",
            ]
            return "\n".join(lines)

        if result.needs_confirmation:
            interpretation = result.final_interpretation or {}
            lines = [
                "CONFIRMATION:",
                "",
                "Final interpretation:",
                f"- Strategy type: {interpretation.get('strategy_type')}",
                f"- Assets: {', '.join(interpretation.get('assets') or [])}",
                f"- Timeframe: {interpretation.get('timeframe')}",
                "",
                "Entry logic:",
                *[f"- {rule}" for rule in interpretation.get("entry_logic") or []],
                "",
                "Exit logic:",
                *[f"- {rule}" for rule in interpretation.get("exit_logic") or []],
                "",
                "Risk management:",
                f"- {interpretation.get('risk_management')}",
                "",
                "Position sizing:",
                f"- {interpretation.get('position_sizing')}",
                "",
                "Confirm or modify before I generate the strategy.",
            ]
            return "\n".join(lines)

        if result.blueprint is None:
            return result.permission_note or "Strategy Creator could not produce an artifact."

        payload = result.blueprint.payload
        artifact = result.artifact or {}
        lines = [
            f"Strategy Creator produced `{payload.strategy_name}`.",
            "",
            "Artifact:",
            f"- Type: {payload.strategy_type}",
            f"- Assets: {', '.join(payload.asset_scope.assets)}",
            f"- Timeframe: {payload.asset_scope.timeframe}",
            f"- Backtest readiness: {payload.backtest_readiness}",
            f"- Code validation: {'passed' if result.code_valid else 'failed'}",
            f"- Persistence: {'registered in strategy catalog' if result.materialized else 'not saved'}",
        ]
        if result.strategy:
            lines.extend(
                [
                    f"- Strategy ID: {result.strategy.get('id')}",
                    f"- Active version: {result.strategy.get('active_version')}",
                    f"- Strategy file: {result.strategy.get('active_file_path')}",
                ]
            )
        if result.validation_issues:
            lines.append(f"- Validation issues: {', '.join(result.validation_issues)}")
        indicator_dependencies = artifact.get("indicator_dependencies", [])
        indicator_artifacts = artifact.get("indicator_artifacts", [])
        lines.extend(
            [
                "",
                "Entry rules:",
                *[f"- {rule}" for rule in payload.entry_logic],
                "",
                "Exit rules:",
                *[f"- {rule}" for rule in payload.exit_logic],
                "",
                "Parameters:",
                *[
                    f"- {param.get('name')}: default={param.get('default')}, range={param.get('range')}"
                    for param in artifact.get("parameters", [])
                ],
                "",
                "Required data fields:",
                f"- {', '.join(artifact.get('required_data_fields', []))}",
                "",
                "Indicator dependencies:",
                *([
                    f"- {item.get('name')} ({'available' if item.get('available') else 'missing'}): {item.get('target_path')}"
                    for item in indicator_dependencies
                ] if indicator_dependencies else ["- None detected"]),
                "",
                "Created indicators:",
                *([
                    f"- {item.get('normalized_name')}: {item.get('file_path')}"
                    for item in indicator_artifacts
                    if item.get("materialized")
                ] if indicator_artifacts else ["- None"]),
                "",
                "Backtest suggestion:",
                f"- Symbol: {artifact.get('backtest_configuration_suggestion', {}).get('symbol')}",
                f"- Timeframe: {artifact.get('backtest_configuration_suggestion', {}).get('timeframe')}",
                "",
                "Known failure modes:",
                *[f"- {mode}" for mode in artifact.get("known_failure_modes", [])],
                "",
                artifact.get("robustness_warning", ""),
                "",
                result.permission_note,
            ]
        )
        return "\n".join(lines)

    def _build_conversational_fallback(
        self,
        *,
        user_prompt: str,
        page_context,
        tool_results: list[ToolExecutionResult],
        task_class: str,
        response_style: str,
        specialist_artifacts: list[SpecialistAgentArtifact],
    ) -> str:
        if task_class == "knowledge_dialogue" or any(
            result.tool_name == "internal_knowledge" and result.success
            for result in tool_results
        ):
            return self.response_composer.compose_knowledge_dialogue(
                user_prompt=user_prompt,
                page_context=page_context,
                tool_results=tool_results,
                specialist_artifacts=specialist_artifacts,
            )
        default_text = self._build_default_conversational_fallback(
            user_prompt=user_prompt,
            page_context=page_context,
            tool_results=tool_results,
            task_class=task_class,
            response_style=response_style,
        )
        return self.agent_consultation_service.compose_final_response(
            user_prompt=user_prompt,
            task_class=task_class,
            page_context=page_context,
            tool_results=tool_results,
            specialist_artifacts=specialist_artifacts,
            default_text=default_text,
        )

    def _build_default_conversational_fallback(
        self,
        *,
        user_prompt: str,
        page_context,
        tool_results: list[ToolExecutionResult],
        task_class: str,
        response_style: str,
    ) -> str:
        lead = page_context.payload.summary.headline.rstrip(".")
        bullet_text = " ".join(page_context.payload.summary.bullets[:2]).strip()
        facts = [
            f"{result.tool_name} reports {self._summarize_tool_payload(result.payload)}"
            for result in tool_results
            if result.success
        ]
        fact_sentence = " ".join(facts[:2]).strip()
        inference_line = self._build_inference_line(
            task_class=task_class,
            tool_results=tool_results,
            page_context=page_context,
        )
        recommendation_line = self._build_recommendation_line(
            task_class=task_class,
            tool_results=tool_results,
        )

        if task_class == "diagnostic":
            return " ".join(
                part for part in (
                    f"{lead}.",
                    fact_sentence and f"From the current HaruQuant state, {fact_sentence}.",
                    f"My best read is that {inference_line.lower()}",
                    recommendation_line,
                )
                if part
            )
        if task_class == "comparison":
            return " ".join(
                part for part in (
                    f"{lead}.",
                    fact_sentence and f"I can ground the comparison on the current data: {fact_sentence}.",
                    f"{inference_line}",
                    recommendation_line,
                )
                if part
            )
        if task_class == "risk_explanation":
            return " ".join(
                part for part in (
                    f"{lead}.",
                    fact_sentence and f"The strongest current risk evidence is {fact_sentence}.",
                    f"{inference_line}",
                    recommendation_line,
                )
                if part
            )
        if task_class == "recommendation":
            return " ".join(
                part for part in (
                    f"{lead}.",
                    bullet_text and f"The current page context suggests {bullet_text}.",
                    f"{inference_line}",
                    recommendation_line,
                )
                if part
            )
        if "what does this page do" in user_prompt.lower():
            page_name = page_context.payload.page_type.replace("_", " ")
            return " ".join(
                part for part in (
                    f"This page is the HaruQuant {page_name} view.",
                    f"{lead}.",
                    bullet_text,
                )
                if part
            )
        return " ".join(
            part for part in (
                f"{lead}.",
                fact_sentence and f"I'm grounding this on {fact_sentence}.",
                bullet_text,
                recommendation_line if response_style != "clarification" else None,
            )
            if part
        )

    @staticmethod
    def _build_page_chunk_fallback(*, prompt: str, page_chunks: list[RetrievedPageChunk]) -> str:
        lead = "I can read structured content from the current page."
        normalized = prompt.lower()
        top_chunks = page_chunks[:3]
        for chunk in top_chunks:
            direct_answer = AIGatewayService._answer_from_page_chunk(prompt=normalized, chunk=chunk)
            if direct_answer:
                return direct_answer
        if any(term in normalized for term in ("summary", "summarise", "summarize", "current page", "results")):
            lines = [lead, "Most relevant visible page evidence:"]
            for chunk in top_chunks:
                lines.append(f"- {chunk.title}: {chunk.content}")
            return "\n".join(lines)
        best = top_chunks[0]
        return f"{lead} The strongest matching page evidence is from {best.title}: {best.content}"

    @staticmethod
    def _answer_from_page_chunk(*, prompt: str, chunk: RetrievedPageChunk) -> str | None:
        metadata = chunk.metadata if isinstance(chunk.metadata, dict) else {}
        series_metadata = metadata.get("series") if isinstance(metadata.get("series"), dict) else {}
        row_map = metadata.get("row_map") if isinstance(metadata.get("row_map"), dict) else {}

        if any(term in prompt for term in ("date", "when")) and series_metadata:
            selected = AIGatewayService._select_series_for_prompt(prompt=prompt, series_metadata=series_metadata, title=chunk.title)
            if selected:
                label, values = selected
                if "drawdown" in prompt and isinstance(values.get("min_x"), str):
                    return (
                        f"On {chunk.title}, the most severe {label} point appears at {values.get('min_x')} "
                        f"with a value of {values.get('min_numeric')}."
                    )
                if any(term in prompt for term in ("max", "highest", "peak")) and isinstance(values.get("max_x"), str):
                    return (
                        f"On {chunk.title}, the peak {label} point appears at {values.get('max_x')} "
                        f"with a value of {values.get('max_numeric')}."
                    )
                if any(term in prompt for term in ("min", "lowest", "worst")) and isinstance(values.get("min_x"), str):
                    return (
                        f"On {chunk.title}, the lowest {label} point appears at {values.get('min_x')} "
                        f"with a value of {values.get('min_numeric')}."
                    )
                if isinstance(values.get("latest_x"), str):
                    return (
                        f"On {chunk.title}, the latest {label} point is at {values.get('latest_x')} "
                        f"with a value of {values.get('latest_numeric', values.get('latest_y'))}."
                    )

        if any(term in prompt for term in ("compare", "previous")) and series_metadata:
            selected = AIGatewayService._select_series_for_prompt(prompt=prompt, series_metadata=series_metadata, title=chunk.title)
            if selected:
                label, values = selected
                latest_x = values.get("latest_x")
                previous_x = values.get("previous_x")
                latest_numeric = values.get("latest_numeric")
                previous_numeric = values.get("previous_numeric")
                delta_numeric = values.get("delta_numeric")
                if (
                    isinstance(latest_x, str)
                    and isinstance(previous_x, str)
                    and isinstance(latest_numeric, (int, float))
                    and isinstance(previous_numeric, (int, float))
                    and isinstance(delta_numeric, (int, float))
                ):
                    direction = "up" if delta_numeric > 0 else "down" if delta_numeric < 0 else "flat"
                    return (
                        f"On {chunk.title}, {label} is {direction} versus the previous point: "
                        f"{previous_x}={previous_numeric}, {latest_x}={latest_numeric}, change={delta_numeric}."
                    )

        if any(term in prompt for term in ("net profit", "total return", "cagr", "profit factor", "win rate", "expectancy", "drawdown", "sharpe", "sortino", "calmar")) and row_map:
            for row_label, values in row_map.items():
                if row_label in prompt:
                    visible_values = " | ".join(str(value) for value in values[:4] if str(value).strip())
                    if visible_values:
                        return f"On {chunk.title}, {row_label.title()} is shown as {visible_values}."

        return None

    @staticmethod
    def _select_series_for_prompt(*, prompt: str, series_metadata: dict[str, object], title: str) -> tuple[str, dict[str, object]] | None:
        if not series_metadata:
            return None
        prompt_terms = set(re.findall(r"[a-z0-9%]+", prompt.lower()))
        best_label = None
        best_score = -1
        best_values: dict[str, object] | None = None
        for label, values in series_metadata.items():
            if not isinstance(values, dict):
                continue
            score = 0
            label_terms = set(re.findall(r"[a-z0-9%]+", str(label).lower()))
            score += len(prompt_terms & label_terms) * 5
            if label in prompt.lower():
                score += 6
            if "drawdown" in prompt.lower() and "drawdown" in f"{title} {label}".lower():
                score += 8
            if "equity" in prompt.lower() and "equity" in f"{title} {label}".lower():
                score += 8
            if score > best_score:
                best_score = score
                best_label = str(label)
                best_values = values
        if best_label is None or best_values is None:
            first_label = next(iter(series_metadata.items()))
            label, values = first_label
            if isinstance(values, dict):
                return str(label), values
            return None
        return best_label, best_values

    @staticmethod
    def _build_latest_candle_fallback(*, prompt: str, payload: dict[str, object]) -> str:
        symbol = str(payload.get("symbol") or "the selected symbol")
        timeframe = str(payload.get("timeframe") or "the selected timeframe")
        if not payload.get("candle_available"):
            reason = str(payload.get("reason") or "market data was unavailable")
            return f"I can't inspect the latest {symbol} {timeframe} candle right now because {reason}."

        last_candle = payload.get("last_candle") if isinstance(payload.get("last_candle"), dict) else {}
        direction = str(payload.get("last_candle_direction") or "neutral")
        timestamp = str(last_candle.get("time") or payload.get("last_candle_time") or "unknown time")
        open_price = last_candle.get("open")
        close_price = last_candle.get("close")
        high_price = last_candle.get("high")
        low_price = last_candle.get("low")

        if any(word in prompt.lower() for word in ("bullish", "bearish")):
            return (
                f"The latest completed {symbol} {timeframe} candle is {direction}. "
                f"It opened at {open_price}, closed at {close_price}, ranged from {low_price} to {high_price}, "
                f"and closed at {timestamp}."
            )
        return (
            f"The latest completed {symbol} {timeframe} candle closed {direction}. "
            f"Open {open_price}, high {high_price}, low {low_price}, close {close_price}, time {timestamp}."
        )

    @staticmethod
    def _has_visible_table(dom_snapshot: dict[str, object]) -> bool:
        tables = dom_snapshot.get("tables")
        return isinstance(tables, list) and any(isinstance(table, dict) for table in tables)

    @staticmethod
    def _build_dom_page_summary(*, prompt: str, dom_snapshot: dict[str, object]) -> str:
        title = str(dom_snapshot.get("title") or "this page").strip()
        headings = dom_snapshot.get("headings") if isinstance(dom_snapshot.get("headings"), list) else []
        tables = dom_snapshot.get("tables") if isinstance(dom_snapshot.get("tables"), list) else []
        excerpt = str(dom_snapshot.get("text_excerpt") or "").strip()
        first_table = tables[0] if tables and isinstance(tables[0], dict) else {}
        headers = first_table.get("headers") if isinstance(first_table.get("headers"), list) else []
        rows = first_table.get("rows") if isinstance(first_table.get("rows"), list) else []

        lead = f"The current page is {title}"
        if headings:
            heading_text = ", ".join(str(item) for item in headings[:3])
            lead = f"The current page is {title}, focused on {heading_text}"

        metric_lines: list[str] = []
        for row in rows[:8]:
            if not isinstance(row, list) or len(row) < 2:
                continue
            label = str(row[0]).strip()
            values = [str(value).strip() for value in row[1:4] if str(value).strip()]
            if label and values:
                metric_lines.append(f"{label}: {' | '.join(values)}")

        if metric_lines:
            summary_lines = [f"{lead}.", "Visible results on the page include:"]
            summary_lines.extend(f"- {line}" for line in metric_lines[:6])
            if any(word in prompt.lower() for word in ("summary", "summarise", "summarize", "results", "current page")):
                return "\n".join(summary_lines)

        if headers and rows:
            first_row = rows[0] if isinstance(rows[0], list) else []
            return (
                f"{lead}. The visible table uses columns {', '.join(str(item) for item in headers[:4])}. "
                f"The first visible row is {', '.join(str(item) for item in first_row[:4])}."
            )

        if excerpt:
            return f"{lead}. Visible page content indicates: {excerpt[:280]}"
        return f"{lead}."

    def _build_inference_line(self, *, task_class: str, tool_results: list[ToolExecutionResult], page_context) -> str:
        summary_text = "; ".join(
            self._summarize_tool_payload(result.payload)
            for result in tool_results
            if result.success
        )
        if task_class == "diagnostic":
            return f"the issue is most likely tied to drawdown, PnL, or exposure drivers based on {summary_text or page_context.payload.summary.headline}"
        if task_class == "comparison":
            return f"the comparison should be anchored on score, Sharpe, drawdown, or exposure metrics, using {summary_text or page_context.payload.summary.headline} as the evidence base"
        if task_class == "risk_explanation":
            return f"current risk is best explained by live exposure concentration and floating PnL, with {summary_text or page_context.payload.summary.headline} carrying the main signal"
        if task_class == "recommendation":
            return f"the next research step should follow from the strongest and weakest observed metrics, especially {summary_text or page_context.payload.summary.headline}"
        if task_class == "knowledge_dialogue":
            return f"the answer should be anchored on the retrieved internal documents, while keeping {page_context.payload.page_type} page context separate from document guidance"
        return f"the current performance summary should come from the latest HaruQuant metrics, especially {summary_text or page_context.payload.summary.headline}"

    @staticmethod
    def _build_recommendation_line(*, task_class: str, tool_results: list[ToolExecutionResult]) -> str:
        if task_class == "diagnostic":
            return "Check the latest backtest, strategy parameters, and live-risk state before changing the hypothesis."
        if task_class == "comparison":
            return "Rank the alternatives by return quality and drawdown efficiency before promoting a candidate."
        if task_class == "risk_explanation":
            return "Review concentration by symbol and session exposure before considering any supervised action."
        if task_class == "recommendation":
            return "Run the next research step as a backtest, optimization, or risk review rather than a live action."
        if task_class == "knowledge_dialogue":
            return "Name the relevant document and keep any page metrics grounded in live HaruQuant state."
        if any(result.tool_name == "optimization_results" for result in tool_results):
            return "Review the top optimization candidates against robustness and drawdown, not score alone."
        return "Use current system metrics as the baseline for any further research decision."

    def _build_signal_proposal(
        self,
        *,
        user_id: int,
        thread_id: str,
        request_id: str,
        prompt: str,
        context: dict[str, object],
        tool_results: list[ToolExecutionResult],
    ):
        symbol = str(context.get("symbol") or "SPY")
        timeframe = "1D"
        direction = "long" if any(keyword in prompt.lower() for keyword in ("buy", "long")) else "short" if any(keyword in prompt.lower() for keyword in ("sell", "short")) else "neutral"
        tool_summary = "; ".join(
            f"{result.tool_name}: {self._summarize_tool_payload(result.payload)}"
            for result in tool_results
            if result.success
        ) or "No supporting tool metrics were available."
        confidence = 72 if tool_results else 58
        return self.conversation_service.create_signal_proposal(
            user_id=user_id,
            thread_id=thread_id,
            request_id=request_id,
            title=f"{symbol} signal proposal",
            hypothesis=prompt.strip(),
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            entry_logic="Enter only after the stated setup condition is confirmed on the current timeframe.",
            exit_logic="Exit on invalidation of the setup, opposing signal confirmation, or predefined review threshold.",
            confidence=confidence,
            rationale=f"Generated from the user prompt and current HaruQuant page context. Supporting evidence: {tool_summary}",
            risk_note="Non-executed AI signal proposal. Requires watchlist or review-queue handling before any supervised action.",
        )

    def _build_action_draft(
        self,
        *,
        user_id: int,
        thread_id: str,
        request_id: str,
        prompt: str,
        context: dict[str, object],
        tool_results: list[ToolExecutionResult],
    ):
        normalized = prompt.lower()
        draft_type = self._infer_action_draft_type(normalized)
        tool_summary = "; ".join(
            f"{result.tool_name}: {self._summarize_tool_payload(result.payload)}"
            for result in tool_results
            if result.success
        ) or "No supporting tool metrics were available."
        direction = "buy" if any(keyword in normalized for keyword in ("buy", "long")) else "sell" if any(keyword in normalized for keyword in ("sell", "short")) else "buy"
        risk_status = "passed"
        risk_notes = "Draft remains non-executed and must be approved before any downstream action."
        if draft_type == "order_draft" and context.get("symbol") is None:
            risk_status = "blocked"
            risk_notes = "Order drafts require an explicit symbol before paper execution can be considered."
        payload = {
            "prompt": prompt.strip(),
            "route": context.get("route"),
            "page_type": context.get("page_type"),
            "strategy_id": context.get("strategy_id"),
            "backtest_id": context.get("backtest_id"),
            "optimization_id": context.get("optimization_id"),
            "session_id": context.get("session_id"),
            "symbol": context.get("symbol"),
            "direction": direction,
            "size": {"units": 1000},
            "entry_price": None,
            "stop_loss_logic": {"type": "fixed_percent", "value": 0.01},
            "take_profit_logic": {"type": "fixed_percent", "value": 0.02},
            "tool_summary": tool_summary,
        }
        return self.conversation_service.create_action_draft(
            user_id=user_id,
            thread_id=thread_id,
            request_id=request_id,
            draft_type=draft_type,
            title=self._make_action_draft_title(draft_type=draft_type, context=context),
            description=self._make_action_draft_description(draft_type=draft_type, prompt=prompt),
            payload=payload,
            risk_precheck_status=risk_status,
            risk_precheck_notes=risk_notes,
            requires_human_approval=True,
            side_effect_status="not_executed",
        )

    @staticmethod
    def _infer_action_draft_type(normalized_prompt: str) -> str:
        if "backtest" in normalized_prompt:
            return "backtest_launch"
        if "optimization" in normalized_prompt or "optimisation" in normalized_prompt or "optimize" in normalized_prompt:
            return "optimization_launch"
        if "export" in normalized_prompt:
            return "export_request"
        if "simulate" in normalized_prompt or "simulation" in normalized_prompt:
            return "simulation_request"
        return "order_draft"

    @staticmethod
    def _make_action_draft_title(*, draft_type: str, context: dict[str, object]) -> str:
        suffix = ""
        if context.get("strategy_id"):
            suffix = f" for {context['strategy_id']}"
        elif context.get("symbol"):
            suffix = f" for {context['symbol']}"
        titles = {
            "backtest_launch": "Backtest launch draft",
            "optimization_launch": "Optimization launch draft",
            "export_request": "Export request draft",
            "simulation_request": "Simulation request draft",
            "order_draft": "Order draft",
        }
        return f"{titles.get(draft_type, 'Action draft')}{suffix}"

    @staticmethod
    def _make_action_draft_description(*, draft_type: str, prompt: str) -> str:
        prefixes = {
            "backtest_launch": "Prepared a supervised backtest request",
            "optimization_launch": "Prepared a supervised optimization request",
            "export_request": "Prepared a supervised export request",
            "simulation_request": "Prepared a supervised simulation request",
            "order_draft": "Prepared a supervised order draft request",
        }
        return f"{prefixes.get(draft_type, 'Prepared a supervised action draft')} from prompt: {prompt.strip()}"

    def _select_tools(
        self,
        *,
        prompt: str,
        page_type: str,
        context: dict[str, object],
        prioritize_page_evidence: bool = False,
    ) -> tuple[str, ...]:
        selected: list[str] = []
        normalized = prompt.lower()
        chart_keywords = (
            "last candle",
            "latest candle",
            "current candle",
            "bullish",
            "bearish",
            "ohlc",
            "candlestick",
            "chart",
        )
        live_summary_keywords = (
            "summarize this page",
            "summarise this page",
            "summary current page",
            "summaries current page",
            "current page",
            "this page",
        )
        is_chart_question = any(word in normalized for word in chart_keywords)
        is_live_page_summary = page_type == "live_trading" and any(word in normalized for word in live_summary_keywords)
        if page_type in {"dashboard", "portfolio_risk"} and not prioritize_page_evidence:
            selected.extend(["portfolio_summary", "risk_snapshot"])
            if context.get("session_id") is not None or "position" in normalized:
                selected.append("open_positions")
            if any(word in normalized for word in ("alert", "warning", "error", "incident", "log")):
                selected.append("alert_history")
        elif page_type == "live_trading":
            if is_chart_question or is_live_page_summary:
                selected.append("latest_candle")
            if not is_chart_question and not prioritize_page_evidence:
                selected.extend(["portfolio_summary", "risk_snapshot"])
            if (context.get("session_id") is not None or "position" in normalized) and not prioritize_page_evidence:
                selected.append("open_positions")
            if any(word in normalized for word in ("alert", "warning", "error", "incident", "log")):
                selected.append("alert_history")
        if page_type == "strategy_detail" or context.get("strategy_id") is not None:
            selected.append("strategy_parameters")
        if page_type == "backtest_detail" or context.get("backtest_id") is not None:
            selected.append("backtest_summary")
        if page_type == "optimization_detail" or context.get("optimization_id") is not None:
            selected.append("optimization_results")
        if context.get("symbol") is not None or any(word in normalized for word in ("symbol", "dataset", "timeframe")):
            selected.append("symbol_stats")
        if any(
            phrase in normalized
            for phrase in (
                "doc",
                "docs",
                "documentation",
                "architecture",
                "runbook",
                "policy",
                "rbac",
                "implementation plan",
                "rollout",
                "support sop",
                "knowledge base",
                "internal knowledge",
                "what does haruquant",
                "how does haruquant",
            )
        ):
            selected.append("internal_knowledge")
        return tuple(dict.fromkeys(selected))

    def _build_tool_context(self, *, page_context, prompt: str) -> dict[str, object]:
        payload = page_context.payload.payload
        route = page_context.payload.route
        session_id = payload.get("session_id")
        strategy_id = payload.get("strategy_id")
        backtest_id = payload.get("backtest_id")
        optimization_id = payload.get("optimization_id")
        symbol = payload.get("symbol")
        timeframe = payload.get("timeframe")
        if not isinstance(symbol, str) or not symbol.strip():
            symbol = self._extract_symbol(prompt)
        if not isinstance(timeframe, str) or not timeframe.strip():
            timeframe = self._extract_timeframe(prompt)
        if symbol is None:
            for entity in page_context.payload.entity_refs:
                if entity.type.lower() in {"symbol", "asset"}:
                    symbol = entity.label or entity.id
                    break
        return {
            "route": route,
            "page_type": page_context.payload.page_type,
            "session_id": session_id,
            "strategy_id": strategy_id,
            "backtest_id": backtest_id,
            "optimization_id": optimization_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "query": prompt.strip(),
        }

    @staticmethod
    def _should_prioritize_page_evidence(*, prompt: str, page_chunks: list[RetrievedPageChunk]) -> bool:
        if not page_chunks:
            return False
        normalized = prompt.lower()
        explicit_page_phrases = (
            "this page",
            "current page",
            "these results",
            "visible",
            "shown here",
            "on this chart",
            "on this table",
        )
        page_metric_phrases = (
            "what date",
            "when was",
            "previous point",
            "compare current",
            "latest point",
            "max drawdown",
            "net profit",
            "total return",
            "cagr",
            "profit factor",
            "win rate",
            "expectancy",
            "sharpe",
            "sortino",
            "calmar",
            "last candle",
            "latest candle",
            "bullish",
            "bearish",
        )
        return any(phrase in normalized for phrase in (*explicit_page_phrases, *page_metric_phrases))

    @staticmethod
    def _extract_symbol(prompt: str) -> str | None:
        match = re.search(r"\b([A-Z]{2,6})\b", prompt)
        return match.group(1) if match else None

    @staticmethod
    def _extract_timeframe(prompt: str) -> str | None:
        match = re.search(r"\b(M1|M5|M15|M30|H1|H4|D1|W1|MN1)\b", prompt.upper())
        return match.group(1) if match else None

    def _compose_grounded_user_prompt(
        self,
        *,
        prompt: str,
        tool_results: list[ToolExecutionResult],
        denied_tools: tuple[str, ...],
    ) -> str:
        lines = [prompt.strip()]
        if tool_results:
            lines.append("Tool grounding:")
            for result in tool_results:
                status = "ok" if result.success else f"error={result.error}"
                # Use compactor for payload truncation
                truncated_payload = self.compactor.truncate_json(str(result.payload), 1500)
                lines.append(f"- {result.tool_name} ({status}): {truncated_payload}")
        if denied_tools:
            lines.append(f"Denied tools: {', '.join(denied_tools)}")
        return "\n".join(lines)

    @staticmethod
    def _summarize_tool_payload(payload: dict[str, object]) -> str:
        headline_metrics = payload.get("headline_metrics")
        if isinstance(headline_metrics, dict) and headline_metrics:
            return ", ".join(f"{key}={value}" for key, value in list(headline_metrics.items())[:5])
        for preferred_key in (
            "aggregate_open_profit",
            "open_position_count",
            "best_score",
            "active_version",
            "alert_count",
            "dataset_count",
            "last_candle_direction",
            "status",
        ):
            if preferred_key in payload:
                return f"{preferred_key}={payload[preferred_key]}"
        return ", ".join(f"{key}={value}" for key, value in list(payload.items())[:3]) or "no payload"

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 48) -> Iterable[str]:
        for index in range(0, len(text), chunk_size):
            yield text[index:index + chunk_size]
