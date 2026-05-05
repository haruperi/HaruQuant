"""Structured planner for AI chat turns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend_retiring.agents.runtime import ADKRunRequest, AgentExecutionContext, LLMRuntimeError, create_llm_runtime
from backend_retiring.config.agent_model import get_model_for_tier
from backend_retiring.contracts.page_context_packet.model import PageContextPacket
from backend_retiring.agents.chat.ai_chat.domain_intelligence import resolve_domain_prompt_spec
from backend_retiring.agents.chat.ai_chat.models import ConversationState, ConversationThreadRecord
from backend_retiring.agents.chat.ai_chat.policy import ChatResponseMode


@dataclass(frozen=True)
class StructuredChatPlan:
    user_goal: str
    intent: str
    response_mode: str
    task_class: str
    model_tier: str
    response_style: str
    domain_focus: str
    answer_mode: str
    rationale: str
    needs_clarification: bool = False
    clarification_question: str | None = None
    missing_inputs: tuple[str, ...] = ()
    context_needed: tuple[str, ...] = ()
    attached_tools: tuple[str, ...] = ()
    backend_tools_to_run: tuple[str, ...] = ()
    specialist_agents_to_run: tuple[str, ...] = ()
    page_actions_to_plan: tuple[str, ...] = ()
    artifact_expected: str | None = None
    risk_level: str = "read_only"
    confidence: float = 1.0
    planner_source: str = "deterministic"


class LLMPlannerClient(Protocol):
    def refine_plan(
        self,
        *,
        prompt: str,
        deterministic_plan: StructuredChatPlan,
        page_context: PageContextPacket,
        conversation_state: ConversationState | None,
        tool_context: dict[str, object],
    ) -> dict[str, object] | None:
        ...


class RuntimeLLMPlannerClient:
    """LLM planner advisor. It proposes plans but never executes them."""

    SYSTEM_PROMPT = """You are HaruQuant's LLM planner advisor.
