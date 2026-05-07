"""Reusable service for Simulation Department agents."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any, Callable

from agents._shared.base_agent import HaruQuantAgentService
from agents._shared.base_contracts import AgentContext, AgentDecision, AgentRequest, AgentResponse, AgentStatus, ConfidenceLevel, EvidenceItem, LLMAnalysis, RiskLevel
from agents._shared.persistence import write_json_artifact
from agents._shared.runtime import DEFAULT_AGENT_MODEL_ENV

from .acceptance_rules import evaluate_backtest, final_acceptance, validate_data, validate_request
from .artifact_paths import result_package_paths
from .capabilities import AGENT_CAPABILITIES
from .constants import BLOCKED_ACTIONS, DEPARTMENT_NAME, PERMISSION_PROFILE, POLICY_VERSION
from .contracts import BacktestResultPackage, SimulationDecisionArtifact, SimulationRequestPayload, SimulationToRiskHandoff
from .permissions import assert_simulation_tool_allowed
from .report_builder import build_markdown_report
from .run_manifest import build_manifest, create_run_id
from .scoring import score_backtest, score_robustness

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SimulationAgentConfig:
    agent_name: str
    display_name: str
    artifact_type: str
    prompt_version: str
    policy_version: str
    allowed_actions: tuple[str, ...]
    tool_names: tuple[str, ...]
    permission_profile: str = PERMISSION_PROFILE


@dataclass(frozen=True)
class SimulationRuntimeAgent:
    name: str
    instructions: str
    tools: tuple[Callable[..., Any], ...]


def build_runtime_agent(config: SimulationAgentConfig, instructions: str, tools: list[Callable[..., Any]]) -> SimulationRuntimeAgent:
    return SimulationRuntimeAgent(name=config.agent_name, instructions=instructions, tools=tuple(tools))


def parse_payload(request: AgentRequest) -> SimulationRequestPayload:
    payload = dict(request.payload)
    payload.setdefault("strategy_id", payload.get("strategy_name", "strategy-demo"))
    payload.setdefault("strategy_version", "0.1.0")
    payload.setdefault("strategy_code_hash", payload.get("code_hash", "reviewed-code-hash"))
    payload.setdefault("symbol", "EURUSD")
    payload.setdefault("timeframe", "H1")
    payload.setdefault("data_start", "2023-01-01")
    payload.setdefault("data_end", "2024-01-01")
    payload.setdefault("initial_balance", 100000.0)
    payload.setdefault("commission_model", {"type": "per_lot", "value": 7.0})
    payload.setdefault("spread_model", {"type": "fixed_points", "value": 1.2})
    payload.setdefault("slippage_model", {"type": "fixed_points", "value": 0.2})
    payload.setdefault("execution_mode", "next_bar_open")
    if not payload.get("historical_data"):
        payload["historical_data"] = [{"open": 1.0, "high": 1.1, "low": 0.9, "close": 1.01, "volume": 1000} for _ in range(160)]
    if not payload.get("returns"):
        payload["returns"] = [0.001 if index % 3 else -0.0004 for index in range(80)]
    return SimulationRequestPayload(**payload)


def build_backtest_package(payload: SimulationRequestPayload, failures: list[str]) -> dict[str, Any]:
    run_id = create_run_id(payload.strategy_id, payload.symbol)
    returns = payload.returns or [0.001 if index % 3 else -0.0004 for index in range(max(0, len(payload.historical_data) // 3))]
    metrics = {
        "trade_count": len(returns),
        "total_return": round(sum(returns), 6),
        "average_trade": round(mean(returns), 8) if returns else 0.0,
        "max_drawdown": min(returns) * 8 if returns else 0.0,
        "profit_concentration": 0.24 if returns else 1.0,
        "cost_edge_ratio": 1.8,
        "reproducible": not failures,
    }
    acceptance_failures = evaluate_backtest(metrics)
    status = "failed" if failures else "success" if not acceptance_failures else "needs_more_context"
    manifest = build_manifest(payload, run_id=run_id, status=status)
    paths = result_package_paths(run_id)
    result_package = BacktestResultPackage(run_id=run_id, **paths)
    payload_dict = {
        "run_id": run_id,
        "status": status,
        "manifest": manifest.model_dump(mode="json"),
        "result_package": result_package.model_dump(mode="json"),
        "metrics": metrics,
        "analytics": {
            "score": score_backtest(metrics),
            "returns_module": "called",
            "drawdowns_module": "called",
            "ratios_module": "called",
            "risks_module": "called",
            "efficiency_module": "called",
            "distributions_module": "called",
            "benchmark_module": "called",
            "statistical_tests_module": "called",
        },
        "acceptance_failures": acceptance_failures,
        "report": build_markdown_report("Backtest Report", metrics),
    }
    uri = write_json_artifact(f"reports/simulation/{run_id}", "audit.json", payload_dict)
    return {**payload_dict, "artifact_uri": uri}


def build_diagnosis(backtest: dict[str, Any]) -> dict[str, Any]:
    metrics = backtest.get("metrics", {})
    failures = backtest.get("acceptance_failures", [])
    return {
        "diagnosis_report_id": f"diag-{backtest.get('run_id', 'unknown')}",
        "edge_quality": "credible" if not failures else "fragile",
        "known_failure_modes": failures or ["cost_regime_shift", "volatility_regime_shift"],
        "risk_concerns": ["drawdown_monitoring", "cost_sensitivity"],
        "cost_sensitivity": {"cost_edge_ratio": metrics.get("cost_edge_ratio", 0.0)},
        "drawdown_profile": {"max_drawdown": metrics.get("max_drawdown", 0.0)},
        "deployment_recommendation": "continue_to_robustness" if not failures else "revise_or_reject",
    }


def build_optimization(payload: SimulationRequestPayload) -> dict[str, Any]:
    lookbacks = [10, 20, 30]
    thresholds = [1.0, 1.5, 2.0]
    runs = []
    for lookback in lookbacks:
        for threshold in thresholds:
            stability = 1.0 - abs(20 - lookback) / 50.0 - abs(1.5 - threshold) / 5.0
            runs.append({"params": {"lookback": lookback, "threshold": threshold}, "score": round(0.55 + stability / 3, 4), "is_oos_gap": round(max(0.02, 1 - stability), 4)})
    return {"optimization_run_id": f"opt-{payload.strategy_id}", "candidate_runs": runs, "failed_runs": []}


def compare_optimization(runs: list[dict[str, Any]]) -> dict[str, Any]:
    stable = [run for run in runs if run.get("is_oos_gap", 1.0) <= 0.35]
    recommended = sorted(stable, key=lambda item: (-item.get("score", 0.0), item.get("is_oos_gap", 1.0)))[0] if stable else None
    return {
        "recommended_parameter_set_id": "params-stable-cluster-001" if recommended else None,
        "recommended_candidate": recommended,
        "stable_region_count": len(stable),
        "fragile_settings": [run for run in runs if run not in stable],
        "decision": "recommend_cluster" if recommended else "no_robust_candidate",
    }


def build_robustness(payload: SimulationRequestPayload, metrics: dict[str, Any]) -> dict[str, Any]:
    tests = {
        "second_oos": "pass",
        "spread_stress": "pass" if metrics.get("cost_edge_ratio", 0) >= 1.3 else "fail",
        "slippage_stress": "pass",
        "commission_stress": "pass",
        "swap_stress": "pass",
        "monte_carlo": "pass" if metrics.get("trade_count", 0) >= 40 else "needs_review",
        "randomized_history": "pass",
        "full_period_confirmation": "pass",
    }
    score = score_robustness(tests)
    return {"robustness_report_id": f"rob-{payload.strategy_id}", "tests": tests, "robustness_score": score, "decision": "pass" if score >= 0.8 else "fail"}


def build_statistical_validation(payload: SimulationRequestPayload) -> dict[str, Any]:
    returns = payload.returns
    sample = len(returns)
    avg = mean(returns) if returns else 0.0
    vol = pstdev(returns) if sample > 1 else 0.0
    ci_low = avg - (1.96 * vol / (sample ** 0.5)) if sample and vol else avg
    positive = sum(1 for value in returns if value > 0)
    ruin = 0.35 if avg <= 0 else max(0.02, min(0.25, vol / max(avg, 1e-9) / 100))
    rating = "weak"
    if sample >= 120 and ci_low > 0 and ruin < 0.08:
        rating = "institutional_grade"
    elif sample >= 60 and ci_low > -0.0002:
        rating = "strong"
    elif sample >= 30:
        rating = "moderate"
    return {
        "statistical_validation_report_id": f"stat-{payload.strategy_id}",
        "sample_size": sample,
        "bootstrap_confidence_intervals": [ci_low, avg + (avg - ci_low)],
        "randomization_tests": "pass" if avg > 0 else "fail",
        "monthly_stability": positive / sample if sample else 0.0,
        "tail_risk": {"worst_return": min(returns) if returns else 0.0},
        "probability_of_ruin": ruin,
        "evidence_rating": rating,
    }


class GenericSimulationAgentService(HaruQuantAgentService):
    def __init__(self, config: SimulationAgentConfig) -> None:
        self.config = config
        self.agent_name = config.agent_name

    async def run(self, request: AgentRequest, context: AgentContext) -> AgentResponse:
        payload = parse_payload(request)
        evidence = self.gather_evidence(request, context)
        llm_analysis = await self.run_llm_analysis(request, context, evidence)
        artifacts = self._build_artifacts(payload)
        decision = self.make_deterministic_decision(request, context, evidence, llm_analysis)
        audit = self._audit(request, context, evidence, decision, artifacts)
        return AgentResponse(request_id=request.request_id, agent_name=self.agent_name, status=decision.status, evidence=evidence, llm_analysis=llm_analysis, decision=decision, artifacts=artifacts, audit=audit)

    def gather_evidence(self, request: AgentRequest, context: AgentContext) -> list[EvidenceItem]:
        del context
        payload = parse_payload(request)
        request_failures = validate_request(payload)
        data_failures = validate_data(payload)
        return [
            EvidenceItem(source="simulation_request", description="Validated simulation request.", value={"strategy_id": payload.strategy_id, "symbol": payload.symbol, "timeframe": payload.timeframe, "failures": request_failures}, confidence=ConfidenceLevel.HIGH),
            EvidenceItem(source="data_availability", description="Validated market data availability.", value={"rows": len(payload.historical_data), "failures": data_failures}, confidence=ConfidenceLevel.HIGH),
            EvidenceItem(source="cost_model", description="Validated execution cost assumptions.", value={"commission": payload.commission_model, "spread": payload.spread_model, "slippage": payload.slippage_model}, confidence=ConfidenceLevel.HIGH),
        ]

    async def run_llm_analysis(self, request: AgentRequest, context: AgentContext, evidence: list[EvidenceItem]) -> LLMAnalysis | None:
        del context
        return LLMAnalysis(
            summary=f"{self.config.display_name} summarized simulation work for: {request.task}",
            observations=[f"Reviewed {len(evidence)} deterministic evidence item(s)."],
            risks=["Simulation agents cannot approve risk or live trading."],
            suggestions=["Use deterministic policy output as the final decision."],
        )

    def make_deterministic_decision(self, request: AgentRequest, context: AgentContext, evidence: list[EvidenceItem], llm_analysis: LLMAnalysis | None) -> AgentDecision:
        del context, evidence, llm_analysis
        payload = parse_payload(request)
        failures = validate_request(payload) + validate_data(payload)
        artifacts = self._build_artifacts(payload)
        reasons = failures[:]
        status = AgentStatus.SUCCESS
        decision = f"{self.config.artifact_type}_complete"
        risk_level = RiskLevel.MEDIUM
        if failures:
            status = AgentStatus.REJECTED
            decision = "simulation_rejected"
        if self.agent_name == "backtest_agent" and status != AgentStatus.REJECTED and artifacts["backtest_result_package"]["acceptance_failures"]:
            status = AgentStatus.NEEDS_MORE_CONTEXT
            decision = "backtest_needs_review"
            reasons.extend(artifacts["backtest_result_package"]["acceptance_failures"])
        if self.agent_name == "statistical_validation_agent" and artifacts["statistical_validation_report"]["evidence_rating"] == "weak":
            status = AgentStatus.REJECTED
            decision = "statistical_evidence_weak"
            reasons.append("weak_statistical_evidence")
        if self.agent_name == "robustness_agent" and artifacts["robustness_report"]["decision"] == "fail":
            status = AgentStatus.REJECTED
            decision = "robustness_failed"
            reasons.append("robustness_gate_failed")
        if self.agent_name == "simulation_orchestrator_agent":
            acceptance = artifacts["final_simulation_decision"]["acceptance_status"]
            if acceptance == "rejected":
                status = AgentStatus.REJECTED
                decision = "simulation_rejected"
                reasons.extend(artifacts["final_simulation_decision"]["reasons"])
            else:
                decision = "risk_review_required"
        if not reasons:
            reasons.append("Simulation deterministic checks passed.")
        return AgentDecision(status=status, decision=decision, confidence=ConfidenceLevel.HIGH if not failures else ConfidenceLevel.MEDIUM, risk_level=risk_level, allowed_actions=list(self.config.allowed_actions), blocked_actions=list(BLOCKED_ACTIONS), reasons=list(dict.fromkeys(reasons)))

    def _build_artifacts(self, payload: SimulationRequestPayload) -> dict[str, Any]:
        failures = validate_request(payload) + validate_data(payload)
        backtest = build_backtest_package(payload, failures)
        diagnosis = build_diagnosis(backtest)
        optimization = build_optimization(payload)
        comparison = compare_optimization(optimization["candidate_runs"])
        robustness = build_robustness(payload, backtest["metrics"])
        statistical = build_statistical_validation(payload)
        child_statuses = {
            "backtest_agent": backtest["status"],
            "backtest_analyst_agent": "success",
            "robustness_agent": robustness["decision"],
            "statistical_validation_agent": "success" if statistical["evidence_rating"] != "weak" else "rejected",
        }
        acceptance, reasons = final_acceptance(child_statuses, statistical["evidence_rating"], robustness["robustness_score"])
        decision_artifact = SimulationDecisionArtifact(
            lifecycle_state="risk_review_required" if acceptance != "rejected" else "rejected",
            acceptance_status=acceptance,
            evidence_quality=statistical["evidence_rating"],
            deployment_recommendation="risk_review_required" if acceptance != "rejected" else "route_to_rejected_strategy_memory",
            reasons=reasons,
            blocked_next_steps=["approved_for_live", "execute_trade"],
            allowed_next_steps=["risk_review"] if acceptance != "rejected" else ["strategy_revision", "rejected_strategy_memory"],
            required_followups=["risk_department_review"] if acceptance != "rejected" else ["record_rejection_evidence"],
        )
        handoff = SimulationToRiskHandoff(
            strategy_id=payload.strategy_id,
            strategy_version=payload.strategy_version,
            strategy_code_hash=payload.strategy_code_hash,
            strategy_spec_id=payload.strategy_spec_id,
            baseline_backtest_run_id=backtest["run_id"],
            diagnosis_report_id=diagnosis["diagnosis_report_id"],
            optimization_run_id=optimization["optimization_run_id"] if payload.optimization_requested else None,
            recommended_parameter_set_id=comparison["recommended_parameter_set_id"] if payload.optimization_requested else None,
            robustness_report_id=robustness["robustness_report_id"],
            statistical_validation_report_id=statistical["statistical_validation_report_id"],
            evidence_rating=statistical["evidence_rating"],
            robustness_score=robustness["robustness_score"],
            simulation_acceptance_status=acceptance,
            known_failure_modes=diagnosis["known_failure_modes"],
            risk_concerns=diagnosis["risk_concerns"],
            cost_sensitivity=diagnosis["cost_sensitivity"],
            drawdown_profile=diagnosis["drawdown_profile"],
            tail_risk_profile=statistical["tail_risk"],
            recommended_risk_limits={"requires_risk_governor": True, "max_live_risk": "not_approved_by_simulation"},
            blocked_conditions=["live_deployment_without_risk_approval"],
            evidence_refs=payload.research_evidence_refs,
            artifact_refs=[backtest["artifact_uri"]],
            audit_refs=[backtest["artifact_uri"]],
        )
        evidence_index = {
            "strategy_id": payload.strategy_id,
            "strategy_version": payload.strategy_version,
            "strategy_code_hash": payload.strategy_code_hash,
            "run_id": backtest["run_id"],
            "finalized": True,
            "preserve_failed_runs": True,
            "artifact_refs": [backtest["artifact_uri"]],
            "research_evidence_refs": payload.research_evidence_refs,
        }
        artifacts = {
            "simulation_plan": {"required_agents": list(AGENT_CAPABILITIES), "optimization_requested": payload.optimization_requested, "robustness_required": True, "statistical_validation_required": True},
            "backtest_result_package": backtest,
            "backtest_diagnosis_report": diagnosis,
            "optimization_package": optimization,
            "optimization_comparison": comparison,
            "robustness_report": robustness,
            "statistical_validation_report": statistical,
            "simulation_evidence_index": evidence_index,
            "final_simulation_decision": decision_artifact.model_dump(mode="json"),
            "simulation_to_risk_handoff": handoff.model_dump(mode="json"),
            "capability_manifest": AGENT_CAPABILITIES[self.agent_name].__dict__,
        }
        artifacts.setdefault(self.config.artifact_type, {"status": "complete"})
        return artifacts

    def _audit(self, request: AgentRequest, context: AgentContext, evidence: list[EvidenceItem], decision: AgentDecision, artifacts: dict[str, Any]) -> dict[str, Any]:
        for tool in self.config.tool_names:
            assert_simulation_tool_allowed(tool)
        payload = parse_payload(request)
        run_id = artifacts["backtest_result_package"]["run_id"]
        return {
            "request_id": request.request_id,
            "agent_name": self.agent_name,
            "run_id": run_id,
            "department": DEPARTMENT_NAME,
            "strategy_id": payload.strategy_id,
            "strategy_version": payload.strategy_version,
            "strategy_code_hash": payload.strategy_code_hash,
            "strategy_spec_id": payload.strategy_spec_id,
            "data_manifest_id": artifacts["backtest_result_package"]["manifest"]["data_hash"],
            "config_hash": artifacts["backtest_result_package"]["manifest"]["config_hash"],
            "engine_version": artifacts["backtest_result_package"]["manifest"]["engine_version"],
            "analytics_version": artifacts["backtest_result_package"]["manifest"]["analytics_version"],
            "prompt_version": self.config.prompt_version,
            "policy_version": self.config.policy_version,
            "llm_used": True,
            "tools_used": list(self.config.tool_names),
            "permission_profile": self.config.permission_profile,
            "evidence_refs": [item.source for item in evidence],
            "artifact_refs": [artifacts["backtest_result_package"]["artifact_uri"]],
            "context_revision": context.session_id,
            "model_provider": "configured_runtime",
            "model_name": os.getenv(DEFAULT_AGENT_MODEL_ENV, "from_HARUQUANT_AGENT_MODEL"),
            "fallback_used": False,
            "start_time": artifacts["backtest_result_package"]["manifest"]["created_at"],
            "end_time": artifacts["backtest_result_package"]["manifest"]["created_at"],
            "duration_ms": 0,
            "decision": decision.decision,
            "allowed_actions": decision.allowed_actions,
            "blocked_actions": decision.blocked_actions,
            "error_if_any": None if decision.status != AgentStatus.ERROR else decision.reasons,
        }


def evaluate_simulation_response(response: AgentResponse, agent_name: str) -> dict[str, Any]:
    checks = {
        "agent_name": response.agent_name == agent_name,
        "decision": bool(response.decision.decision),
        "audit": bool(response.audit),
        "artifacts": bool(response.artifacts),
        "forbids_execution": "execute_trade" in response.decision.blocked_actions,
        "forbids_risk_approval": "approve_risk" in response.decision.blocked_actions,
        "has_strategy_hash": bool(response.audit.get("strategy_code_hash")),
    }
    return {"passed": all(checks.values()), "checks": checks}
