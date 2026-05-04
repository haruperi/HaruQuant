"""CEO Agent for the HaruQuant Agentic Firm."""

from __future__ import annotations

from typing import Any

from backend.agents.base import AgentRunContext, AgentRunResult, BaseAgent
from backend.agents.ceo.templates import (
    backtest_report_template,
    blocked_by_risk_template,
    board_approval_request_template,
    rejection_template,
    research_memo_template,
    risk_memo_template,
    strategy_proposal_template,
)
from backend.services.ai_chat.conversation_orchestrator import ConversationOrchestrator
from backend.services.ai_chat.models import ConversationPlan
from backend.services.ai_chat.response_composer import ResponseComposer

CEO_AGENT_DEPARTMENT = "ceo"

CEO_SYSTEM_INSTRUCTIONS = """You are the CEO Agent of the HaruQuant Agentic Firm.
You are the single operator-facing interface. You plan through the Planner Agent,
delegate to specialist departments, require evidence, respect the firm
constitution, escalate live-capital decisions to the human Board, and never
perform live execution directly."""

CEO_POLICY_REFERENCES = (
    "docs/agentic_firm/constitution.md",
    "docs/agentic_firm/risk_policy.md",
    "docs/agentic_firm/agent_permissions.md",
    "docs/agentic_firm/strategy_lifecycle.md",
)

CEO_REFUSAL_RULES = (
    "Refuse any request to bypass RiskGovernor.",
    "Refuse any request to hide, delete, or weaken audit records.",
    "Refuse any request to place live trades without Board approval.",
    "Refuse any request to skip paper-trading evidence before live activation.",
)

CEO_BOARD_ESCALATION_RULES = (
    "Live activation requires human Board approval.",
    "Allocation increases require human Board approval.",
    "Risk threshold changes require human Board approval.",
    "Critical tool use requires the approval gates from the Phase 5 permission layer.",
)


class CEOAgent(BaseAgent):
    """Firm-facing CEO Agent.

    The CEO does not replace deterministic gates. It synthesizes the control
    plane result into the appropriate memo and blocks unsafe requests.
    """

    agent_name = "ceo"
    role = "CEO Agent"
    allowed_tools = (
        "get_symbol_data",
        "get_latest_ohlcv",
        "get_strategy",
        "list_strategies",
        "get_backtest_result",
        "get_analytics_summary",
        "get_open_positions",
        "get_account_snapshot",
        "get_risk_snapshot",
        "create_report",
        "request_live_activation",
        "pause_strategy",
        "disable_live_trading",
        "trigger_kill_switch",
    )
    system_instructions = CEO_SYSTEM_INSTRUCTIONS
    policy_references = CEO_POLICY_REFERENCES
    refusal_rules = CEO_REFUSAL_RULES
    board_escalation_rules = CEO_BOARD_ESCALATION_RULES

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        user_request = str(
            task_input.get("user_request")
            or context.user_request
            or task_input.get("description")
            or ""
        )
        if self.is_unsafe_request(user_request):
            memo = self.refusal_memo(request=user_request)
            return AgentRunResult(
                agent_name=self.agent_name,
                task_id=context.task_id,
                status="completed",
                output=memo,
                decisions=(
                    {
                        "decision_type": "reject",
                        "decision": "refused",
                        "rationale": memo["reason"],
                    },
                ),
            )
        return super().run(context=context, task_input=task_input)

    def create_final_memo(
        self,
        *,
        request: str,
        planner_result: ConversationPlan,
        agent_outputs: tuple[dict[str, Any], ...] = (),
        evidence_refs: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        evidence = list(evidence_refs) or self._infer_evidence_refs(planner_result)
        if planner_result.requires_board_approval:
            return board_approval_request_template(
                request=request,
                reason="Planner marked this workflow as requiring Board approval.",
                evidence_refs=evidence,
            )
        if planner_result.requires_risk_governor and planner_result.intent == "risk_review":
            return risk_memo_template(
                request=request,
                verdict="risk_review_required",
                evidence_refs=evidence,
            )
        if planner_result.intent == "execution_proposal":
            return blocked_by_risk_template(
                request=request,
                reason="Execution proposals cannot proceed without RiskGovernor and human approval.",
                evidence_refs=evidence,
            )
        if planner_result.intent == "backtest_diagnosis":
            return backtest_report_template(
                request=request,
                summary="Backtest evidence was routed for diagnosis and CEO review.",
                evidence_refs=evidence,
            )
        if planner_result.intent == "research":
            return research_memo_template(
                request=request,
                findings=["Research workflow completed by delegated departments."],
                evidence_refs=evidence,
            )
        if planner_result.intent == "clarification":
            return {
                "memo_type": "clarification",
                "request": request,
                "question": planner_result.clarification_question,
                "evidence_refs": evidence,
            }
        if agent_outputs and any(output.get("status") == "failed" for output in agent_outputs):
            return rejection_template(
                request=request,
                reason="One or more required delegated tasks failed.",
                evidence_refs=evidence,
            )
        return strategy_proposal_template(
            request=request,
            recommendation="Continue through review, backtest, robustness, and paper-trading gates before any live consideration.",
            evidence_refs=evidence,
        )

    def refusal_memo(self, *, request: str) -> dict[str, Any]:
        return rejection_template(
            request=request,
            reason="The request conflicts with firm governance, audit, or live-trading approval policy.",
            evidence_refs=list(self.policy_references),
        )

    @staticmethod
    def is_unsafe_request(request: str) -> bool:
        normalized = request.lower()
        unsafe_markers = (
            "bypass risk",
            "skip risk",
            "disable audit",
            "delete audit",
            "hide audit",
            "place live order now",
            "go live without approval",
            "skip paper",
            "ignore board",
        )
        return any(marker in normalized for marker in unsafe_markers)

    @staticmethod
    def _infer_evidence_refs(planner_result: ConversationPlan) -> list[str]:
        refs = ["planner_result"]
        refs.extend(planner_result.evidence_requirements)
        return list(dict.fromkeys(refs))


__all__ = [
    "CEO_AGENT_DEPARTMENT",
    "CEO_BOARD_ESCALATION_RULES",
    "CEO_POLICY_REFERENCES",
    "CEO_REFUSAL_RULES",
    "CEO_SYSTEM_INSTRUCTIONS",
    "CEOAgent",
    "ConversationOrchestrator",
    "ResponseComposer",
]
