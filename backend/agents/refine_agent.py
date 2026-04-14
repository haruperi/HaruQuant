"""Refinement agent wrapper for AI trading workflow analysis."""

from __future__ import annotations

from dataclasses import dataclass

from .prompts.refine_template import REFINE_AGENT_INSTRUCTION
from .runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentRuntime,
    CanonicalOutputValidator,
)


@dataclass(frozen=True)
class RefineAgentWrapper:
    """Agent wrapper that analyzes backtest results and produces conclusions."""

    runner: ADKRunnerService
    output_validator: CanonicalOutputValidator

    agent_name: str = "refine_agent"
    instruction: str = REFINE_AGENT_INSTRUCTION

    def execute(
        self,
        *,
        runtime_agent: AgentRuntime,
        request: ADKRunRequest,
    ) -> ADKRunResult:
        result = self.runner.run(agent=runtime_agent, request=request)
        validated = self.output_validator.validate(result.output_payload)
        if validated.contract_type != "RefinementReport":
            raise ValueError("RefineAgent must emit RefinementReport outputs")
        return result