Return JSON only. You are not allowed to execute tools or actions.
Choose from allowlisted intents/tools/risk levels only.
Schema:
{
  "intent": "...",
  "backend_tools_to_run": [],
  "attached_tools": [],
  "specialist_agents_to_run": [],
  "page_actions_to_plan": [],
  "artifact_expected": null,
  "risk_level": "read_only",
  "confidence": 0.0,
  "rationale": "..."
}
"""

    def __init__(self, *, model: str | None = None) -> None:
        self.model = model or get_model_for_tier("fast")

    def refine_plan(
        self,
        *,
        prompt: str,
        deterministic_plan: StructuredChatPlan,
        page_context: PageContextPacket,
        conversation_state: ConversationState | None,
        tool_context: dict[str, object],
    ) -> dict[str, object] | None:
        try:
            runtime = create_llm_runtime(model=self.model, json_mode=True, temperature=0.0, max_output_tokens=800)
            request = ADKRunRequest(
                workflow_id="ai_chat_planner",
                correlation_id="ai_chat_planner",
                agent_name="llm_planner_assist",
                input_payload={
                    "_system_prompt": self.SYSTEM_PROMPT,
                    "prompt": prompt,
                    "deterministic_plan": deterministic_plan.__dict__,
                    "page_type": page_context.payload.page_type,
                    "route": page_context.payload.route,
                    "active_topic": conversation_state.active_topic if conversation_state else None,
                    "tool_context": tool_context,
                },
            )
            result = runtime.run(
                request=request,
                context=AgentExecutionContext(
                    workflow_id="ai_chat_planner",
                    correlation_id="ai_chat_planner",
                    session_id=None,
                    model=self.model,
                    allowed_tools=(),
                    prompt_version_id=None,
                    metadata={},
                ),
            )
        except (LLMRuntimeError, Exception):
            return None
        payload = result.output_payload
        if not isinstance(payload, dict) or payload.get("_parse_error"):
            return None
        return payload


class ConversationPlanner:
    """Create one explicit turn plan instead of scattered keyword routing."""

    CONFIDENCE_THRESHOLD = 0.8

    ALLOWED_INTENTS = {
        "create_strategy",
        "operate_page",
        "retrieve_knowledge",
        "diagnose_backtest",
        "compare_optimization",
        "compare_runs",
        "review_risk",
        "draft_action",
        "build_signal_proposal",
        "diagnose_performance",
        "recommend_next_step",
        "summarize_or_answer",
    }
    ALLOWED_BACKEND_TOOLS = {
        "portfolio_summary",
        "risk_snapshot",
        "open_positions",
        "latest_candle",
        "strategy_parameters",
        "backtest_summary",
        "optimization_results",
        "symbol_stats",
        "internal_knowledge",
    }
    ALLOWED_ATTACHED_TOOLS = {
        "strategy_creator",
        "strategy_refiner",
        "backtest_analyst",
        "risk_reviewer",
        "optimization_comparator",
        "signal_proposal_builder",
        "page_operator",
        "haruquant_docs",
        "full_permissions",
    }
    ALLOWED_SPECIALISTS = {
        "strategy_creator_agent",
        "backtest_explainer_agent",
        "portfolio_risk_agent",
        "optimization_comparison_agent",
        "page_operator_agent",
    }
    ALLOWED_PAGE_ACTIONS = {"registered_page_action_plan"}
    ALLOWED_ARTIFACTS = {None, "strategy_artifact", "page_action_plan", "action_draft", "signal_proposal"}
    ALLOWED_RISK_LEVELS = {"read_only", "supervised_drafts", "page_action_plan"}

    def __init__(
        self,
        *,
        llm_planner: LLMPlannerClient | None = None,
        confidence_threshold: float | None = None,
    ) -> None:
        self.llm_planner = llm_planner
        self.confidence_threshold = confidence_threshold or self.CONFIDENCE_THRESHOLD

    def plan(
        self,
        *,
        prompt: str,
        thread: ConversationThreadRecord,
        page_context: PageContextPacket,
        conversation_state: ConversationState | None,
        tool_context: dict[str, object],
    ) -> StructuredChatPlan:
        deterministic_plan = self._deterministic_plan(
            prompt=prompt,
            thread=thread,
            page_context=page_context,
            conversation_state=conversation_state,
            tool_context=tool_context,
        )
        if deterministic_plan.confidence >= self.confidence_threshold or not self._should_use_llm_assist(prompt, deterministic_plan):
            return deterministic_plan
        if self.llm_planner is None:
            return deterministic_plan
        proposal = self.llm_planner.refine_plan(
            prompt=prompt,
            deterministic_plan=deterministic_plan,
            page_context=page_context,
            conversation_state=conversation_state,
            tool_context=tool_context,
        )
        refined = self._validated_llm_plan(proposal=proposal, fallback=deterministic_plan)
        return refined or deterministic_plan

    def _deterministic_plan(
        self,
        *,
        prompt: str,
        thread: ConversationThreadRecord,
        page_context: PageContextPacket,
        conversation_state: ConversationState | None,
        tool_context: dict[str, object],
    ) -> StructuredChatPlan:
        normalized = prompt.lower()
        attached_tool_ids = tuple(
            str(value)
            for value in tool_context.get("attached_tool_ids", ())
            if isinstance(value, str)
        )
        user_goal = self._infer_user_goal(prompt=prompt, page_context=page_context)

        tool_guidance = self._missing_required_tool_guidance(normalized, attached_tool_ids)
        if tool_guidance is not None:
            return StructuredChatPlan(
                user_goal=user_goal,
                intent="summarize_or_answer",
                response_mode=ChatResponseMode.ANSWER.value,
                task_class="tool_requirement",
                model_tier="standard",
                response_style="clarification",
                domain_focus="tool_requirement",
                answer_mode="clarification",
                rationale="Planner detected a request that requires an explicitly selected chat tool.",
                needs_clarification=True,
                clarification_question=tool_guidance,
                missing_inputs=("required_chat_tool",),
                risk_level="read_only",
                confidence=0.96,
            )

        if self._confirms_pending_page_action(normalized, thread):
            return StructuredChatPlan(
                user_goal=user_goal,
                intent="operate_page",
                response_mode=ChatResponseMode.ANSWER.value,
                task_class="page_operation",
                model_tier="standard",
                response_style="recommendation",
                domain_focus="page_operation",
                answer_mode="governed_artifact",
                rationale="Planner selected Page Operator because the user confirmed a pending page action inference.",
                attached_tools=tuple(dict.fromkeys((*attached_tool_ids, "page_operator"))),
                page_actions_to_plan=("registered_page_action_plan",),
                artifact_expected="page_action_plan",
                risk_level="page_action_plan",
                confidence=0.95,
            )

        if self._is_strategy_creation(normalized, attached_tool_ids):
            spec = resolve_domain_prompt_spec("recommendation")
            return StructuredChatPlan(
                user_goal=user_goal,
                intent="create_strategy",
                response_mode=ChatResponseMode.ANSWER.value,
                task_class="strategy_creation",
                model_tier="standard",
                response_style="recommendation",
                domain_focus="strategy_creation",
                answer_mode="governed_artifact",
                rationale="Planner selected Strategy Creator because the prompt asks for a strategy artifact.",
                attached_tools=tuple(dict.fromkeys((*attached_tool_ids, "strategy_creator"))),
                backend_tools_to_run=("symbol_stats", "internal_knowledge"),
                specialist_agents_to_run=("strategy_creator_agent",),
                artifact_expected="strategy_artifact",
                risk_level="supervised_drafts" if "full_permissions" in attached_tool_ids else "read_only",
                confidence=0.94,
            )

        if self._is_page_operation(normalized, attached_tool_ids):
            return StructuredChatPlan(
                user_goal=user_goal,
                intent="operate_page",
                response_mode=ChatResponseMode.ANSWER.value,
                task_class="page_operation",
                model_tier="standard",
                response_style="recommendation",
                domain_focus="page_operation",
                answer_mode="governed_artifact",
                rationale="Planner selected Page Operator because the prompt asks to operate the UI.",
                attached_tools=tuple(dict.fromkeys((*attached_tool_ids, "page_operator"))),
                page_actions_to_plan=("registered_page_action_plan",),
                artifact_expected="page_action_plan",
                risk_level="page_action_plan",
                confidence=0.93,
            )

        if self._looks_like_knowledge_dialogue(normalized):
            spec = resolve_domain_prompt_spec("knowledge_dialogue")
            return StructuredChatPlan(
                user_goal=user_goal,
                intent="retrieve_knowledge",
                response_mode=ChatResponseMode.ANSWER.value,
                task_class="knowledge_dialogue",
                model_tier="standard",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
                answer_mode="direct_answer",
                rationale="Planner selected internal knowledge retrieval.",
                backend_tools_to_run=("internal_knowledge",),
                risk_level="read_only",
                confidence=0.9,
            )

        if "backtest_analyst" in attached_tool_ids or self._is_backtest_diagnostic(normalized, tool_context):
            spec = resolve_domain_prompt_spec("diagnostic")
            missing = () if tool_context.get("backtest_id") is not None or page_context.payload.page_type == "backtest_detail" else ("backtest_id",)
            return StructuredChatPlan(
                user_goal=user_goal,
                intent="diagnose_backtest",
                response_mode=ChatResponseMode.ANSWER.value,
                task_class="diagnostic",
                model_tier="premium",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
                answer_mode="clarification" if missing else "direct_answer",
                rationale="Planner selected Backtest Analyst diagnostic path.",
                needs_clarification=bool(missing),
                clarification_question="Which backtest should I diagnose?" if missing else None,
                missing_inputs=missing,
                context_needed=("backtest_id",),
                attached_tools=tuple(dict.fromkeys((*attached_tool_ids, "backtest_analyst"))),
                backend_tools_to_run=("backtest_summary", "strategy_parameters"),
                specialist_agents_to_run=("backtest_explainer_agent",),
                risk_level="read_only",
                confidence=0.9 if not missing else 0.82,
            )

        if "optimization_comparator" in attached_tool_ids or self._is_optimization_comparison(normalized, tool_context):
            spec = resolve_domain_prompt_spec("comparison")
            missing = (
                ()
                if (
                    tool_context.get("optimization_id") is not None
                    or page_context.payload.page_type == "optimization_detail"
                    or self._has_named_optimization_references(normalized)
                )
                else ("optimization_id",)
            )
            return StructuredChatPlan(
                user_goal=user_goal,
                intent="compare_optimization",
                response_mode=ChatResponseMode.ANSWER.value,
                task_class="comparison",
                model_tier="premium",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
                answer_mode="clarification" if missing else "direct_answer",
                rationale="Planner selected Optimization Comparator path.",
                needs_clarification=bool(missing),
                clarification_question="Which optimization run should I compare?" if missing else None,
                missing_inputs=missing,
                context_needed=("optimization_id",),
                attached_tools=tuple(dict.fromkeys((*attached_tool_ids, "optimization_comparator"))),
                backend_tools_to_run=("optimization_results", "backtest_summary"),
                specialist_agents_to_run=("optimization_comparison_agent",),
                risk_level="read_only",
                confidence=0.9 if not missing else 0.82,
            )

        if self._is_comparison(normalized, tool_context):
            spec = resolve_domain_prompt_spec("comparison")
            return StructuredChatPlan(
                user_goal=user_goal,
                intent="compare_runs",
                response_mode=ChatResponseMode.ANSWER.value,
                task_class="comparison",
                model_tier="premium",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
                answer_mode="direct_answer",
                rationale="Planner selected comparison path from resolved conversation references.",
                backend_tools_to_run=("backtest_summary", "symbol_stats"),
                specialist_agents_to_run=("optimization_comparison_agent",),
                risk_level="read_only",
                confidence=0.88,
            )

        if "risk_reviewer" in attached_tool_ids or self._is_risk_review(normalized):
            spec = resolve_domain_prompt_spec("risk_explanation")
            return StructuredChatPlan(
                user_goal=user_goal,
                intent="review_risk",
                response_mode=ChatResponseMode.ANSWER.value,
                task_class="risk_explanation",
                model_tier="premium",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
                answer_mode="direct_answer",
                rationale="Planner selected Risk Reviewer path.",
                attached_tools=tuple(dict.fromkeys((*attached_tool_ids, "risk_reviewer"))),
                backend_tools_to_run=("portfolio_summary", "risk_snapshot", "open_positions"),
                specialist_agents_to_run=("portfolio_risk_agent",),
                risk_level="read_only",
                confidence=0.9,
            )

        if self._is_action_draft(normalized):
            spec = resolve_domain_prompt_spec("action_draft")
            return StructuredChatPlan(
                user_goal=user_goal,
                intent="draft_action",
                response_mode=ChatResponseMode.ACTION_DRAFT.value,
                task_class="action_draft",
                model_tier="standard",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
                answer_mode="governed_artifact",
                rationale="Planner selected governed action draft path.",
                backend_tools_to_run=self._page_backend_tools(page_context=page_context, tool_context=tool_context),
                artifact_expected="action_draft",
                risk_level="supervised_drafts",
                confidence=0.92,
            )

        if self._is_signal_proposal(normalized):
            spec = resolve_domain_prompt_spec("signal_proposal")
            return StructuredChatPlan(
                user_goal=user_goal,
                intent="build_signal_proposal",
                response_mode=ChatResponseMode.SIGNAL_PROPOSAL.value,
                task_class="signal_proposal",
                model_tier="standard",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
                answer_mode="governed_artifact",
                rationale="Planner selected signal proposal path.",
                backend_tools_to_run=("symbol_stats",),
                artifact_expected="signal_proposal",
                risk_level="read_only",
                confidence=0.9,
            )

        if self._is_diagnostic(normalized):
            spec = resolve_domain_prompt_spec("diagnostic")
            return StructuredChatPlan(
                user_goal=user_goal,
                intent="diagnose_performance",
                response_mode=ChatResponseMode.ANSWER.value,
                task_class="diagnostic",
                model_tier="premium",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
                answer_mode="direct_answer",
                rationale="Planner selected diagnostic path from performance weakness language.",
                backend_tools_to_run=self._page_backend_tools(page_context=page_context, tool_context=tool_context),
                specialist_agents_to_run=("portfolio_risk_agent",),
                risk_level="read_only",
                confidence=0.86,
            )

        if self._is_recommendation(normalized):
            spec = resolve_domain_prompt_spec("recommendation")
            return StructuredChatPlan(
                user_goal=user_goal,
                intent="recommend_next_step",
                response_mode=ChatResponseMode.ANSWER.value,
                task_class="recommendation",
                model_tier="standard",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
                answer_mode="direct_answer",
                rationale="Planner selected recommendation path.",
                backend_tools_to_run=self._page_backend_tools(page_context=page_context, tool_context=tool_context),
                risk_level="read_only",
                confidence=0.84,
            )

        spec = resolve_domain_prompt_spec("performance_summary")
        return StructuredChatPlan(
            user_goal=user_goal,
            intent="summarize_or_answer",
            response_mode=ChatResponseMode.ANSWER.value,
            task_class="performance_summary",
            model_tier="fast",
            response_style=spec.response_style,
            domain_focus=spec.domain_focus,
            answer_mode="direct_answer",
            rationale="Planner selected default grounded answer path.",
            backend_tools_to_run=self._page_backend_tools(page_context=page_context, tool_context=tool_context),
            risk_level="read_only",
            confidence=self._default_confidence(normalized),
        )

    @classmethod
    def _should_use_llm_assist(cls, prompt: str, plan: StructuredChatPlan) -> bool:
        normalized = prompt.lower()
        if plan.risk_level != "read_only" and plan.intent not in {"create_strategy", "operate_page"}:
            return False
        ambiguity_markers = (
            "something",
            "make it better",
            "not too",
            "smoother",
            "last",
            "previous",
            "improve",
            "suggest improvements",
        )
        multi_step_markers = (" and ", " then ", "compare", "suggest", "optimize")
        return plan.confidence < cls.CONFIDENCE_THRESHOLD or any(marker in normalized for marker in (*ambiguity_markers, *multi_step_markers))

    @staticmethod
    def _default_confidence(normalized: str) -> float:
        if len(normalized.split()) <= 3:
            return 0.45
        if any(marker in normalized for marker in ("make it better", "something", "not too", "smoother", "last backtest")):
            return 0.55
        return 0.78

    def _validated_llm_plan(self, *, proposal: dict[str, object] | None, fallback: StructuredChatPlan) -> StructuredChatPlan | None:
        if not proposal:
            return None
        intent = proposal.get("intent")
        if not isinstance(intent, str) or intent not in self.ALLOWED_INTENTS:
            return None
        confidence = proposal.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            return None
        risk_level = proposal.get("risk_level")
        if not isinstance(risk_level, str) or risk_level not in self.ALLOWED_RISK_LEVELS:
            return None
        if fallback.risk_level == "read_only" and risk_level not in {"read_only", "page_action_plan", "supervised_drafts"}:
            return None
        backend_tools = self._validated_string_list(proposal.get("backend_tools_to_run"), self.ALLOWED_BACKEND_TOOLS)
        attached_tools = self._validated_string_list(proposal.get("attached_tools"), self.ALLOWED_ATTACHED_TOOLS)
        specialists = self._validated_string_list(proposal.get("specialist_agents_to_run"), self.ALLOWED_SPECIALISTS)
        page_actions = self._validated_string_list(proposal.get("page_actions_to_plan"), self.ALLOWED_PAGE_ACTIONS)
        artifact = proposal.get("artifact_expected")
        if artifact is not None and not isinstance(artifact, str):
            return None
        if artifact not in self.ALLOWED_ARTIFACTS:
            return None
        return self._plan_from_intent(
            fallback=fallback,
            intent=intent,
            backend_tools=backend_tools,
            attached_tools=attached_tools,
            specialists=specialists,
            page_actions=page_actions,
            artifact=artifact,
            risk_level=risk_level,
            confidence=float(confidence),
            rationale=str(proposal.get("rationale") or "LLM planner refined the deterministic plan."),
        )

    @staticmethod
    def _validated_string_list(value: object, allowed: set[str]) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(dict.fromkeys(item for item in value if isinstance(item, str) and item in allowed))

    def _plan_from_intent(
        self,
        *,
        fallback: StructuredChatPlan,
        intent: str,
        backend_tools: tuple[str, ...],
        attached_tools: tuple[str, ...],
        specialists: tuple[str, ...],
        page_actions: tuple[str, ...],
        artifact: str | None,
        risk_level: str,
        confidence: float,
        rationale: str,
    ) -> StructuredChatPlan:
        task_map = {
            "create_strategy": ("strategy_creation", "recommendation", "strategy_creation", "governed_artifact"),
            "operate_page": ("page_operation", "recommendation", "page_operation", "governed_artifact"),
            "retrieve_knowledge": ("knowledge_dialogue", "summary", "knowledge_dialogue", "direct_answer"),
            "diagnose_backtest": ("diagnostic", "diagnostic", "drawdown_diagnosis", "direct_answer"),
            "compare_optimization": ("comparison", "compare", "optimization_selection", "direct_answer"),
            "compare_runs": ("comparison", "compare", "optimization_selection", "direct_answer"),
            "review_risk": ("risk_explanation", "warning", "risk_review", "direct_answer"),
            "draft_action": ("action_draft", "recommendation", "action_draft", "governed_artifact"),
            "build_signal_proposal": ("signal_proposal", "recommendation", "signal_proposal", "governed_artifact"),
            "diagnose_performance": ("diagnostic", "diagnostic", "drawdown_diagnosis", "direct_answer"),
            "recommend_next_step": ("recommendation", "recommendation", "research_recommendation", "direct_answer"),
            "summarize_or_answer": ("performance_summary", "summary", "performance_summary", "direct_answer"),
        }
        task_class, response_style, domain_focus, answer_mode = task_map[intent]
        response_mode = "action_draft" if intent == "draft_action" else "signal_proposal" if intent == "build_signal_proposal" else "answer"
        return StructuredChatPlan(
            user_goal=fallback.user_goal,
            intent=intent,
            response_mode=response_mode,
            task_class=task_class,
            model_tier="premium" if intent in {"diagnose_backtest", "compare_optimization", "compare_runs", "review_risk", "diagnose_performance"} else "standard",
            response_style=response_style,
            domain_focus=domain_focus,
            answer_mode=answer_mode,
            rationale=rationale,
            needs_clarification=False,
            context_needed=fallback.context_needed,
            attached_tools=attached_tools,
            backend_tools_to_run=backend_tools,
            specialist_agents_to_run=specialists,
            page_actions_to_plan=page_actions,
            artifact_expected=artifact,
            risk_level=risk_level,
            confidence=confidence,
            planner_source="llm_assist",
        )

    @staticmethod
    def _infer_user_goal(*, prompt: str, page_context: PageContextPacket) -> str:
        prompt_text = " ".join(prompt.strip().split())
        return prompt_text or f"Understand the current {page_context.payload.page_type} state."

    @staticmethod
    def _is_strategy_creation(normalized: str, attached_tool_ids: tuple[str, ...]) -> bool:
        return "strategy_creator" in attached_tool_ids or (
            any(token in normalized for token in ("create", "build", "generate", "make", "design"))
            and "strategy" in normalized
        )

    @staticmethod
    def _is_page_operation(normalized: str, attached_tool_ids: tuple[str, ...]) -> bool:
        return "page_operator" in attached_tool_ids or any(
            phrase in normalized
            for phrase in (
                "click",
                "open tab",
                "show me",
                "go to",
                "navigate",
                "switch to",
                "change filter",
                "select ",
                "select row",
                "select the",
                "select first",
                "select backtest",
                "export this report",
                "download this",
                "change symbol",
                "switch symbol",
                "change timeframe",
                "switch timeframe",
                "trades calendar",
                "monte carlo",
                "walk forward",
            )
        )

    @staticmethod
    def _missing_required_tool_guidance(normalized: str, attached_tool_ids: tuple[str, ...]) -> str | None:
        if "page_operator" not in attached_tool_ids and ConversationPlanner._looks_like_page_operation_request(normalized):
            return (
                "This request needs the Page Operator tool selected. "
                "Attach Page Operator from the Tools menu, then resend the page action. "
                "Page Operator is required for real UI actions like navigation, clicking, selecting rows, tabs, or visible controls."
            )
        wants_strategy_artifact = ConversationPlanner._mentions_strategy_creation(normalized)
        wants_strategy_write = wants_strategy_artifact and any(
            phrase in normalized
            for phrase in (
                "save",
                "persist",
                "register",
                "materialize",
                "write file",
                "create file",
                "actual strategy",
                "from a to z",
                "implementation",
            )
        )
        if wants_strategy_write and "full_permissions" not in attached_tool_ids:
            missing = ["Full Permissions"]
            if "strategy_creator" not in attached_tool_ids:
                missing.insert(0, "Strategy Creator")
            return (
                f"This request needs the {' and '.join(missing)} tool"
                f"{'s' if len(missing) > 1 else ''} selected. "
                "Attach them from the Tools menu, then resend the request. "
                "Without Full Permissions I can only draft/review artifacts, not save files or register strategies."
            )
        if wants_strategy_artifact and "strategy_creator" not in attached_tool_ids:
            return (
                "This request needs the Strategy Creator tool selected. "
                "Attach Strategy Creator from the Tools menu, then resend the strategy idea. "
                "Add Full Permissions as well only if you want me to save/register the generated strategy."
            )
        if ConversationPlanner._mentions_signal_proposal(normalized) and "signal_proposal_builder" not in attached_tool_ids:
            return (
                "This request needs the Signal Proposal Builder tool selected. "
                "Attach Signal Proposal Builder from the Tools menu so I can produce a structured, non-executed trade setup."
            )
        if ConversationPlanner._mentions_optimization_comparison(normalized) and "optimization_comparator" not in attached_tool_ids:
            return (
                "This request needs the Optimization Comparator tool selected. "
                "Attach Optimization Comparator from the Tools menu and make sure an optimization run is selected or named."
            )
        if ConversationPlanner._mentions_risk_review(normalized) and "risk_reviewer" not in attached_tool_ids:
            return (
                "This request needs the Risk Reviewer tool selected. "
                "Attach Risk Reviewer from the Tools menu so I can focus on exposure, concentration, open risk, and session state."
            )
        if ConversationPlanner._mentions_docs(normalized) and "haruquant_docs" not in attached_tool_ids:
            return (
                "This request needs the HaruQuant Docs tool selected. "
                "Attach HaruQuant Docs from the Tools menu so I can answer from internal documentation with provenance."
            )
        return None

    @staticmethod
    def _mentions_strategy_creation(normalized: str) -> bool:
        strategy_terms = ("strategy", "strategy.py", "trading system")
        creation_terms = ("create", "build", "generate", "implement", "write")
        if any(strategy in normalized for strategy in strategy_terms) and any(term in normalized for term in creation_terms):
            return True
        return any(
            phrase in normalized
            for phrase in (
                "create strategy",
                "create a strategy",
                "build strategy",
                "build a strategy",
                "generate strategy",
                "generate a strategy",
                "strategy creator",
                "strategy artifact",
                "strategy.py",
            )
        )

    @staticmethod
    def _mentions_signal_proposal(normalized: str) -> bool:
        return any(phrase in normalized for phrase in ("signal proposal", "trade setup proposal", "setup proposal"))

    @staticmethod
    def _mentions_optimization_comparison(normalized: str) -> bool:
        return any(phrase in normalized for phrase in ("compare optimization", "optimization comparator", "rank candidates"))

    @staticmethod
    def _mentions_risk_review(normalized: str) -> bool:
        return any(phrase in normalized for phrase in ("risk review", "review risk", "risk reviewer", "portfolio risk"))

    @staticmethod
    def _mentions_docs(normalized: str) -> bool:
        return any(phrase in normalized for phrase in ("haruquant docs", "internal docs", "internal documentation"))

    @staticmethod
    def _looks_like_page_operation_request(normalized: str) -> bool:
        return any(
            phrase in normalized
            for phrase in (
                "click",
                "open tab",
                "show me",
                "go to",
                "navigate",
                "switch to",
                "change filter",
                "select ",
                "select row",
                "select the",
                "select first",
                "export this report",
                "download this",
                "change symbol",
                "switch symbol",
                "change timeframe",
                "switch timeframe",
                "trades calendar",
                "monte carlo",
                "walk forward",
            )
        )

    @staticmethod
    def _confirms_pending_page_action(normalized: str, thread: ConversationThreadRecord) -> bool:
        confirmations = {
            "yes",
            "y",
            "confirm",
            "confirmed",
            "correct",
            "that's right",
            "that is right",
            "do it",
            "proceed",
            "go ahead",
        }
        if normalized.strip() not in confirmations:
            return False
        recent_messages = list(getattr(thread, "messages", []) or [])[-4:]
        for message in reversed(recent_messages):
            if str(getattr(message, "role", "")) != "assistant":
                continue
            content = str(getattr(message, "content", "") or "").lower()
            if "do you want me to" in content and "page_action_confirmation" in content:
                return True
        return False

    @staticmethod
    def _looks_like_knowledge_dialogue(normalized: str) -> bool:
        return any(
            keyword in normalized
            for keyword in (
                "docs",
                "documentation",
                "runbook",
                "playbook",
                "policy",
                "architecture",
                "implementation plan",
                "rollout",
                "rbac",
                "knowledge base",
                "what does haruquant",
                "how does haruquant",
            )
        )

    @staticmethod
    def _is_backtest_diagnostic(normalized: str, tool_context: dict[str, object]) -> bool:
        return tool_context.get("backtest_id") is not None and any(
            keyword in normalized for keyword in ("why", "diagnose", "fail", "weak", "drawdown", "underperform")
        )

    @staticmethod
    def _is_optimization_comparison(normalized: str, tool_context: dict[str, object]) -> bool:
        return tool_context.get("optimization_id") is not None or any(
            keyword in normalized for keyword in ("compare optimization", "optimization run", "best candidate", "rank candidates")
        )

    @staticmethod
    def _has_named_optimization_references(normalized: str) -> bool:
        return "optimization" in normalized and any(
            marker in normalized
            for marker in ("run a", "run b", "versus", " vs ", "compare")
        )

    @staticmethod
    def _is_comparison(normalized: str, tool_context: dict[str, object]) -> bool:
        return any(keyword in normalized for keyword in ("compare", "versus", "vs", "better than")) and (
            tool_context.get("backtest_id") is not None
            or tool_context.get("comparison_backtest_id") is not None
            or tool_context.get("optimization_id") is not None
        )

    @staticmethod
    def _is_risk_review(normalized: str) -> bool:
        return any(keyword in normalized for keyword in ("risk", "exposure", "var", "draw risk", "danger"))

    @staticmethod
    def _is_action_draft(normalized: str) -> bool:
        return any(
            phrase in normalized
            for phrase in (
                "run backtest",
                "run a backtest",
                "run the backtest",
                "launch backtest",
                "launch a backtest",
                "launch the backtest",
                "start backtest",
                "start a backtest",
                "start the backtest",
                "run optimization",
                "run an optimization",
                "launch optimization",
                "launch an optimization",
                "export the",
                "export this",
                "draft order",
                "create order",
                "place order",
            )
        )

    @staticmethod
    def _is_diagnostic(normalized: str) -> bool:
        return any(keyword in normalized for keyword in ("diagnose", "why", "drawdown", "underperform", "flat", "stalled", "weakness", "fail"))

    @staticmethod
    def _is_signal_proposal(normalized: str) -> bool:
        return any(keyword in normalized for keyword in ("buy", "sell", "signal", "entry", "setup"))

    @staticmethod
    def _is_recommendation(normalized: str) -> bool:
        return any(keyword in normalized for keyword in ("recommend", "next step", "should i", "what next"))

    @staticmethod
    def _page_backend_tools(*, page_context: PageContextPacket, tool_context: dict[str, object]) -> tuple[str, ...]:
        page_type = page_context.payload.page_type
        tools: list[str] = []
        if page_type in {"dashboard", "portfolio_risk", "live_trading"}:
            tools.extend(["portfolio_summary", "risk_snapshot"])
        if page_type == "live_trading":
            tools.append("latest_candle")
        if page_type == "strategy_detail" or tool_context.get("strategy_id") is not None:
            tools.append("strategy_parameters")
        if page_type == "backtest_detail" or tool_context.get("backtest_id") is not None:
            tools.append("backtest_summary")
        if page_type == "optimization_detail" or tool_context.get("optimization_id") is not None:
            tools.append("optimization_results")
        if tool_context.get("symbol") is not None:
            tools.append("symbol_stats")
        return tuple(dict.fromkeys(tools))


__all__ = ["ConversationPlanner", "StructuredChatPlan"]
