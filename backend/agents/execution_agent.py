"""Execution agent instruction and wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .prompts.execution_template import EXECUTION_AGENT_INSTRUCTION
from .runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    AgentRuntime,
    CanonicalOutputValidator,
)


@dataclass(frozen=True)
class ExecutionAgentWrapper:
    """Thin wrapper that validates execution outputs as ExecutionIntent."""

    runner: ADKRunnerService
    output_validator: CanonicalOutputValidator

    agent_name: str = "execution_agent"
    instruction: str = EXECUTION_AGENT_INSTRUCTION

    def execute(
        self,
        *,
        runtime_agent: AgentRuntime,
        request: ADKRunRequest,
    ) -> ADKRunResult:
        result = self.runner.run(agent=runtime_agent, request=request)
        validated = self.output_validator.validate(result.output_payload)
        if validated.contract_type != "ExecutionIntent":
            raise ValueError("ExecutionAgent must emit ExecutionIntent outputs")
        return result
