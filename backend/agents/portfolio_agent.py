"""Portfolio agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .prompts.portfolio_template import PORTFOLIO_AGENT_INSTRUCTION
from .runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentRuntime,
    CanonicalOutputValidator,
)


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
