"""Service interface for the Strategy Creator Agent."""

from __future__ import annotations

from typing import Any

from agents._shared import AgentRunContext, AgentRunResult
from agents._shared.schemas import StrategySpec as LegacyStrategySpec

from agents.strategy_development.shared.strategy_agent import GenericStrategyCreationAgentService, StrategyAgentConfig

CONFIG = StrategyAgentConfig(
    agent_name="strategy_creator_agent",
    display_name="Strategy Creator Agent",
    artifact_type="strategy_spec",
    prompt_version="strategy_creator_agent_prompt_v1",
    policy_version="strategy_creator_agent_policy_v1",
    allowed_actions=('create_strategy_spec', 'create_implementation_brief', 'define_strategy_contracts', 'save_creation_evidence'),
    tool_names=('read_research_reports', 'read_approved_hypotheses', 'write_strategy_spec'),
    permission_profile="strategy_spec_write_v1",
)


class StrategyCreatorAgentService(GenericStrategyCreationAgentService):
    def __init__(self) -> None:
        super().__init__(CONFIG)


class StrategyCreatorAgent:
    """Compatibility facade for older operating-cycle callers."""

    agent_name = "strategy_creator"

    def create_spec(
        self,
        *,
        request: str,
        research_evidence: list[str] | None = None,
    ) -> LegacyStrategySpec:
        upper = request.upper()
        symbol = "EURUSD" if "EURUSD" in upper else "XAUUSD" if "XAUUSD" in upper else "EURUSD"
        timeframe = "H1" if "H1" in upper else "M15" if "M15" in upper else "H1"
        family = "mean_reversion" if "MEAN" in upper or "REVERSION" in upper else "candidate"
        return LegacyStrategySpec(
            strategy_name=f"{symbol}_{timeframe}_{family}",
            version="0.1.0",
            market="forex" if symbol != "XAUUSD" else "metals",
            symbol=symbol,
            timeframe=timeframe,
            data_requirements=["ohlcv", "spread", "execution_costs"],
            entry_logic=[
                "Use only closed bars.",
                "Enter when validated setup conditions are true.",
            ],
            exit_logic=[
                "Exit at target, stop, invalidation, or max holding period.",
                "Never use future bars or repainting indicators.",
            ],
            position_sizing={
                "method": "fixed_fractional",
                "max_risk_per_trade": 0.005,
            },
            risk_assumptions=[
                "RiskGovernor must approve all paper/live proposals.",
                "Live deployment requires Board approval.",
            ],
            cost_assumptions=[
                "Use spread, slippage, commission, and swap assumptions.",
            ],
            invalid_conditions=[
                "News block active",
                "Spread above policy",
                "Missing OHLCV columns",
            ],
            test_plan=[
                "unit_tests",
                "backtest",
                "cost_sensitivity",
                "robustness",
            ],
            evidence_refs=[] if research_evidence is None else [],
            deployment_recommendation="spec_review",
        )

    def run(
        self,
        *,
        context: AgentRunContext,
        task_input: dict[str, Any],
    ) -> AgentRunResult:
        spec = self.create_spec(
            request=task_input.get("request", context.user_request),
            research_evidence=task_input.get("research_evidence", []),
        )
        return AgentRunResult(
            agent_name=self.agent_name,
            status="completed",
            output={
                "spec": spec.model_dump(mode="json"),
                "lifecycle_state": "spec",
            },
            evidence_refs=[],
            decisions=[
                {
                    "decision": "spec_created",
                    "rationale": "Compatibility StrategySpec created from request.",
                }
            ],
        )


__all__ = ["CONFIG", "StrategyCreatorAgent", "StrategyCreatorAgentService"]
