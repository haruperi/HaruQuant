"""CEO Agent for the HaruQuant agentic trading firm."""

from __future__ import annotations

import os
from typing import Any

from agents.executive.ceo_agent.contracts import CEOResponseSynthesizer
from agents.executive.ceo_agent.prompts import (
    CEO_POLICY_REFERENCES,
    CEO_SYSTEM_INSTRUCTIONS,
    backtest_report_template,
    blocked_by_risk_template,
    rejection_template,
    research_memo_template,
    risk_memo_template,
    strategy_proposal_template,
)
from agents.executive.ceo_agent.deterministic_policy import make_executive_decision
from agents.executive.ceo_agent.shared.audit import build_executive_audit
from agents.executive.ceo_agent.shared.escalation_rules import build_board_escalation_packet, board_escalation_reasons
from agents.executive.ceo_agent.shared.executive_contracts import CEOResponse
from agents.executive.ceo_agent.shared.memo_builder import synthesize_evidence_summary
from agents.executive.ceo_agent.shared.response_templates import governed_action_draft_template, portfolio_memo_template
from agents._shared.schemas import AgentPlan


class CEOAgent:
    agent_name = "ceo"

    def __init__(self, *, response_synthesizer: CEOResponseSynthesizer | None = None) -> None:
        self.response_synthesizer = response_synthesizer

    def create_final_memo(
        self,
        *,
        request: str,
        planner_result: AgentPlan,
        agent_outputs: dict[str, Any] | None = None,
        evidence_refs: list[str] | None = None,
    ) -> dict[str, Any]:
        agent_outputs = agent_outputs or {}
        evidence_refs = evidence_refs or self._collect_evidence_refs(agent_outputs)

        if self.is_unsafe_request(request):
            return self.refusal_memo(request=request)

        if planner_result.intent == "ceo_identity":
            return self.identity_memo()

        if planner_result.requires_board_approval or planner_result.requires_risk_governor:
            if planner_result.intent == "execution_proposal":
                return self._blocked_execution_memo(request=request, evidence_refs=evidence_refs)

        if planner_result.intent == "ceo_answer":
            return self.answer_memo(
                request=request,
                planner_result=planner_result,
                agent_outputs=agent_outputs,
                evidence_refs=evidence_refs,
            )

        if planner_result.intent == "strategy_creation":
            return strategy_proposal_template(request=request, evidence_refs=evidence_refs)
        if planner_result.intent == "backtest_diagnosis":
            return backtest_report_template(request=request, evidence_refs=evidence_refs)
        if planner_result.intent == "portfolio":
            return portfolio_memo_template(request=request, evidence_refs=evidence_refs)
        if planner_result.intent == "governed_action_draft":
            return governed_action_draft_template(request=request, evidence_refs=evidence_refs)
        if planner_result.intent in {"risk_review", "execution_proposal"}:
            return risk_memo_template(request=request, evidence_refs=evidence_refs)
        if planner_result.intent in {"research", "optimization_comparison", "reporting", "page_action", "clarification"}:
            return research_memo_template(
                request=request,
                planner_intent=planner_result.intent,
                evidence_refs=evidence_refs,
            )

        return {
            "memo_type": "ceo_memo",
            "request": request,
            "decision": "completed",
            "summary": "CEO Agent completed delegated firm workflow with deterministic governance boundaries intact.",
            "evidence_refs": evidence_refs,
        }

    def create_executive_response(
        self,
        *,
        request_id: str,
        request: str,
        planner_result: AgentPlan,
        agent_outputs: dict[str, Any] | None = None,
        evidence_refs: list[str] | None = None,
        tools_used: list[str] | None = None,
    ) -> CEOResponse:
        agent_outputs = agent_outputs or {}
        evidence_refs = evidence_refs or self._collect_evidence_refs(agent_outputs)
        decision = make_executive_decision(
            request=request,
            planner_result=planner_result,
            evidence_refs=evidence_refs,
            tools_used=tools_used or [],
            specialist_responses=agent_outputs,
        )
        memo = self.create_final_memo(
            request=request,
            planner_result=planner_result,
            agent_outputs=agent_outputs,
            evidence_refs=evidence_refs,
        )
        escalation_reasons = board_escalation_reasons(request, risk_level=planner_result.risk_level)
        board_escalation = (
            build_board_escalation_packet(request=request, reasons=escalation_reasons or decision.reasons, evidence_refs=evidence_refs)
            if decision.requires_board_approval
            else None
        )
        evidence_summary = synthesize_evidence_summary(specialist_responses=agent_outputs, evidence_refs=evidence_refs)
        planner_dump = planner_result.model_dump() if hasattr(planner_result, "model_dump") else dict(planner_result)
        audit = build_executive_audit(
            request_id=request_id,
            planner_output=planner_dump,
            departments_called=_departments_from_agents(planner_result.allowed_agents),
            agents_called=planner_result.allowed_agents,
            evidence_refs=evidence_refs,
            missing_evidence=decision.missing_evidence,
            decision=decision.decision,
            allowed_actions=decision.allowed_actions,
            blocked_actions=decision.blocked_actions,
        )
        return CEOResponse(
            request_id=request_id,
            status=decision.status,
            planner_output=planner_dump,
            specialist_responses=agent_outputs,
            evidence_summary=evidence_summary,
            final_memo=memo,
            decision=decision,
            allowed_actions=decision.allowed_actions,
            blocked_actions=decision.blocked_actions,
            required_next_steps=_next_steps_for_decision(decision),
            board_escalation=board_escalation,
            audit=audit,
        )

    def identity_memo(self) -> dict[str, Any]:
        return {
            "memo_type": "ceo_identity",
            "name": "HaruQuant AI",
            "summary": "I am the CEO/CIO-style orchestrator for HaruQuant AI, not an execution engine.",
            "responsibilities": [
                "delegate work to specialist departments",
                "require evidence before recommendations",
                "synthesize final investment memos",
                "escalate live capital, risk-threshold, and deployment decisions to the Human Board",
            ],
            "boundaries": [
                "I do not place live trades directly",
                "I do not bypass the RiskGovernor",
                "I do not alter audit records",
                "I do not approve my own live deployment",
            ],
            "policy_references": list(CEO_POLICY_REFERENCES),
        }

    def answer_memo(
        self,
        *,
        request: str,
        planner_result: AgentPlan,
        agent_outputs: dict[str, Any],
        evidence_refs: list[str],
    ) -> dict[str, Any]:
        if self.response_synthesizer is not None and os.getenv("HARUQUANT_CEO_LLM_ENABLED", "false").lower() != "false":
            answer, source = self.response_synthesizer.synthesize(
                request=request,
                planner_result=planner_result,
                agent_outputs=agent_outputs,
                evidence_refs=evidence_refs,
            )
        elif self.response_synthesizer is not None:
            answer, source = self.response_synthesizer.synthesize(
                request=request,
                planner_result=planner_result,
                agent_outputs=agent_outputs,
                evidence_refs=evidence_refs,
            )
        else:
            answer, source = (
                "Focus first on evidence quality, risk constraints, and the next governed workflow step before considering deployment.",
                "deterministic:fallback",
            )
        return {
            "memo_type": "ceo_answer",
            "request": request,
            "answer": answer,
            "source": source,
            "policy_references": list(CEO_POLICY_REFERENCES),
            "evidence_refs": evidence_refs,
        }

    def page_identity_memo(self, *, request: str, page_context: Any) -> dict[str, Any]:
        title = str((page_context.summary or {}).get("headline") or page_context.page_title or "Current page")
        route = page_context.route or "/"
        bullets = [str(value) for value in list((page_context.summary or {}).get("bullets") or [])[:3]]
        details = f"You are on {title} ({page_context.page_type}) at route {route}."
        if bullets:
            details += f" Visible context: {'; '.join(bullets)}."
        return {
            "memo_type": "page_identity",
            "request": request,
            "answer": details,
            "source": "page_context",
            "context_revision": page_context.context_revision,
            "context_schema_version": page_context.context_schema_version,
        }

    def response_mode_for_memo(self, *, plan: AgentPlan, memo: dict[str, Any] | None = None) -> str:
        memo_type = str((memo or {}).get("memo_type", ""))
        if memo_type == "page_identity":
            return "page_aware_summary"
        if memo_type in {"rejection", "blocked_by_risk"}:
            return "blocked_by_policy"
        if plan.requires_board_approval:
            return "approval_request"
        if plan.intent == "strategy_creation":
            return "strategy_spec_draft"
        if plan.intent == "risk_review":
            return "risk_memo"
        if plan.intent in {"research", "optimization_comparison", "reporting"}:
            return "research_memo"
        return plan.response_mode or "direct_ceo_answer"

    def format_memo(self, *, memo: dict[str, Any], plan: AgentPlan | None = None, page_context: Any = None) -> str:
        if "answer" in memo:
            return str(memo["answer"])
        if "reason" in memo:
            return str(memo["reason"])
        return str(memo.get("summary") or "CEO Agent prepared a governed firm workflow.")

    def refusal_memo(self, *, request: str) -> dict[str, Any]:
        return rejection_template(
            request=request,
            reason="The request conflicts with HaruQuant governance, live-trading controls, audit integrity, or Board approval rules.",
        )

    def is_unsafe_request(self, request: str) -> bool:
        lowered = request.lower()
        unsafe_terms = (
            "ignore board",
            "without approval",
            "bypass risk",
            "bypass riskgovernor",
            "delete audit",
            "disable audit",
            "hide audit",
            "change risk threshold",
            "skip paper",
        )
        live_action = ("place live order" in lowered or "go live" in lowered) and (
            "ignore" in lowered or "without" in lowered or "delete audit" in lowered
        )
        return live_action or any(term in lowered for term in unsafe_terms)

    def _blocked_execution_memo(self, *, request: str, evidence_refs: list[str]) -> dict[str, Any]:
        lowered = request.lower()
        if "live" in lowered or "best judgment" in lowered:
            reason = (
                "The CEO cannot place a live trade by best judgment. Execution is blocked until RiskGovernor "
                "checks, complete evidence, immutable audit logging, and Human Board approval are present."
            )
        else:
            reason = (
                "Execution proposals are blocked at the CEO layer until RiskGovernor review, complete evidence, "
                "immutable audit logging, and Human Board approval are present."
            )
        return blocked_by_risk_template(request=request, reason=reason, evidence_refs=evidence_refs)

    def _collect_evidence_refs(self, agent_outputs: dict[str, Any]) -> list[str]:
        evidence_refs: list[str] = []
        for output in agent_outputs.values():
            refs = getattr(output, "evidence_refs", None)
            if refs:
                evidence_refs.extend(str(ref) for ref in refs)
        return evidence_refs


def _departments_from_agents(agent_names: list[str]) -> list[str]:
    departments: list[str] = []
    for name in agent_names:
        if "research" in name:
            departments.append("research")
        elif "strategy" in name:
            departments.append("strategy_creation")
        elif "simulation" in name or "backtest" in name:
            departments.append("simulation")
        elif "risk" in name:
            departments.append("risk")
        elif "portfolio" in name or "execution" in name or "allocation" in name:
            departments.append("portfolio")
        elif "audit" in name:
            departments.append("audit")
        elif "ceo" in name:
            departments.append("executive")
    return list(dict.fromkeys(departments))


def _next_steps_for_decision(decision) -> list[str]:
    if decision.status == "needs_more_context":
        return ["provide_missing_evidence_or_inputs"]
    if decision.requires_board_approval:
        return ["prepare_board_approval_request", "wait_for_human_approval"]
    if decision.status == "rejected":
        return ["choose_a_governed_safe_workflow"]
    return ["continue_with_governed_department_workflow"]


__all__ = ["CEOAgent", "CEO_POLICY_REFERENCES", "CEO_SYSTEM_INSTRUCTIONS"]
