"""Portfolio agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentRuntime,
    CanonicalOutputValidator,
)


PORTFOLIO_AGENT_INSTRUCTION = """
You are the HaruQuant PortfolioAgent.
Analyze portfolio state and emit advisory rebalancing, hedging, resizing,
or de-risking recommendations without causing live side effects.
All outputs must be emitted as canonical EvaluationReport contracts.
""".strip()


@dataclass(frozen=True)
class PortfolioAgentWrapper:
    """Thin wrapper that validates portfolio outputs as EvaluationReport."""

    runner: ADKRunnerService
    output_validator: CanonicalOutputValidator

    agent_name: str = "portfolio_agent"
    instruction: str = PORTFOLIO_AGENT_INSTRUCTION

    def execute(
        self,
        *,
        runtime_agent: AgentRuntime,
        request: ADKRunRequest,
    ) -> ADKRunResult:
        result = self.runner.run(agent=runtime_agent, request=request)
        validated = self.output_validator.validate(result.output_payload)
        if validated.contract_type != "EvaluationReport":
            raise ValueError("PortfolioAgent must emit EvaluationReport outputs")
        return result
