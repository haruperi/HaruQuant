"""Strategy agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentRuntime,
    CanonicalOutputValidator,
)


STRATEGY_AGENT_INSTRUCTION = """
You are the HaruQuant StrategyAgent.
Generate evidence-backed trade hypotheses, compare candidate actions when needed,
and never emit broker orders or direct execution instructions.
All outputs must be emitted as canonical TradeHypothesis contracts.
""".strip()


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
