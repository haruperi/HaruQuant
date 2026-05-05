"""CEO Agent for the HaruQuant Agentic Firm."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

from backend_retiring.agents.base import AgentRunContext, AgentRunResult, BaseAgent
from backend_retiring.agents.permissions import AgentToolPermissionService
from backend_retiring.agents.ceo.templates import (
    backtest_report_template,
    blocked_by_risk_template,
    board_approval_request_template,
    ceo_answer_template,
    ceo_identity_template,
    rejection_template,
    research_memo_template,
    risk_memo_template,
    strategy_proposal_template,
)

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

    def __init__(
        self,
        *,
        permission_service: AgentToolPermissionService | None = None,
        response_synthesizer: "CEOResponseSynthesizer | None" = None,
    ) -> None:
        super().__init__(permission_service=permission_service)
        self.response_synthesizer = response_synthesizer or DefaultCEOResponseSynthesizer()

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
        planner_result: Any,
        agent_outputs: tuple[dict[str, Any], ...] = (),
        evidence_refs: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        evidence = list(evidence_refs) or self._infer_evidence_refs(planner_result)
        if planner_result.intent == "ceo_identity":
            return ceo_identity_template(
                request=request,
                evidence_refs=evidence,
            )
        if planner_result.intent == "ceo_answer":
            answer, source = self.response_synthesizer.synthesize(
                request=request,
                planner_result=planner_result,
                agent_outputs=agent_outputs,
                evidence_refs=evidence,
            )
            return ceo_answer_template(
                request=request,
                answer=answer,
                evidence_refs=evidence,
                source=source,
            )
        if planner_result.intent == "execution_proposal":
            return blocked_by_risk_template(
                request=request,
                reason=(
                    "I cannot place a live trade or use judgment to bypass firm gates. "
                    "Execution proposals require lifecycle evidence, RiskGovernor clearance, "
                    "audit, and Human Board approval before any live order path can proceed."
                ),
                evidence_refs=evidence,
            )
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
            "place a live trade",
            "place live trade",
            "execute live trade",
            "live trade",
            "go live without approval",
            "skip paper",
            "ignore board",
        )
        return any(marker in normalized for marker in unsafe_markers)

    @staticmethod
    def _infer_evidence_refs(planner_result: Any) -> list[str]:
        refs = ["planner_result"]
        refs.extend(planner_result.evidence_requirements)
        return list(dict.fromkeys(refs))


class CEOResponseSynthesizer(Protocol):
    def synthesize(
        self,
        *,
        request: str,
        planner_result: Any,
        agent_outputs: tuple[dict[str, Any], ...],
        evidence_refs: list[str],
    ) -> tuple[str, str]: ...


class DefaultCEOResponseSynthesizer:
    """Hybrid CEO communication layer.

    Governance and routing decisions stay deterministic in CEOAgent. This
    synthesizer is only allowed to phrase generic CEO answers and falls back to
    a deterministic answer if no LLM is configured or the provider fails.
    """

    SYSTEM_PROMPT = """You are the CEO/CIO-style communication layer for HaruQuant.
You may explain, summarize, and answer general operator questions.
You must not approve live trading, place trades, change risk thresholds, bypass
RiskGovernor, bypass lifecycle gates, or claim Board approval.
Return compact JSON with exactly: {"answer": "..."}."""

    def synthesize(
        self,
        *,
        request: str,
        planner_result: Any,
        agent_outputs: tuple[dict[str, Any], ...],
        evidence_refs: list[str],
    ) -> tuple[str, str]:
        if not self._llm_enabled():
            return self._fallback_answer(planner_result), "deterministic_fallback"
        try:
            from backend_retiring.agents.runtime import LLMRuntimeError, create_llm_runtime
            from backend_retiring.config.agent_model import get_model_for_tier

            runtime = create_llm_runtime(
                model=get_model_for_tier("standard"),
                json_mode=True,
                temperature=0.2,
                max_output_tokens=700,
                timeout_seconds=20,
            )
            payload = {
                "request": request,
                "intent": planner_result.intent,
                "domain_focus": planner_result.domain_focus,
                "allowed_agents": planner_result.allowed_agents,
                "evidence_refs": evidence_refs,
                "agent_outputs": agent_outputs[:4],
                "policy_boundaries": list(CEO_REFUSAL_RULES) + list(CEO_BOARD_ESCALATION_RULES),
            }
            result = runtime._call_llm(
                self.SYSTEM_PROMPT,
                json.dumps(payload, ensure_ascii=False, default=str),
            )
            parsed = json.loads(str(result.get("content") or "{}"))
            answer = str(parsed.get("answer") or "").strip()
            if answer and not self._contains_forbidden_commitment(answer):
                return answer, f"llm:{runtime.provider_name}/{runtime.model}"
        except (json.JSONDecodeError, Exception):
            return self._fallback_answer(planner_result), "deterministic_fallback"
        return self._fallback_answer(planner_result), "deterministic_fallback"

    @staticmethod
    def _llm_enabled() -> bool:
        value = os.environ.get("HARUQUANT_CEO_LLM_ENABLED", "true")
        return value.strip().lower() not in {"0", "false", "no", "off"}

    @staticmethod
    def _contains_forbidden_commitment(answer: str) -> bool:
        normalized = answer.lower()
        forbidden = (
            "i placed",
            "i will place",
            "trade is live",
            "approved for live",
            "board approved",
            "risk limit changed",
        )
        return any(marker in normalized for marker in forbidden)

    @staticmethod
    def _fallback_answer(planner_result: Any) -> str:
        return (
            "I can help with that as the HaruQuant CEO/CIO-style orchestrator. "
            "I will route firm work through the Planner Agent, consult the relevant "
            "specialist departments, summarize the evidence, and keep live-capital "
            "or risk-threshold decisions behind RiskGovernor, lifecycle evidence, "
            "audit, and Human Board approval."
        )


__all__ = [
    "CEO_AGENT_DEPARTMENT",
    "CEO_BOARD_ESCALATION_RULES",
    "CEO_POLICY_REFERENCES",
    "CEO_REFUSAL_RULES",
    "CEO_SYSTEM_INSTRUCTIONS",
    "CEOAgent",
    "CEOResponseSynthesizer",
    "DefaultCEOResponseSynthesizer",
]
