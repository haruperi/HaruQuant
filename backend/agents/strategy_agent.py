"""Strategy agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .prompts.strategy_template import STRATEGY_AGENT_INSTRUCTION
from .runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentRuntime,
    CanonicalOutputValidator,
)


@dataclass(frozen=True)
class StrategyAgentWrapper:
    """Thin wrapper that validates strategy outputs as TradeHypothesis."""

    runner: ADKRunnerService
    output_validator: CanonicalOutputValidator

    agent_name: str = "strategy_agent"
    instruction: str = STRATEGY_AGENT_INSTRUCTION

    def execute(
        self,
        *,
        runtime_agent: AgentRuntime,
        request: ADKRunRequest,
    ) -> ADKRunResult:
        result = self.runner.run(agent=runtime_agent, request=request)
        validated = self.output_validator.validate(result.output_payload)
        if validated.contract_type != "TradeHypothesis":
            raise ValueError("StrategyAgent must emit TradeHypothesis outputs")
        return result
