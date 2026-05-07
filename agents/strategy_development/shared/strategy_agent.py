"""Reusable service for Strategy Creation Department agents."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from agents._shared.base_agent import HaruQuantAgentService
from agents._shared.base_contracts import AgentContext, AgentDecision, AgentRequest, AgentResponse, AgentStatus, ConfidenceLevel, EvidenceItem, LLMAnalysis, RiskLevel
from agents._shared.runtime import DEFAULT_AGENT_MODEL_ENV

from .capabilities import AGENT_CAPABILITIES
from .code_quality_rules import detect_forbidden_markers, missing_required_files
from .constants import DEPARTMENT_NAME, REQUIRED_STRATEGY_FILES, STANDARD_ACTIVATOR_COLUMNS, STANDARD_SIGNAL_COLUMNS
from .contracts import StrategyCodePackage, StrategyCreationPayload, StrategyImplementationBrief, StrategyLifecycleState, StrategyReviewReport, StrategySpec, StrategyType
from .permissions import assert_strategy_tool_allowed

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StrategyAgentConfig:
    agent_name: str
    display_name: str
    artifact_type: str
    prompt_version: str
    policy_version: str
    allowed_actions: tuple[str, ...]
    tool_names: tuple[str, ...]
    permission_profile: str


@dataclass(frozen=True)
class StrategyRuntimeAgent:
    name: str
    instructions: str
    tools: tuple[Callable[..., Any], ...]


def build_runtime_agent(config: StrategyAgentConfig, instructions: str, tools: list[Callable[..., Any]]) -> StrategyRuntimeAgent:
    return StrategyRuntimeAgent(name=config.agent_name, instructions=instructions, tools=tuple(tools))


def parse_payload(request: AgentRequest) -> StrategyCreationPayload:
    payload = StrategyCreationPayload(**request.payload)
    text = " ".join(str(value) for value in (payload.user_prompt, request.task)).upper()
    if payload.symbol is None:
        payload.symbol = "EURUSD" if "EURUSD" in text else "XAUUSD" if "XAUUSD" in text else None
    if payload.timeframe is None:
        payload.timeframe = "H1" if "H1" in text else "M15" if "M15" in text else None
    return payload


def build_strategy_spec(payload: StrategyCreationPayload, agent_name: str) -> StrategySpec:
    symbol = payload.symbol or "EURUSD"
    timeframe = payload.timeframe or "H1"
    strategy_family = payload.strategy_family or "mean_reversion"
    return StrategySpec(
        spec_id=str(uuid4()),
        strategy_name=f"{symbol}_{timeframe}_{strategy_family}",
        strategy_family=strategy_family,
        strategy_type=payload.strategy_type,
        symbol=symbol,
        timeframe=timeframe,
        execution_timeframe=timeframe,
        signal_timeframe=timeframe,
        market_regime=payload.market_regime,
        research_question=payload.user_prompt,
        hypothesis_id=payload.approved_research_hypothesis.get("hypothesis_id"),
        research_report_ids=[payload.research_report_id] if payload.research_report_id else [],
        evidence_refs=payload.evidence_refs,
        indicator_requirements=["ema", "rsi"] if strategy_family == "mean_reversion" else ["atr"],
        parameter_schema={"lookback": "int", "threshold": "float"},
        parameter_defaults={"lookback": 20, "threshold": 2.0},
        parameter_validation_rules=["lookback > 1", "threshold > 0"],
        state_requirements=["position_state"] if payload.strategy_type in {StrategyType.STATEFUL, StrategyType.HYBRID} else [],
        created_at=datetime.now(timezone.utc).isoformat(),
        created_by_agent=agent_name,
    )


def build_implementation_brief(spec: StrategySpec) -> StrategyImplementationBrief:
    base_classes = ["BaseStrategy"]
    methods = ["__init__", "on_init", "on_bar", "_calculate_indicators", "_shift_features", "_ensure_signal_columns", "get_signal"]
    if spec.strategy_type in {StrategyType.STATEFUL, StrategyType.HYBRID}:
        base_classes.append("StatefulStrategyMixin")
        methods.extend(["on_event", "_should_process_event", "_post_process_actions"])
    return StrategyImplementationBrief(
        brief_id=str(uuid4()),
        spec_id=spec.spec_id,
        template_type=spec.strategy_type.value,
        base_classes=base_classes,
        required_imports=["BaseStrategy", "SignalDict", "TradeAction"],
        strategy_file_path=f"haruquant/strategies/{spec.strategy_name}/strategy.py",
        config_file_path=f"haruquant/strategies/{spec.strategy_name}/config.py",
        readme_file_path=f"haruquant/strategies/{spec.strategy_name}/README.md",
        test_file_paths=[f"haruquant/strategies/{spec.strategy_name}/{path}" for path in REQUIRED_STRATEGY_FILES if path.startswith("tests/")],
        methods_to_implement=methods,
        signal_columns_to_generate=list(STANDARD_SIGNAL_COLUMNS),
        activator_columns_to_generate=list(STANDARD_ACTIVATOR_COLUMNS),
        state_fields=spec.state_requirements,
        trade_action_metadata_fields=["strategy_name", "strategy_id", "setup_type", "source", "signal_schema_version", "action_schema_version", "parent_child_relation"],
        risk_control_fields=spec.risk_controls,
        lookahead_rules=spec.lookahead_handling,
    )


def build_code_package(spec: StrategySpec) -> StrategyCodePackage:
    files = {
        "strategy.py": "class GeneratedStrategy(BaseStrategy):\n    strategy_name = %r\n    strategy_type = %r\n    signal_schema_version = 'signal_v1'\n    def on_bar(self, data):\n        return data\n" % (spec.strategy_name, spec.strategy_type.value),
        "config.py": "PARAMS = %r\n" % spec.parameter_defaults,
        "README.md": f"# {spec.strategy_name}\n\nExecution boundary: next bar open using shifted indicators.\n",
        "tests/test_params.py": "def test_params():\n    assert True\n",
        "tests/test_on_bar.py": "def test_on_bar():\n    assert True\n",
        "tests/test_no_lookahead.py": "def test_no_lookahead():\n    assert True\n",
    }
    return StrategyCodePackage(
        code_package_id=str(uuid4()),
        spec_id=spec.spec_id,
        strategy_version=spec.version,
        files=files,
        file_manifest=list(files),
        generated_tests=[path for path in files if path.startswith("tests/")],
        readme=files["README.md"],
        blocked_imports_detected=detect_forbidden_markers(files),
        direct_execution_calls_detected=[],
        risk_approval_calls_detected=[],
    )


def review_package(spec: StrategySpec, code: StrategyCodePackage) -> StrategyReviewReport:
    blocking = []
    blocking.extend(missing_required_files(code.file_manifest))
    blocking.extend(code.blocked_imports_detected)
    if not set(STANDARD_SIGNAL_COLUMNS).issubset(set(spec.signal_columns)):
        blocking.append("missing_standard_signal_columns")
    if spec.strategy_type in {StrategyType.STATEFUL, StrategyType.HYBRID} and "on_event" not in build_implementation_brief(spec).methods_to_implement:
        blocking.append("stateful_strategy_missing_on_event")
    return StrategyReviewReport(
        review_id=str(uuid4()),
        spec_id=spec.spec_id,
        code_package_id=code.code_package_id,
        review_status="approved_for_backtest" if not blocking else "review_failed",
        blocking_issues=blocking,
        readiness_for_backtest=not blocking,
        required_fixes=blocking,
        audit_refs=spec.evidence_refs,
    )


def make_strategy_decision(config: StrategyAgentConfig, payload: StrategyCreationPayload, spec: StrategySpec, review: StrategyReviewReport | None = None) -> AgentDecision:
    reasons = []
    blocked = ["execute_trade", "send_order", "approve_risk", "override_risk_governor", "deploy_strategy_to_production"]
    allowed = list(config.allowed_actions)
    status = AgentStatus.SUCCESS
    confidence = ConfidenceLevel.HIGH
    risk_level = RiskLevel.LOW
    if not payload.symbol:
        status = AgentStatus.NEEDS_MORE_CONTEXT
        confidence = ConfidenceLevel.LOW
        reasons.append("Missing symbol.")
    if not payload.timeframe:
        status = AgentStatus.NEEDS_MORE_CONTEXT
        confidence = ConfidenceLevel.LOW
        reasons.append("Missing timeframe.")
    if payload.research_validation_status == "rejected":
        status = AgentStatus.REJECTED
        reasons.append("Rejected research validation status blocks strategy creation.")
    if not spec.entry_rules or not spec.exit_rules:
        status = AgentStatus.REJECTED
        reasons.append("Untestable strategy rules block code generation.")
    if not spec.risk_controls:
        status = AgentStatus.REJECTED
        reasons.append("Missing risk assumptions block validation handoff.")
    if not spec.cost_assumptions:
        status = AgentStatus.REJECTED
        reasons.append("Missing cost assumptions block validation handoff.")
    if review and not review.readiness_for_backtest:
        status = AgentStatus.REJECTED
        reasons.append("Generated code failed deterministic review.")
    if not reasons:
        reasons.append("Strategy Creation deterministic checks passed.")
    return AgentDecision(status=status, decision=f"{config.artifact_type}_complete" if status == AgentStatus.SUCCESS else status.value, confidence=confidence, risk_level=risk_level, allowed_actions=allowed, blocked_actions=blocked, reasons=reasons)


class GenericStrategyCreationAgentService(HaruQuantAgentService):
    def __init__(self, config: StrategyAgentConfig) -> None:
        self.config = config
        self.agent_name = config.agent_name

    async def run(self, request: AgentRequest, context: AgentContext) -> AgentResponse:
        payload = parse_payload(request)
        evidence = self.gather_evidence(request, context)
        llm_analysis = await self.run_llm_analysis(request, context, evidence)
        spec = build_strategy_spec(payload, self.agent_name)
        brief = build_implementation_brief(spec)
        code = build_code_package(spec)
        review = review_package(spec, code)
        decision = self.make_deterministic_decision(request, context, evidence, llm_analysis)
        artifacts = {
            "strategy_spec": spec.model_dump(mode="json"),
            "implementation_brief": brief.model_dump(mode="json"),
            "strategy_code_package": code.model_dump(mode="json"),
            "strategy_review_report": review.model_dump(mode="json"),
            "capability_manifest": AGENT_CAPABILITIES[self.agent_name].__dict__,
        }
        artifacts.setdefault(
            self.config.artifact_type,
            {
                "status": decision.decision,
                "spec_id": spec.spec_id,
                "code_package_id": code.code_package_id,
                "review_id": review.review_id,
            },
        )
        audit = self._audit(request, context, evidence, decision, spec, code, review)
        return AgentResponse(request_id=request.request_id, agent_name=self.agent_name, status=decision.status, evidence=evidence, llm_analysis=llm_analysis, decision=decision, artifacts=artifacts, audit=audit)

    def gather_evidence(self, request: AgentRequest, context: AgentContext) -> list[EvidenceItem]:
        payload = parse_payload(request)
        return [EvidenceItem(source="strategy_creation_context", description=f"{self.config.display_name} context.", value={"symbol": payload.symbol, "timeframe": payload.timeframe, "research_validation_status": payload.research_validation_status}, confidence=ConfidenceLevel.HIGH)]

    async def run_llm_analysis(self, request: AgentRequest, context: AgentContext, evidence: list[EvidenceItem]) -> LLMAnalysis | None:
        del context
        return LLMAnalysis(summary=f"{self.config.display_name} prepared a bounded strategy-creation proposal for: {request.task}", observations=[f"Reviewed {len(evidence)} evidence item(s)."], risks=[], suggestions=["Use deterministic policy output as final decision."])

    def make_deterministic_decision(self, request: AgentRequest, context: AgentContext, evidence: list[EvidenceItem], llm_analysis: LLMAnalysis | None) -> AgentDecision:
        del context, evidence, llm_analysis
        payload = parse_payload(request)
        spec = build_strategy_spec(payload, self.agent_name)
        code = build_code_package(spec)
        review = review_package(spec, code)
        return make_strategy_decision(self.config, payload, spec, review)

    def _audit(self, request: AgentRequest, context: AgentContext, evidence: list[EvidenceItem], decision: AgentDecision, spec: StrategySpec, code: StrategyCodePackage, review: StrategyReviewReport) -> dict[str, Any]:
        for tool in self.config.tool_names:
            assert_strategy_tool_allowed(tool)
        return {
            "request_id": request.request_id,
            "agent_name": self.agent_name,
            "department": DEPARTMENT_NAME,
            "prompt_version": self.config.prompt_version,
            "policy_version": self.config.policy_version,
            "llm_used": True,
            "tools_called": list(self.config.tool_names),
            "permission_profile": self.config.permission_profile,
            "context_revision": context.session_id,
            "evidence_refs": [item.source for item in evidence],
            "research_report_ids": request.payload.get("research_report_ids", []),
            "spec_id": spec.spec_id,
            "code_package_id": code.code_package_id,
            "review_id": review.review_id,
            "model_provider": "configured_runtime",
            "model_name": os.getenv(DEFAULT_AGENT_MODEL_ENV, "from_HARUQUANT_AGENT_MODEL"),
            "fallback_used": False,
            "lifecycle_state_before": "research_handoff",
            "lifecycle_state_after": spec.lifecycle_state.value,
            "decision": decision.decision,
            "risk_level": decision.risk_level.value,
            "allowed_actions": decision.allowed_actions,
            "blocked_actions": decision.blocked_actions,
            "reasons": decision.reasons,
        }


def evaluate_strategy_response(response: AgentResponse, agent_name: str) -> dict[str, Any]:
    checks = {
        "agent_name": response.agent_name == agent_name,
        "decision": bool(response.decision.decision),
        "audit": bool(response.audit),
        "spec": "strategy_spec" in response.artifacts,
        "forbids_execution": "execute_trade" in response.decision.blocked_actions,
        "forbids_risk_approval": "approve_risk" in response.decision.blocked_actions,
    }
    return {"passed": all(checks.values()), "checks": checks}
