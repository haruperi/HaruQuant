"""Reusable implementation for standard Research Department agents."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable

from agents._shared.base_agent import HaruQuantAgentService
from agents._shared.base_contracts import AgentContext, AgentDecision, AgentRequest, AgentResponse, AgentStatus, ConfidenceLevel, EvidenceItem, LLMAnalysis, RiskLevel
from agents._shared.runtime import DEFAULT_AGENT_MODEL_ENV
from .capabilities import RESEARCH_WORKFLOW_STEPS, capabilities_for
from .constants import DEPARTMENT_NAME, EXTREME_VOLATILITY_LABELS, MAX_SPREAD_PIPS, MIN_DATA_QUALITY_SCORE, MIN_SAMPLE_SIZE
from .contracts import ResearchReportArtifact, ValidationStatus
from .permissions import RESEARCH_PERMISSION_PROFILE_NAME, assert_research_tool_allowed
from .report_builder import build_research_report
from .validation import parse_research_payload

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResearchAgentConfig:
    agent_name: str
    display_name: str
    report_type: str
    prompt_version: str
    policy_version: str
    purpose: str
    allowed_actions: tuple[str, ...]
    blocked_actions: tuple[str, ...] = ("place_trade", "execute_order", "approve_risk", "modify_portfolio", "deploy_strategy")
    tool_names: tuple[str, ...] = ()
    required_payload_fields: tuple[str, ...] = ("symbol",)
    required_evidence_sources: tuple[str, ...] = ()
    controlled_write_actions: tuple[str, ...] = ()
    normal_evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchRuntimeAgent:
    name: str
    instructions: str
    tools: tuple[Callable[..., Any], ...] = ()


def build_runtime_agent(config: ResearchAgentConfig, instructions: str, tools: list[Callable[..., Any]] | tuple[Callable[..., Any], ...]) -> ResearchRuntimeAgent:
    return ResearchRuntimeAgent(name=config.agent_name, instructions=instructions, tools=tuple(tools))


def make_research_decision(*, config: ResearchAgentConfig, evidence: list[EvidenceItem], llm_analysis: LLMAnalysis | None) -> AgentDecision:
    del llm_analysis
    reasons: list[str] = []
    blocked = list(dict.fromkeys(config.blocked_actions))
    allowed = list(dict.fromkeys((*config.allowed_actions, *config.controlled_write_actions)))
    risk_level = RiskLevel.LOW
    confidence = ConfidenceLevel.HIGH
    status = AgentStatus.SUCCESS
    decision = f"{config.report_type}_complete"
    sources = {item.source for item in evidence}
    for required in config.required_evidence_sources:
        if required not in sources:
            status = AgentStatus.NEEDS_MORE_CONTEXT
            decision = "needs_more_context"
            confidence = ConfidenceLevel.LOW
            risk_level = RiskLevel.MEDIUM
            reasons.append(f"Required evidence source is missing: {required}.")
    for item in evidence:
        value = item.value if isinstance(item.value, dict) else {}
        data_quality = value.get("data_quality_score")
        sample_size = value.get("sample_size")
        spread_pips = value.get("spread_pips")
        volatility_state = str(value.get("volatility_state", "")).lower()
        validation_status = value.get("validation_status")
        missing_evidence = value.get("missing_evidence") or []
        if data_quality is not None and float(data_quality) < MIN_DATA_QUALITY_SCORE:
            confidence = ConfidenceLevel.LOW
            reasons.append("Data quality is below the Research Department threshold.")
        if sample_size is not None and int(sample_size) < MIN_SAMPLE_SIZE:
            for action in ("handoff_approved_hypothesis", "recommend_research_strategy_families"):
                if action in allowed:
                    allowed.remove(action)
            reasons.append("Sample size is insufficient for downstream handoff or recommendations.")
        if spread_pips is not None and float(spread_pips) > MAX_SPREAD_PIPS:
            risk_level = RiskLevel.HIGH
            blocked.append("trade_execution")
            reasons.append("Spread exceeds configured Research Department threshold.")
        if volatility_state in EXTREME_VOLATILITY_LABELS:
            risk_level = RiskLevel.CRITICAL
            blocked.extend(["position_scaling", "trade_execution"])
            reasons.append("Extreme volatility detected.")
        if validation_status == ValidationStatus.REJECTED.value:
            if "handoff_approved_hypothesis" in allowed:
                allowed.remove("handoff_approved_hypothesis")
            blocked.append("handoff_approved_hypothesis")
            reasons.append("Rejected validation status blocks Strategy Development handoff.")
        if validation_status in {ValidationStatus.APPROVED.value, ValidationStatus.APPROVED_WITH_CAUTION.value}:
            if "handoff_approved_hypothesis" in config.allowed_actions and "handoff_approved_hypothesis" not in allowed:
                allowed.append("handoff_approved_hypothesis")
            reasons.append("Validation status allows Strategy Development handoff.")
        if missing_evidence:
            status = AgentStatus.NEEDS_MORE_CONTEXT
            confidence = ConfidenceLevel.LOW
            reasons.append("Required supporting evidence is incomplete.")
    if not evidence:
        status = AgentStatus.NEEDS_MORE_CONTEXT
        confidence = ConfidenceLevel.LOW
        risk_level = RiskLevel.MEDIUM
        decision = "needs_more_context"
        reasons.append("No evidence was gathered.")
    if not reasons:
        reasons.append("Research evidence passed deterministic policy checks.")
    return AgentDecision(status=status, decision=decision, confidence=confidence, risk_level=risk_level, allowed_actions=allowed, blocked_actions=list(dict.fromkeys(blocked)), reasons=reasons)


class GenericResearchAgentService(HaruQuantAgentService):
    config: ResearchAgentConfig

    def __init__(self, config: ResearchAgentConfig) -> None:
        self.config = config
        self.agent_name = config.agent_name

    async def run(self, request: AgentRequest, context: AgentContext) -> AgentResponse:
        logger.info("Starting research agent run", extra={"request_id": request.request_id, "agent_name": self.agent_name})
        try:
            payload = parse_research_payload(request)
            missing_fields = [field for field in self.config.required_payload_fields if not getattr(payload, field, None)]
            if missing_fields:
                evidence: list[EvidenceItem] = []
                llm_analysis = None
                decision = AgentDecision(status=AgentStatus.NEEDS_MORE_CONTEXT, decision="needs_more_context", confidence=ConfidenceLevel.LOW, risk_level=RiskLevel.MEDIUM, allowed_actions=[], blocked_actions=list(self.config.blocked_actions), reasons=[f"Missing required field: {field}." for field in missing_fields])
                artifacts: dict[str, Any] = {}
                validation_status = "missing_required_fields"
            else:
                evidence = self.gather_evidence(request, context)
                llm_analysis = await self.run_llm_analysis(request, context, evidence)
                decision = self.make_deterministic_decision(request, context, evidence, llm_analysis)
                report = self._build_report(request, evidence, decision)
                artifacts = self._build_artifacts(report)
                validation_status = "valid"
        except Exception as exc:  # pragma: no cover
            logger.exception("Research agent run failed", extra={"request_id": request.request_id, "agent_name": self.agent_name})
            evidence = []
            llm_analysis = None
            decision = AgentDecision(status=AgentStatus.ERROR, decision="error", confidence=ConfidenceLevel.LOW, risk_level=RiskLevel.MEDIUM, allowed_actions=[], blocked_actions=list(self.config.blocked_actions), reasons=[str(exc)])
            artifacts = {}
            validation_status = "error"
        audit = self._build_audit(request, context, evidence, decision, validation_status)
        logger.info(
            "Finished research agent run",
            extra={
                "request_id": request.request_id,
                "agent_name": self.agent_name,
                "decision": decision.decision,
                "risk_level": decision.risk_level.value,
            },
        )
        return AgentResponse(request_id=request.request_id, agent_name=self.agent_name, status=decision.status, evidence=evidence, llm_analysis=llm_analysis, decision=decision, artifacts=artifacts, audit=audit)

    def gather_evidence(self, request: AgentRequest, context: AgentContext) -> list[EvidenceItem]:
        payload = parse_research_payload(request)
        evidence_value = dict(self.config.normal_evidence)
        evidence_value.update({"symbol": payload.symbol, "symbols": payload.symbols or ([payload.symbol] if payload.symbol else []), "timeframes": payload.timeframes, "data_window": payload.data_window, "research_question": payload.research_question, "context_revision": payload.context_revision or context.session_id, "data_quality_score": request.payload.get("data_quality_score", evidence_value.get("data_quality_score", 0.8)), "sample_size": request.payload.get("sample_size", evidence_value.get("sample_size", 250)), "spread_pips": request.payload.get("spread_pips", evidence_value.get("spread_pips")), "volatility_state": request.payload.get("volatility_state", evidence_value.get("volatility_state", "normal")), "validation_status": request.payload.get("validation_status", evidence_value.get("validation_status")), "missing_evidence": request.payload.get("missing_evidence", evidence_value.get("missing_evidence", []))})
        source = self.config.required_evidence_sources[0] if self.config.required_evidence_sources else self.config.report_type
        return [EvidenceItem(source=source, description=f"{self.config.display_name} deterministic research evidence.", value=evidence_value, confidence=ConfidenceLevel.HIGH)]

    async def run_llm_analysis(self, request: AgentRequest, context: AgentContext, evidence: list[EvidenceItem]) -> LLMAnalysis | None:
        del context
        return LLMAnalysis(summary=f"{self.config.display_name} prepared a bounded analytical proposal for: {request.task}", observations=[f"Reviewed {len(evidence)} evidence item(s)."], risks=[], suggestions=["Use deterministic policy output as the final decision."], raw_model_output=None)

    def make_deterministic_decision(self, request: AgentRequest, context: AgentContext, evidence: list[EvidenceItem], llm_analysis: LLMAnalysis | None) -> AgentDecision:
        del request, context
        return make_research_decision(config=self.config, evidence=evidence, llm_analysis=llm_analysis)

    def _build_report(self, request: AgentRequest, evidence: list[EvidenceItem], decision: AgentDecision) -> ResearchReportArtifact:
        payload = parse_research_payload(request)
        status = ValidationStatus.NEEDS_MORE_EVIDENCE
        if "handoff_approved_hypothesis" in decision.allowed_actions:
            status = ValidationStatus.APPROVED_WITH_CAUTION
        if "handoff_approved_hypothesis" in decision.blocked_actions:
            status = ValidationStatus.REJECTED
        return build_research_report(agent_name=self.agent_name, report_type=self.config.report_type, symbol=payload.symbol, timeframes=payload.timeframes, data_window=payload.data_window, research_question=payload.research_question, evidence=evidence, risks=decision.reasons, recommended_next_steps=decision.allowed_actions, confidence=decision.confidence, validation_status=status)

    def _build_artifacts(self, report: ResearchReportArtifact) -> dict[str, Any]:
        capabilities = capabilities_for(self.agent_name)
        report_payload = report.model_dump(mode="json")
        artifacts: dict[str, Any] = {self.config.report_type: report_payload}
        for artifact_name in capabilities.output_artifacts:
            artifacts.setdefault(
                artifact_name,
                {
                    "source_report_id": report.report_id,
                    "source_agent": self.agent_name,
                    "artifact_type": artifact_name,
                    "evidence_refs": report.evidence_refs,
                    "status": report.validation_status.value,
                },
            )
        artifacts["capability_manifest"] = {
            "inputs": capabilities.inputs,
            "evidence_required": capabilities.evidence_required,
            "llm_responsibilities": capabilities.llm_responsibilities,
            "deterministic_rules": capabilities.deterministic_rules,
            "functional_capabilities": capabilities.functional_capabilities,
            "tests_required": capabilities.tests_required,
            "route_targets": capabilities.route_targets,
            "workflow_steps": RESEARCH_WORKFLOW_STEPS,
        }
        return artifacts

    def _build_audit(self, request: AgentRequest, context: AgentContext, evidence: list[EvidenceItem], decision: AgentDecision, input_validation_status: str) -> dict[str, Any]:
        tools_used = list(self.config.tool_names)
        for tool in tools_used:
            assert_research_tool_allowed(tool)
        capabilities = capabilities_for(self.agent_name)
        return {"agent_name": self.agent_name, "department": DEPARTMENT_NAME, "request_id": request.request_id, "context_revision": request.payload.get("context_revision") or context.session_id, "prompt_version": self.config.prompt_version, "policy_version": self.config.policy_version, "llm_used": True, "tools_used": tools_used, "tools_called": tools_used, "permission_profile": RESEARCH_PERMISSION_PROFILE_NAME, "evidence_refs": [item.source for item in evidence], "model_provider": "configured_runtime", "model_name": os.getenv(DEFAULT_AGENT_MODEL_ENV, "from_HARUQUANT_AGENT_MODEL"), "fallback_used": False, "input_validation_status": input_validation_status, "evidence_count": len(evidence), "decision": decision.decision, "risk_level": decision.risk_level.value, "allowed_actions": decision.allowed_actions, "blocked_actions": decision.blocked_actions, "error_if_any": None if decision.status != AgentStatus.ERROR else "; ".join(decision.reasons), "accepted_inputs": list(capabilities.inputs), "evidence_required": list(capabilities.evidence_required), "deterministic_rules": list(capabilities.deterministic_rules), "output_artifacts": list(capabilities.output_artifacts), "functional_capabilities": list(capabilities.functional_capabilities)}


def evaluate_research_response(response: AgentResponse, agent_name: str) -> dict[str, Any]:
    blocked = set(response.decision.blocked_actions)
    checks = {"has_request_id": bool(response.request_id), "has_agent_name": response.agent_name == agent_name, "has_decision": bool(response.decision.decision), "has_reasons": bool(response.decision.reasons), "has_audit": bool(response.audit), "forbids_execution": bool({"place_trade", "execute_order"} & blocked), "forbids_risk_approval": "approve_risk" in blocked}
    return {"passed": all(checks.values()), "checks": checks}
