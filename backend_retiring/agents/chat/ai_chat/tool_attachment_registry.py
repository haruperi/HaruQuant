"""Chat tool attachment definitions for HaruQuant AI chat."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend_retiring.agents.chat.ai_chat.models import ChatToolAttachment


@dataclass(frozen=True)
class ChatToolDefinition:
    tool_id: str
    display_name: str
    description: str
    capability_type: str
    authority_band: str
    side_effect_policy: str
    system_prompt_fragment: str
    response_template: str | None = None
    allowed_backend_tools: tuple[str, ...] = ()
    allowed_specialist_agents: tuple[str, ...] = ()
    required_context: tuple[str, ...] = ()
    artifact_type: str | None = None
    required_user_ack: bool = False
    input_schema: dict[str, object] = field(default_factory=dict)
    output_schema: dict[str, object] = field(default_factory=dict)

    def to_attachment(self, *, missing_context: list[str] | None = None) -> ChatToolAttachment:
        return ChatToolAttachment(
            tool_id=self.tool_id,
            display_name=self.display_name,
            capability_type=self.capability_type,  # type: ignore[arg-type]
            authority_band=self.authority_band,
            side_effect_policy=self.side_effect_policy,  # type: ignore[arg-type]
            system_prompt_fragment=self.system_prompt_fragment,
            response_template=self.response_template,
            allowed_backend_tools=list(self.allowed_backend_tools),
            allowed_specialist_agents=list(self.allowed_specialist_agents),
            required_context=list(self.required_context),
            artifact_type=self.artifact_type,
            missing_context=missing_context or [],
        )


class ChatToolAttachmentRegistry:
    """Allowlisted thread/message attachment tools."""

    def __init__(self, definitions: tuple[ChatToolDefinition, ...] | None = None) -> None:
        self._definitions = {definition.tool_id: definition for definition in (definitions or DEFAULT_CHAT_TOOLS)}

    def list_definitions(self) -> list[ChatToolDefinition]:
        return list(self._definitions.values())

    def resolve(self, tool_ids: list[str] | tuple[str, ...]) -> list[ChatToolDefinition]:
        resolved: list[ChatToolDefinition] = []
        seen: set[str] = set()
        for tool_id in tool_ids:
            if tool_id in seen:
                continue
            definition = self._definitions.get(tool_id)
            if definition is not None:
                resolved.append(definition)
                seen.add(tool_id)
        return resolved


DEFAULT_CHAT_TOOLS: tuple[ChatToolDefinition, ...] = (
    ChatToolDefinition(
        tool_id="full_permissions",
        display_name="Full Permissions",
        description="Explicitly allows attached chat tools to perform implementation writes that they otherwise cannot perform.",
        capability_type="page_operation",
        authority_band="supervised_drafts",
        side_effect_policy="approval_gate",
        system_prompt_fragment=(
            "Full Permissions is attached. This only grants write authority to other attached tools that explicitly support it. "
            "It does not allow broker execution or live trades."
        ),
        response_template="permission_gate",
        required_user_ack=True,
    ),
    ChatToolDefinition(
        tool_id="strategy_creator",
        display_name="Strategy Creator",
        description="Create a HaruQuant strategy artifact with code, parameters, and validation checklist.",
        capability_type="strategy_creation",
        authority_band="supervised_drafts",
        side_effect_policy="artifact_only",
        artifact_type="strategy_blueprint",
        required_context=("symbol", "timeframe"),
        allowed_backend_tools=("symbol_stats", "internal_knowledge"),
        allowed_specialist_agents=("strategy_creator_agent",),
        system_prompt_fragment=(
            "When Strategy Creator is attached, produce a HaruQuant strategy artifact. "
            "Include hypothesis, assumptions, entry rules, exit rules, risk rules, parameters, "
            "Python strategy script, validation checklist, and overfitting warnings. "
            "Do not save or execute the strategy unless a governed draft action is requested."
        ),
        response_template="strategy_artifact",
    ),
    ChatToolDefinition(
        tool_id="strategy_refiner",
        display_name="Strategy Refiner",
        description="Review an existing strategy and propose safe, inspectable improvements.",
        capability_type="strategy_refinement",
        authority_band="read_only",
        side_effect_policy="artifact_only",
        artifact_type="strategy_refinement",
        required_context=("strategy_id",),
        allowed_backend_tools=("strategy_parameters", "internal_knowledge"),
        allowed_specialist_agents=("strategy_code_review_agent",),
        system_prompt_fragment=(
            "When Strategy Refiner is attached, inspect the current strategy and produce improvement notes, "
            "parameter adjustments, and code-diff proposals. Do not edit files unless Full Permissions is also attached."
        ),
        response_template="strategy_refinement",
    ),
    ChatToolDefinition(
        tool_id="backtest_analyst",
        display_name="Backtest Analyst",
        description="Diagnose a selected backtest using metrics, trades, equity, and drawdown evidence.",
        capability_type="backtest_analysis",
        authority_band="read_only",
        side_effect_policy="read_only",
        required_context=("backtest_id",),
        allowed_backend_tools=("backtest_summary", "strategy_parameters"),
        allowed_specialist_agents=("backtest_explainer_agent",),
        system_prompt_fragment=(
            "When Backtest Analyst is attached, lead with observed backtest metrics, then separate "
            "interpretation from facts. Identify missing metrics explicitly and recommend the next research check."
        ),
        response_template="backtest_diagnostic",
    ),
    ChatToolDefinition(
        tool_id="risk_reviewer",
        display_name="Risk Reviewer",
        description="Review current portfolio, exposure, concentration, open risk, and live-session state.",
        capability_type="risk_review",
        authority_band="read_only",
        side_effect_policy="read_only",
        allowed_backend_tools=("portfolio_summary", "risk_snapshot", "open_positions"),
        allowed_specialist_agents=("portfolio_risk_agent",),
        system_prompt_fragment=(
            "When Risk Reviewer is attached, explain current risk from exposure, concentration, open positions, "
            "floating PnL, and session state. Do not escalate warnings unless the data supports it."
        ),
        response_template="risk_review",
    ),
    ChatToolDefinition(
        tool_id="signal_proposal_builder",
        display_name="Signal Proposal Builder",
        description="Create a structured, non-executed trade setup proposal for review.",
        capability_type="signal_proposal",
        authority_band="signal_only",
        side_effect_policy="draft_action",
        artifact_type="signal_proposal",
        required_context=("symbol", "timeframe"),
        allowed_backend_tools=("symbol_stats", "latest_candle", "risk_snapshot"),
        system_prompt_fragment=(
            "When Signal Proposal Builder is attached, create a non-executed signal proposal with entry logic, "
            "exit logic, confidence, and risk note. Never claim execution and never place live trades."
        ),
        response_template="signal_proposal",
    ),
    ChatToolDefinition(
        tool_id="optimization_comparator",
        display_name="Optimization Comparator",
        description="Compare optimization candidates by score, drawdown, stability, and deployability.",
        capability_type="optimization_comparison",
        authority_band="read_only",
        side_effect_policy="read_only",
        required_context=("optimization_id",),
        allowed_backend_tools=("optimization_results", "backtest_summary"),
        allowed_specialist_agents=("optimization_comparison_agent",),
        system_prompt_fragment=(
            "When Optimization Comparator is attached, rank candidates by robustness, drawdown efficiency, "
            "stability, and practical deployability. Avoid selecting by score alone."
        ),
        response_template="optimization_comparison",
    ),
    ChatToolDefinition(
        tool_id="page_operator",
        display_name="Page Operator",
        description="Plan safe UI actions on the current page using registered action affordances.",
        capability_type="page_operation",
        authority_band="supervised_drafts",
        side_effect_policy="page_action_plan",
        required_context=("page_intelligence.actionAffordances",),
        allowed_specialist_agents=("page_operator_agent",),
        system_prompt_fragment=(
            "When Page Operator is attached, create an inspectable page action plan. "
            "Only use registered page action affordances. Do not claim that an action has been executed."
        ),
        response_template="page_action_plan",
    ),
    ChatToolDefinition(
        tool_id="haruquant_docs",
        display_name="HaruQuant Docs",
        description="Answer from internal HaruQuant documentation and include provenance.",
        capability_type="knowledge_retrieval",
        authority_band="read_only",
        side_effect_policy="read_only",
        allowed_backend_tools=("internal_knowledge",),
        allowed_specialist_agents=("knowledge_retrieval_agent",),
        system_prompt_fragment=(
            "When HaruQuant Docs is attached, answer from internal documentation and cite the retrieved source names. "
            "If docs are missing, say what was unavailable."
        ),
        response_template="doc_grounded_answer",
    ),
)


__all__ = [
    "ChatToolAttachmentRegistry",
    "ChatToolDefinition",
    "DEFAULT_CHAT_TOOLS",
]
