"""Strategy Creation Department."""

from __future__ import annotations

from typing import Any

from agents._shared.persistence import stable_id, utc_stamp, write_json_artifact
from agents._shared import AgentRunContext, AgentRunResult
from agents._shared.schemas import StrategySpec


class StrategyCreatorAgent:
    agent_name = "strategy_creator"

    def create_spec(self, *, request: str, research_evidence: list[str] | None = None) -> StrategySpec:
        upper = request.upper()
        symbol = "EURUSD" if "EURUSD" in upper else "XAUUSD" if "XAUUSD" in upper else "UNKNOWN"
        timeframe = "H1" if "H1" in upper else "M15" if "M15" in upper else "H1"
        is_mean_reversion = "MEAN" in upper or "REVERSION" in upper
        strategy_name = f"{symbol}_{timeframe}_{'mean_reversion' if is_mean_reversion else 'candidate'}"
        return StrategySpec(
            strategy_name=strategy_name,
            version="0.1.0",
            market="forex" if symbol.endswith("USD") and symbol != "XAUUSD" else "metals",
            symbol=symbol,
            timeframe=timeframe,
            data_requirements=["ohlcv", "spread", "session", "execution_costs"],
            entry_logic=[
                "Use only closed bars.",
                "Enter when price deviates from rolling mean and confirmation closes inside allowed session.",
            ],
            exit_logic=[
                "Exit at mean reversion target, protective stop, or max holding period.",
                "Never use future bars or repainting indicators.",
            ],
            position_sizing={"method": "fixed_fractional", "max_risk_per_trade": 0.005},
            risk_assumptions=["RiskGovernor must approve all paper/live proposals.", "Live deployment requires Board approval."],
            cost_assumptions=["Use spread, slippage, commission, and swap assumptions from broker-grade data."],
            invalid_conditions=["News block active", "Spread above policy", "Insufficient warmup", "Missing OHLCV columns"],
            test_plan=["unit_tests", "backtest", "cost_sensitivity", "robustness", "statistical_validation"],
            deployment_recommendation="spec_review",
        )

    def save_spec(self, spec: StrategySpec) -> str:
        strategy_id = stable_id("strategy", f"{spec.strategy_name}-{spec.version}")
        path = write_json_artifact(
            "memory/strategies/active",
            f"{strategy_id}.json",
            {"strategy_id": strategy_id, "lifecycle_state": "spec", "spec": spec.model_dump(mode="json")},
        )
        return path

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        spec = self.create_spec(
            request=task_input.get("request", context.user_request),
            research_evidence=task_input.get("research_evidence", []),
        )
        path = self.save_spec(spec)
        return AgentRunResult(
            agent_name=self.agent_name,
            status="completed",
            output={"spec": spec.model_dump(mode="json"), "strategy_spec_uri": path, "lifecycle_state": "spec"},
            evidence_refs=[path],
            decisions=[{"decision": "spec_created", "rationale": "Formal StrategySpec created from request and research evidence."}],
        )


__all__ = ["StrategyCreatorAgent"]
