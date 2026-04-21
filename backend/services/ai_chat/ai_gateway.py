"""Phase 4 AI gateway and streaming orchestration for HaruQuant chat."""

from __future__ import annotations

from dataclasses import dataclass
import re
import time
from typing import Iterable
from uuid import uuid4

from backend.agents.runtime import LLMRuntimeError, create_llm_runtime
from backend.config.agent_model import get_model_for_tier
from backend.observability.cost_tracker import calculate_cost
from backend.services.ai_chat.agent_router import ChatAgentRouter
from backend.services.ai_chat.agent_consultation_service import AgentConsultationService
from backend.services.ai_chat.conversation_orchestrator import ConversationOrchestrator
from backend.services.ai_chat.conversation_state_service import ConversationStateService
from backend.services.ai_chat.context_service import PageContextAssembler
from backend.services.ai_chat.conversation_service import ConversationService
from backend.services.ai_chat.models import ConversationPlan, SpecialistAgentArtifact
from backend.services.ai_chat.prompt_builder import ChatPromptBuilder, ContextCompactor
from backend.services.ai_chat.rate_limiter import ChatRateLimiter
from backend.services.ai_chat.policy import AuthorityBand
from backend.services.cost import CostEnforcer
from backend.services.tool_executor import ToolExecutionResult, ToolExecutor


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
        rate_limiter: ChatRateLimiter | None = None,
        compactor: ContextCompactor | None = None,
        cost_enforcer: CostEnforcer | None = None,
    ) -> None:
        self.conversation_service = conversation_service
        self.context_assembler = context_assembler
        self.prompt_builder = prompt_builder or ChatPromptBuilder()
        self.agent_router = agent_router or ChatAgentRouter()
        self.conversation_orchestrator = conversation_orchestrator or ConversationOrchestrator(
            agent_router=self.agent_router,
        )
        self.conversation_state_service = conversation_state_service or ConversationStateService()
        self.agent_consultation_service = agent_consultation_service or AgentConsultationService()
        self.tool_executor = tool_executor or ToolExecutor(db_manager=context_assembler.db_manager)
        self.rate_limiter = rate_limiter or ChatRateLimiter()
        self.compactor = compactor or ContextCompactor()
        self.cost_enforcer = cost_enforcer or CostEnforcer()

    def stream_response(self, request: ChatStreamRequest) -> tuple[dict[str, object], Iterable[str], str]:
        if not self.rate_limiter.acquire(request.user_id, wait=True, timeout=15.0):
            raise ChatRateLimitError(f"Rate limit or concurrency limit exceeded for user {request.user_id}")

        try:
            start_time = time.perf_counter()
            request_id = request.request_id or f"chatreq_{uuid4().hex}"
            thread = self.conversation_service.get_thread(user_id=request.user_id, thread_id=request.thread_id)
            page_context = self.context_assembler.assemble_context(
                route=thread.current_route or "/dashboard",
                user_id=request.user_id,
            )
            conversation_state = self.conversation_state_service.build_state(
                thread=thread,
                page_context=page_context,
                latest_prompt=request.prompt,
            )
            tool_context = self._build_tool_context(page_context=page_context, prompt=request.prompt)
            tool_context = self.conversation_state_service.enrich_tool_context(
                context=tool_context,
                prompt=request.prompt,
                state=conversation_state,
            )
            plan = self.conversation_orchestrator.build_plan(
                prompt=request.prompt,
                thread=thread,
                page_context=page_context,
                conversation_state=conversation_state,
                tool_context=tool_context,
            )
            if plan.needs_clarification:
                return self._stream_clarification_response(
                    request=request,
                    request_id=request_id,
                    page_context=page_context,
                    plan=plan,
                )
            requested_tools = self._select_tools(
                prompt=request.prompt,
                page_type=page_context.payload.page_type,
                context=tool_context,
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
                signal_proposal=signal_proposal,
                action_draft=action_draft,
                specialist_artifacts=specialist_artifacts,
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
            )
            refreshed_thread = self.conversation_service.get_thread(
                user_id=request.user_id,
                thread_id=request.thread_id,
            )
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
                "model": model,
                "generation_source": gen_result.generation_source,
                "provider_name": gen_result.provider_name,
                "context_revision": page_context.payload.context_revision,
                "tools_used": [result.tool_name for result in tool_results if result.success],
                "tools_denied": list(denied_tools),
                "active_topic": conversation_state.active_topic,
                "specialist_agents_used": [artifact.agent_name for artifact in specialist_artifacts],
                "specialist_artifacts": [artifact.model_dump(mode="json") for artifact in specialist_artifacts],
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
            if request.include_debug:
                metadata["debug"] = {
                    "router_rationale": plan.rationale,
                    "conversation_plan": plan.model_dump(mode="json"),
                    "conversation_state": conversation_state.model_dump(mode="json"),
                    "specialist_artifacts": [artifact.model_dump(mode="json") for artifact in specialist_artifacts],
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
        signal_proposal=None,
        action_draft=None,
        specialist_artifacts: list[SpecialistAgentArtifact] | None = None,
    ) -> GenerationResult:
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
            signal_proposal=signal_proposal,
            action_draft=action_draft,
            specialist_artifacts=specialist_artifacts or [],
        )
        return GenerationResult(text=fallback_text, generation_source="fallback", provider_name=None)

    def _generate_fallback_text(
        self,
        *,
        user_prompt: str,
        page_context,
        response_mode: str,
        tool_results: list[ToolExecutionResult],
        task_class: str,
        response_style: str,
        signal_proposal=None,
        action_draft=None,
        specialist_artifacts: list[SpecialistAgentArtifact],
    ) -> str:
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
        if page_context.payload.page_type == "generic" and not tool_results:
            return "\n".join(
                [
                    "I only have generic context for this page right now, so I can't summarize HaruQuant-specific metrics yet.",
                    "Open a dashboard, strategy, backtest, optimization, portfolio, or live-trading page and I can answer against that page state.",
                ]
            )
        return self._build_conversational_fallback(
            user_prompt=user_prompt,
            page_context=page_context,
            tool_results=tool_results,
            task_class=task_class,
            response_style=response_style,
            specialist_artifacts=specialist_artifacts,
        )

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
    ) -> tuple[str, ...]:
        selected: list[str] = []
        normalized = prompt.lower()
        if page_type in {"dashboard", "portfolio_risk", "live_trading"}:
            selected.extend(["portfolio_summary", "risk_snapshot"])
            if context.get("session_id") is not None or "position" in normalized:
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
        symbol = self._extract_symbol(prompt)
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
            "query": prompt.strip(),
        }

    @staticmethod
    def _extract_symbol(prompt: str) -> str | None:
        match = re.search(r"\b([A-Z]{2,6})\b", prompt)
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
            "status",
        ):
            if preferred_key in payload:
                return f"{preferred_key}={payload[preferred_key]}"
        return ", ".join(f"{key}={value}" for key, value in list(payload.items())[:3]) or "no payload"

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 48) -> Iterable[str]:
        for index in range(0, len(text), chunk_size):
            yield text[index:index + chunk_size]
